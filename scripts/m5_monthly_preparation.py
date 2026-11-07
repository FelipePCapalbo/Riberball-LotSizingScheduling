import os
import sys

import pandas as pd

str_raw_directory = sys.argv[1]
str_root_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
str_output_path = os.path.join(str_root_directory, 'data', 'literatura', 'm5_mensal_departamento.csv')

df_calendar = pd.read_csv(os.path.join(str_raw_directory, 'calendar.csv'), usecols=['date'])
df_sales = pd.read_csv(os.path.join(str_raw_directory, 'sales_train_evaluation.csv'))

list_day_columns = []
for str_column in df_sales.columns:
    if str_column.startswith('d_'):
        list_day_columns.append(str_column)

df_department_daily = df_sales.groupby(['cat_id', 'dept_id'])[list_day_columns].sum().T
df_department_daily.index = pd.to_datetime(df_calendar['date'].iloc[:len(df_department_daily)].to_numpy())
df_department_monthly = df_department_daily.resample('MS').sum()

df_days_per_month = df_department_daily.iloc[:, 0].resample('MS').count()
list_complete_months = []
for timestamp_month in df_days_per_month.index:
    if df_days_per_month[timestamp_month] == timestamp_month.days_in_month:
        list_complete_months.append(timestamp_month)
df_department_monthly = df_department_monthly.loc[list_complete_months]

df_output = df_department_monthly.T.reset_index()
list_month_names = []
for timestamp_month in df_department_monthly.index:
    list_month_names.append(timestamp_month.strftime('%m/%Y'))
df_output.columns = ['CATEGORIA', 'DEPARTAMENTO'] + list_month_names
os.makedirs(os.path.dirname(str_output_path), exist_ok=True)
df_output.to_csv(str_output_path, index=False, sep=';')
print(df_output.iloc[:, :8].to_string())
print(len(list_month_names), list_month_names[0], list_month_names[-1])
