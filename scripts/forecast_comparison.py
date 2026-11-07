import math
import os
import warnings

import numpy as np
import pandas as pd
from sklearn.neural_network import MLPRegressor
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing, Holt, SimpleExpSmoothing
from statsmodels.tsa.statespace.sarimax import SARIMAX

warnings.filterwarnings('ignore')

str_root_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
str_client_path = os.path.join(str_root_directory, 'data', 'brutos', 'input_asis.xlsx')
str_literature_path = os.path.join(str_root_directory, 'data', 'literatura', 'm5_mensal_departamento.csv')
str_output_root = os.path.join(str_root_directory, 'dissertacao', 'dados', 'previsao')

int_season_length = 12
int_minimum_seasonal_history = 24
int_neural_network_seeds = 10
float_level_prior_variance = 100.0
list_level_noise_grid = [0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
list_lambda_grid = [0.25, 0.5, 1.0, 2.0, 4.0]
list_month_abbreviations = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']

list_methods = [
    ['rls', 'RLS hierárquico (proposto)'],
    ['company', 'Previsão da empresa'],
    ['naive', 'Ingênuo'],
    ['seasonal_naive', 'Ingênuo sazonal'],
    ['moving_average', 'Média móvel simples (3)'],
    ['weighted_moving_average', 'Média móvel ponderada (3)'],
    ['ses', 'Suavização exponencial simples'],
    ['holt', 'Holt'],
    ['holt_winters', 'Holt-Winters'],
    ['linear_regression', 'Regressão linear'],
    ['arima', 'ARIMA'],
    ['sarima', 'SARIMA'],
    ['neural_network', 'Rede neural (MLP)'],
]


def fit_rls(array_log_history, array_features, array_seasonal_prior, float_lambda):
    int_coefficient_count = array_features.shape[1] + 1
    array_best_coefficients = None
    float_best_squared_error = math.inf
    for float_level_noise in list_level_noise_grid:
        array_coefficients = np.concatenate([[array_log_history[0]], array_seasonal_prior])
        array_covariance = np.zeros((int_coefficient_count, int_coefficient_count))
        array_covariance[0, 0] = float_level_prior_variance
        array_covariance[1:, 1:] = np.eye(int_coefficient_count - 1) / float_lambda
        float_squared_error = 0.0
        for int_row in range(len(array_log_history)):
            array_covariance[0, 0] += float_level_noise
            array_row = np.concatenate([[1.0], array_features[int_row]])
            float_residual = array_log_history[int_row] - array_row @ array_coefficients
            if int_row >= 2:
                float_squared_error += float_residual * float_residual
            array_projected = array_covariance @ array_row
            array_gain = array_projected / (1.0 + array_row @ array_projected)
            array_coefficients = array_coefficients + array_gain * float_residual
            array_covariance = array_covariance - np.outer(array_gain, array_projected)
        if float_squared_error < float_best_squared_error:
            float_best_squared_error = float_squared_error
            array_best_coefficients = array_coefficients
    return array_best_coefficients


def forecast_hierarchical_rls(df_sales, dict_parent_by_series, list_parents, array_month_dummies, int_origin, float_lambda):
    if int_origin >= int_minimum_seasonal_history:
        array_features = array_month_dummies
    else:
        array_features = np.zeros(array_month_dummies.shape)
    array_features_training = array_features[:int_origin]
    array_features_target = array_features[int_origin]
    array_total_log_history = np.log(df_sales.iloc[:, :int_origin].sum(axis=0).to_numpy())
    array_global_coefficients = fit_rls(array_total_log_history, array_features_training, np.zeros(array_features.shape[1]), float_lambda)
    float_total_forecast = math.exp(array_global_coefficients[0] + array_features_target @ array_global_coefficients[1:])
    dict_parent_forecast = {}
    dict_series_forecast = {}
    for str_parent in list_parents:
        list_children = []
        for str_series in df_sales.index:
            if dict_parent_by_series[str_series] == str_parent:
                list_children.append(str_series)
        array_parent_log_history = np.log(df_sales.loc[list_children].iloc[:, :int_origin].sum(axis=0).to_numpy())
        array_parent_coefficients = fit_rls(array_parent_log_history, array_features_training, array_global_coefficients[1:], float_lambda)
        dict_parent_forecast[str_parent] = math.exp(array_parent_coefficients[0] + array_features_target @ array_parent_coefficients[1:])
        for str_series in list_children:
            array_series_log_history = np.log(df_sales.loc[str_series].iloc[:int_origin].to_numpy())
            array_series_coefficients = fit_rls(array_series_log_history, array_features_training, array_parent_coefficients[1:], float_lambda)
            dict_series_forecast[str_series] = math.exp(array_series_coefficients[0] + array_features_target @ array_series_coefficients[1:])
    return float_total_forecast, dict_parent_forecast, dict_series_forecast


def compute_error_metrics(dict_forecast_by_series, dict_actual_by_series, list_evaluation_months):
    dict_metrics = {}
    for str_series in dict_forecast_by_series:
        float_absolute_percentage_sum = 0.0
        float_error_sum = 0.0
        float_actual_sum = 0.0
        int_point_count = 0
        for int_month in list_evaluation_months:
            if int_month in dict_forecast_by_series[str_series]:
                float_forecast = dict_forecast_by_series[str_series][int_month]
                float_actual = dict_actual_by_series[str_series][int_month]
                float_absolute_percentage_sum += abs(float_actual - float_forecast) / float_actual
                float_error_sum += float_forecast - float_actual
                float_actual_sum += float_actual
                int_point_count += 1
        if int_point_count == len(list_evaluation_months):
            dict_metrics[str_series] = {
                'mape': 100.0 * float_absolute_percentage_sum / int_point_count,
                'bias': 100.0 * float_error_sum / float_actual_sum,
            }
    return dict_metrics


def format_decimal(float_value, int_decimals):
    str_formatted = f'{float_value:.{int_decimals}f}'.replace('.', ',')
    if str_formatted.startswith('-'):
        str_formatted = '$-$' + str_formatted[1:]
    return str_formatted


def run_instance(str_instance, df_sales, dict_parent_by_series, list_month_columns, list_tuning_months, list_evaluation_months, dict_company_forecast, int_display_months, float_display_scale):
    str_output_directory = os.path.join(str_output_root, str_instance)
    os.makedirs(str_output_directory, exist_ok=True)
    list_series = list(df_sales.index)
    int_month_count = len(list_month_columns)

    list_parents = []
    for str_series in list_series:
        if dict_parent_by_series[str_series] not in list_parents:
            list_parents.append(dict_parent_by_series[str_series])

    list_month_labels = []
    array_month_dummies = np.zeros((int_month_count, int_season_length))
    for int_month in range(int_month_count):
        int_month_of_year = int(list_month_columns[int_month].split('/')[0])
        list_month_labels.append(list_month_abbreviations[int_month_of_year - 1] + '/' + list_month_columns[int_month].split('/')[1][2:])
        array_month_dummies[int_month, int_month_of_year - 1] = 1.0

    dict_actual_by_series = {}
    for str_series in list_series:
        dict_actual_by_series[str_series] = {}
        for int_month in range(int_month_count):
            dict_actual_by_series[str_series][int_month] = float(df_sales.loc[str_series, int_month])
    dict_actual_by_level = {'Total': {}}
    for int_month in range(int_month_count):
        dict_actual_by_level['Total'][int_month] = float(df_sales[int_month].sum())
    for str_parent in list_parents:
        dict_actual_by_level[str_parent] = {}
        for int_month in range(int_month_count):
            float_parent_sum = 0.0
            for str_series in list_series:
                if dict_parent_by_series[str_series] == str_parent:
                    float_parent_sum += df_sales.loc[str_series, int_month]
            dict_actual_by_level[str_parent][int_month] = float_parent_sum

    float_best_lambda = list_lambda_grid[0]
    float_best_tuning_mape = math.inf
    for float_lambda in list_lambda_grid:
        dict_tuning_forecasts = {}
        for str_series in list_series:
            dict_tuning_forecasts[str_series] = {}
        for int_origin in list_tuning_months:
            float_unused_total, dict_unused_parents, dict_series_forecast = forecast_hierarchical_rls(
                df_sales, dict_parent_by_series, list_parents, array_month_dummies, int_origin, float_lambda
            )
            for str_series in list_series:
                dict_tuning_forecasts[str_series][int_origin] = dict_series_forecast[str_series]
        dict_tuning_metrics = compute_error_metrics(dict_tuning_forecasts, dict_actual_by_series, list_tuning_months)
        float_tuning_mape = 0.0
        for str_series in dict_tuning_metrics:
            float_tuning_mape += dict_tuning_metrics[str_series]['mape'] / len(dict_tuning_metrics)
        if float_tuning_mape < float_best_tuning_mape:
            float_best_tuning_mape = float_tuning_mape
            float_best_lambda = float_lambda
    print(str_instance, 'lambda', float_best_lambda)

    dict_forecasts = {}
    for list_method in list_methods:
        dict_forecasts[list_method[0]] = {}
        for str_series in list_series:
            dict_forecasts[list_method[0]][str_series] = {}
    for str_series in dict_company_forecast:
        dict_forecasts['company'][str_series] = dict_company_forecast[str_series]
    dict_rls_by_level = {'Total': {}}
    for str_parent in list_parents:
        dict_rls_by_level[str_parent] = {}

    for int_origin in list_evaluation_months:
        print(str_instance, 'origin', list_month_labels[int_origin])
        float_total_forecast, dict_parent_forecast, dict_series_forecast = forecast_hierarchical_rls(
            df_sales, dict_parent_by_series, list_parents, array_month_dummies, int_origin, float_best_lambda
        )
        dict_rls_by_level['Total'][int_origin] = float_total_forecast
        for str_parent in list_parents:
            dict_rls_by_level[str_parent][int_origin] = dict_parent_forecast[str_parent]
        for str_series in list_series:
            dict_forecasts['rls'][str_series][int_origin] = dict_series_forecast[str_series]

        bool_seasonal_history = int_origin >= int_minimum_seasonal_history
        if bool_seasonal_history:
            int_lag_count = int_season_length
        else:
            int_lag_count = 3
        list_network_inputs = []
        list_network_targets = []
        for str_series in list_series:
            array_history = df_sales.loc[str_series].iloc[:int_origin].to_numpy()
            float_history_mean = array_history.mean()
            for int_target in range(int_lag_count, int_origin):
                list_network_inputs.append(array_history[int_target - int_lag_count:int_target] / float_history_mean)
                list_network_targets.append(array_history[int_target] / float_history_mean)
        list_network_models = []
        for int_seed in range(int_neural_network_seeds):
            model_network = MLPRegressor(hidden_layer_sizes=(8,), solver='lbfgs', max_iter=5000, random_state=int_seed)
            model_network.fit(np.array(list_network_inputs), np.array(list_network_targets))
            list_network_models.append(model_network)

        for str_series in list_series:
            array_history = df_sales.loc[str_series].iloc[:int_origin].to_numpy()
            dict_forecasts['naive'][str_series][int_origin] = array_history[-1]
            dict_forecasts['seasonal_naive'][str_series][int_origin] = array_history[int_origin - int_season_length]
            dict_forecasts['moving_average'][str_series][int_origin] = array_history[-3:].mean()
            dict_forecasts['weighted_moving_average'][str_series][int_origin] = (3.0 * array_history[-1] + 2.0 * array_history[-2] + array_history[-3]) / 6.0
            model_ses = SimpleExpSmoothing(array_history, initialization_method='estimated').fit()
            dict_forecasts['ses'][str_series][int_origin] = float(model_ses.forecast(1)[0])
            model_holt = Holt(array_history, initialization_method='estimated').fit()
            dict_forecasts['holt'][str_series][int_origin] = float(model_holt.forecast(1)[0])
            array_line_coefficients = np.polyfit(np.arange(int_origin), array_history, 1)
            dict_forecasts['linear_regression'][str_series][int_origin] = float(np.polyval(array_line_coefficients, int_origin))

            float_best_criterion = math.inf
            float_best_arima_forecast = array_history[-1]
            for int_ar_order in range(2):
                for int_difference_order in range(2):
                    for int_ma_order in range(2):
                        if int_difference_order == 0:
                            str_trend = 'c'
                        else:
                            str_trend = 'n'
                        model_arima = ARIMA(array_history, order=(int_ar_order, int_difference_order, int_ma_order), trend=str_trend, enforce_stationarity=False, enforce_invertibility=False).fit()
                        if np.isfinite(model_arima.aicc) and model_arima.aicc < float_best_criterion:
                            float_best_criterion = model_arima.aicc
                            float_best_arima_forecast = float(model_arima.forecast(1)[0])
            dict_forecasts['arima'][str_series][int_origin] = float_best_arima_forecast

            if bool_seasonal_history:
                model_holt_winters = ExponentialSmoothing(array_history, trend='add', seasonal='mul', seasonal_periods=int_season_length, initialization_method='estimated').fit()
                dict_forecasts['holt_winters'][str_series][int_origin] = float(model_holt_winters.forecast(1)[0])
                float_best_criterion = math.inf
                float_best_sarima_forecast = array_history[-1]
                for int_ar_order in range(2):
                    for int_difference_order in range(2):
                        for int_ma_order in range(2):
                            model_sarima = SARIMAX(np.log(array_history), order=(int_ar_order, int_difference_order, int_ma_order), seasonal_order=(0, 1, 1, int_season_length)).fit(disp=False)
                            if np.isfinite(model_sarima.aicc) and model_sarima.aicc < float_best_criterion:
                                float_best_criterion = model_sarima.aicc
                                float_best_sarima_forecast = float(math.exp(model_sarima.forecast(1)[0]))
                dict_forecasts['sarima'][str_series][int_origin] = float_best_sarima_forecast

            float_history_mean = array_history.mean()
            array_network_input = (array_history[-int_lag_count:] / float_history_mean).reshape(1, -1)
            float_network_sum = 0.0
            for model_network in list_network_models:
                float_network_sum += float(model_network.predict(array_network_input)[0])
            dict_forecasts['neural_network'][str_series][int_origin] = float_history_mean * float_network_sum / int_neural_network_seeds

    list_summary_rows = []
    list_table_lines = ['\\begin{tabular}{@{}lrr@{}}', '\\toprule', 'Método & MAPE (\\%) & Viés (\\%) \\\\', '\\midrule']
    for list_method in list_methods:
        dict_metrics = compute_error_metrics(dict_forecasts[list_method[0]], dict_actual_by_series, list_evaluation_months)
        if len(dict_metrics) == len(list_series):
            float_mape_sum = 0.0
            float_bias_sum = 0.0
            for str_series in dict_metrics:
                float_mape_sum += dict_metrics[str_series]['mape']
                float_bias_sum += dict_metrics[str_series]['bias']
            float_mean_mape = float_mape_sum / len(dict_metrics)
            float_mean_bias = float_bias_sum / len(dict_metrics)
            list_summary_rows.append({'method': list_method[1], 'mape': float_mean_mape, 'bias': float_mean_bias})
            str_method_cell = list_method[1]
            str_mape_cell = format_decimal(float_mean_mape, 1)
            str_bias_cell = format_decimal(float_mean_bias, 1)
            if list_method[0] == 'rls':
                str_method_cell = '\\textbf{' + str_method_cell + '}'
                str_mape_cell = '\\textbf{\\boldmath ' + str_mape_cell + '}'
                str_bias_cell = '\\textbf{\\boldmath ' + str_bias_cell + '}'
            list_table_lines.append(str_method_cell + ' & ' + str_mape_cell + ' & ' + str_bias_cell + ' \\\\')
    list_table_lines.append('\\bottomrule')
    list_table_lines.append('\\end{tabular}')
    with open(os.path.join(str_output_directory, 'tabela_metricas.tex'), 'w', encoding='utf-8') as file_table:
        file_table.write('\n'.join(list_table_lines) + '\n')
    df_summary = pd.DataFrame(list_summary_rows)
    df_summary.to_csv(os.path.join(str_output_directory, 'metricas_resumo.csv'), index=False, sep=';')
    print(df_summary.round(1).to_string())

    int_first_display_month = int_month_count - int_display_months
    list_aggregate_rows = []
    for int_month in range(int_first_display_month, int_month_count):
        dict_aggregate_row = {'month': int_month - int_first_display_month, 'label': list_month_labels[int_month], 'actual': dict_actual_by_level['Total'][int_month] / float_display_scale}
        for list_method in list_methods:
            float_total_sum = 0.0
            int_series_with_forecast = 0
            for str_series in list_series:
                if int_month in dict_forecasts[list_method[0]][str_series]:
                    float_total_sum += dict_forecasts[list_method[0]][str_series][int_month]
                    int_series_with_forecast += 1
            if int_series_with_forecast == len(list_series) and int_month in list_evaluation_months:
                dict_aggregate_row[list_method[0]] = float_total_sum / float_display_scale
            else:
                dict_aggregate_row[list_method[0]] = np.nan
        list_aggregate_rows.append(dict_aggregate_row)
    pd.DataFrame(list_aggregate_rows).to_csv(os.path.join(str_output_directory, 'serie_agregada.csv'), index=False, na_rep='nan', sep=';')

    list_tree_series = [['total', 'Total', dict_actual_by_level['Total'], dict_rls_by_level['Total']]]
    str_letters = 'abcdefghijklmnopqrstuvwxyz'
    for int_parent_index in range(len(list_parents)):
        str_parent = list_parents[int_parent_index]
        list_tree_series.append(['p' + str_letters[int_parent_index], str_parent, dict_actual_by_level[str_parent], dict_rls_by_level[str_parent]])
        int_child_index = 0
        for str_series in list_series:
            if dict_parent_by_series[str_series] == str_parent:
                str_child_key = 'c' + str_letters[int_parent_index] + str_letters[int_child_index]
                list_tree_series.append([str_child_key, str_series, dict_actual_by_series[str_series], dict_forecasts['rls'][str_series]])
                int_child_index += 1

    list_tree_rows = []
    for int_month in range(int_first_display_month, int_month_count):
        dict_tree_row = {'month': int_month - int_first_display_month, 'label': list_month_labels[int_month]}
        for list_tree_entry in list_tree_series:
            dict_tree_row[list_tree_entry[0] + '_actual'] = list_tree_entry[2][int_month] / float_display_scale
            if int_month in list_tree_entry[3]:
                dict_tree_row[list_tree_entry[0] + '_forecast'] = list_tree_entry[3][int_month] / float_display_scale
            else:
                dict_tree_row[list_tree_entry[0] + '_forecast'] = np.nan
        list_tree_rows.append(dict_tree_row)
    pd.DataFrame(list_tree_rows).to_csv(os.path.join(str_output_directory, 'arvore.csv'), index=False, na_rep='nan', sep=';')

    str_macro_prefix = '\\def\\' + str_instance
    list_macro_lines = [str_macro_prefix + 'Lambda{' + format_decimal(float_best_lambda, 2) + '}']
    for list_tree_entry in list_tree_series:
        dict_tree_metrics = compute_error_metrics({'serie': list_tree_entry[3]}, {'serie': list_tree_entry[2]}, list_evaluation_months)
        list_macro_lines.append(str_macro_prefix + 'Nome' + list_tree_entry[0] + '{' + list_tree_entry[1] + '}')
        list_macro_lines.append(str_macro_prefix + 'Mape' + list_tree_entry[0] + '{' + format_decimal(dict_tree_metrics['serie']['mape'], 1) + '}')
        list_macro_lines.append(str_macro_prefix + 'Vies' + list_tree_entry[0] + '{' + format_decimal(dict_tree_metrics['serie']['bias'], 1) + '}')
    with open(os.path.join(str_output_directory, 'arvore_valores.tex'), 'w', encoding='utf-8') as file_macros:
        file_macros.write('%\n'.join(list_macro_lines) + '%\n')


df_raw_client_sales = pd.read_excel(str_client_path, sheet_name='Faturado', header=1)
df_raw_client_forecast = pd.read_excel(str_client_path, sheet_name='Demanda', header=1)
list_client_month_columns = list(df_raw_client_sales.columns[2:])
list_client_series = []
dict_client_parent_by_series = {}
for int_row in range(len(df_raw_client_sales)):
    str_format = str(df_raw_client_sales.iloc[int_row]['MODELO']).strip()
    str_balloon = str_format + ' ' + str(df_raw_client_sales.iloc[int_row]['TIPO']).strip()
    list_client_series.append(str_balloon)
    dict_client_parent_by_series[str_balloon] = str_format
df_client_sales = pd.DataFrame(df_raw_client_sales[list_client_month_columns].to_numpy(dtype=float), index=list_client_series, columns=range(len(list_client_month_columns)))

dict_client_company_forecast = {}
list_client_company_months = []
for int_row in range(len(df_raw_client_forecast)):
    str_balloon = str(df_raw_client_forecast.iloc[int_row]['MODELO']).strip() + ' ' + str(df_raw_client_forecast.iloc[int_row]['TIPO']).strip()
    dict_client_company_forecast[str_balloon] = {}
    for str_company_column in list(df_raw_client_forecast.columns[2:]):
        int_month = list_client_month_columns.index(str_company_column)
        dict_client_company_forecast[str_balloon][int_month] = float(df_raw_client_forecast.iloc[int_row][str_company_column])
        if int_month >= int_season_length and int_month not in list_client_company_months:
            list_client_company_months.append(int_month)

run_instance(
    'cliente', df_client_sales, dict_client_parent_by_series, list_client_month_columns,
    list(range(6, int_season_length)), list_client_company_months, dict_client_company_forecast,
    len(list_client_month_columns), 1000.0,
)

df_raw_literature_sales = pd.read_csv(str_literature_path, sep=';')
list_literature_month_columns = list(df_raw_literature_sales.columns[2:])
list_literature_series = []
dict_literature_parent_by_series = {}
for int_row in range(len(df_raw_literature_sales)):
    str_department = str(df_raw_literature_sales.iloc[int_row]['DEPARTAMENTO']).replace('_', ' ')
    list_literature_series.append(str_department)
    dict_literature_parent_by_series[str_department] = str(df_raw_literature_sales.iloc[int_row]['CATEGORIA'])
df_literature_sales = pd.DataFrame(df_raw_literature_sales[list_literature_month_columns].to_numpy(dtype=float), index=list_literature_series, columns=range(len(list_literature_month_columns)))
int_literature_month_count = len(list_literature_month_columns)

run_instance(
    'literatura', df_literature_sales, dict_literature_parent_by_series, list_literature_month_columns,
    list(range(int_literature_month_count - 24, int_literature_month_count - 12)),
    list(range(int_literature_month_count - 12, int_literature_month_count)), {},
    36, 1000.0,
)
