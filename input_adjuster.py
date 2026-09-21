import os
import numpy as np
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, 'data')
SOURCE_PATH = os.path.join(DATA_DIR, 'input_asis.xlsx')
OUTPUT_PATH = os.path.join(DATA_DIR, 'input_asis_ajustado.xlsx')

WORKING_DAYS_PER_WEEK = 6
HOURS_PER_SHIFT = 8.0

COLOR_DARKNESS = {
    'BRANCO': 0,
    'AMARELO': 1,
    'LARANJA': 2,
    'ROSA': 3,
    'VERDE': 4,
    'AZUL': 5,
    'VERMELHO': 6,
    'ROXO': 7,
    'PRETO': 8,
}
COLOR_POPULARITY = ['VERMELHO', 'AZUL', 'BRANCO', 'AMARELO', 'VERDE', 'ROSA', 'PRETO', 'LARANJA', 'ROXO']
FORBIDDEN_COLOR_TRANSITIONS = [('PRETO', 'BRANCO'), ('PRETO', 'AMARELO'), ('ROXO', 'BRANCO')]

COLOR_SETUP_BASE = 0.25
COLOR_SETUP_DARKENING_STEP = 0.08
COLOR_SETUP_PURGE_BASE = 0.70
COLOR_SETUP_LIGHTENING_STEP = 0.45

FORM_SETUP_BASE = 2.5
FORM_SETUP_FAMILY_CHANGE = 2.0
FORM_SETUP_CALIBER_STEP = 0.4
FORM_SETUP_LARGER_PENALTY = 0.3
FORM_SETUP_TYPE_CHANGE = 1.5

MIN_LOT_DEMAND_FRACTION = 0.06
MIN_LOT_SHIFT_CAP = 0.25

CONFIRMED_FRACTION_START = 0.95
ORDER_DECAY_TAU = 8.0
ORDER_MIN_LINE_KG = 50.0
MIN_ITEMS_PER_ORDER = 1
MAX_ITEMS_PER_ORDER = 4
NUMBER_OF_CUSTOMERS = 20

MAINTENANCE_WEEKS_PER_YEAR = 2
MAINTENANCE_AVAILABILITY_LOW = 0.72
MAINTENANCE_AVAILABILITY_HIGH = 0.90
COLLECTIVE_SHUTDOWN_AVAILABILITY = 0.40
CARNIVAL_AVAILABILITY = 0.85

rng = np.random.default_rng(42)

df_source_productivity = pd.read_excel(SOURCE_PATH, sheet_name='Produtividade', header=1)
df_source_demand = pd.read_excel(SOURCE_PATH, sheet_name='Demanda', header=1)
df_source_inventory = pd.read_excel(SOURCE_PATH, sheet_name='Estoque', header=1)
df_source_costs = pd.read_excel(SOURCE_PATH, sheet_name='Custos')
df_source_availability = pd.read_excel(SOURCE_PATH, sheet_name='Disponibilidade de maquinas')
df_source_invoiced = pd.read_excel(SOURCE_PATH, sheet_name='Faturado', header=1)
df_source_produced = pd.read_excel(SOURCE_PATH, sheet_name='Produzido', header=1)

list_models = []
list_types = []
list_products = []
for int_row in range(len(df_source_demand)):
    series_row = df_source_demand.iloc[int_row]
    list_models.append(series_row['MODELO'])
    list_types.append(series_row['TIPO'])
    list_products.append(f"{series_row['MODELO']}-{series_row['TIPO']}")

list_machines = []
for str_column in df_source_productivity.columns:
    if str_column not in ('MODELO', 'TIPO'):
        list_machines.append(str(int(float(str_column))))

dict_productivity = {}
for str_product in list_products:
    dict_productivity[str_product] = {}
for int_row in range(len(df_source_productivity)):
    series_row = df_source_productivity.iloc[int_row]
    str_product = f"{series_row['MODELO']}-{series_row['TIPO']}"
    if str_product in dict_productivity:
        int_column = 0
        for str_column in df_source_productivity.columns:
            if str_column not in ('MODELO', 'TIPO'):
                float_rate = series_row[str_column]
                if pd.notna(float_rate) and float_rate > 0:
                    dict_productivity[str_product][list_machines[int_column]] = float(float_rate)
                int_column += 1

list_demand_months = []
for str_column in df_source_demand.columns:
    if str_column not in ('MODELO', 'TIPO'):
        list_demand_months.append(str_column)

dict_monthly_demand = {}
for int_row in range(len(df_source_demand)):
    series_row = df_source_demand.iloc[int_row]
    str_product = f"{series_row['MODELO']}-{series_row['TIPO']}"
    dict_monthly_demand[str_product] = {}
    for str_month in list_demand_months:
        dict_monthly_demand[str_product][str_month] = float(series_row[str_month])

dict_monthly_availability = {}
for int_row in range(len(df_source_availability)):
    series_row = df_source_availability.iloc[int_row]
    dict_monthly_availability[str(series_row['DATA'])] = True

timestamp_first_week = pd.Timestamp('2024-01-01')
str_last_month = list_demand_months[-1]
timestamp_last_covered = pd.Timestamp(
    year=int(str_last_month.split('/')[1]), month=int(str_last_month.split('/')[0]), day=1)
timestamp_last_covered = timestamp_last_covered + pd.offsets.MonthEnd(0)

list_weeks = []
timestamp_cursor = timestamp_first_week
while timestamp_cursor <= timestamp_last_covered:
    list_weeks.append(timestamp_cursor)
    timestamp_cursor = timestamp_cursor + pd.Timedelta(days=7)

dict_working_days_in_week_month = {}
dict_working_days_in_month = {}
for timestamp_week in list_weeks:
    dict_working_days_in_week_month[timestamp_week] = {}
    for int_day in range(WORKING_DAYS_PER_WEEK):
        timestamp_day = timestamp_week + pd.Timedelta(days=int_day)
        str_month = timestamp_day.strftime('%m/%Y')
        if str_month not in dict_working_days_in_week_month[timestamp_week]:
            dict_working_days_in_week_month[timestamp_week][str_month] = 0
        dict_working_days_in_week_month[timestamp_week][str_month] += 1
        if str_month not in dict_working_days_in_month:
            dict_working_days_in_month[str_month] = 0
        dict_working_days_in_month[str_month] += 1

dict_weekly_demand = {}
for str_product in list_products:
    dict_weekly_demand[str_product] = {}
    for timestamp_week in list_weeks:
        float_week_demand = 0.0
        for str_month in dict_working_days_in_week_month[timestamp_week]:
            if str_month in dict_monthly_demand[str_product]:
                float_share = (dict_working_days_in_week_month[timestamp_week][str_month]
                               / dict_working_days_in_month[str_month])
                float_week_demand += dict_monthly_demand[str_product][str_month] * float_share
        dict_weekly_demand[str_product][timestamp_week] = float_week_demand

dict_initial_inventory = {}
str_opening_month = list_demand_months[0]
for int_row in range(len(df_source_inventory)):
    series_row = df_source_inventory.iloc[int_row]
    str_product = f"{series_row['MODELO']}-{series_row['TIPO']}"
    if str_product in dict_weekly_demand:
        dict_initial_inventory[str_product] = float(series_row[str_opening_month])

dict_unit_cost = {}
for int_row in range(len(df_source_costs)):
    series_row = df_source_costs.iloc[int_row]
    str_product = f"{series_row['MODELO']}-{series_row['TIPO']}"
    if str_product in dict_weekly_demand:
        dict_unit_cost[str_product] = float(series_row['CUSTO_UNITARIO'])

dict_average_weekly_demand = {}
for str_product in list_products:
    float_total = 0.0
    for timestamp_week in list_weeks:
        float_total += dict_weekly_demand[str_product][timestamp_week]
    dict_average_weekly_demand[str_product] = float_total / len(list_weeks)

list_products_by_volume = []
list_remaining_products = list(list_products)
while len(list_remaining_products) > 0:
    str_best_product = list_remaining_products[0]
    for str_product in list_remaining_products:
        if dict_average_weekly_demand[str_product] > dict_average_weekly_demand[str_best_product]:
            str_best_product = str_product
    list_products_by_volume.append(str_best_product)
    list_remaining_products.remove(str_best_product)

dict_volume_rank = {}
for int_index in range(len(list_products_by_volume)):
    dict_volume_rank[list_products_by_volume[int_index]] = int_index

dict_sale_price = {}
for str_product in list_products:
    float_position = dict_volume_rank[str_product] / (len(list_products) - 1)
    float_margin_rate = 0.22 + 0.18 * float_position
    if str_product.split('-')[-1] != 'LISO':
        float_margin_rate += 0.10
    dict_sale_price[str_product] = dict_unit_cost[str_product] * (1.0 + float_margin_rate)

dict_model_of_product = {}
for int_index in range(len(list_products)):
    dict_model_of_product[list_products[int_index]] = str(list_models[int_index])

dict_family = {}
dict_caliber = {}
for int_index in range(len(list_products)):
    str_model_text = str(list_models[int_index])
    list_tokens = str_model_text.replace('.', ' ').split(' ')
    dict_family[list_products[int_index]] = list_tokens[0]
    float_caliber = 0.0
    bool_found = False
    for str_token in list_tokens:
        if str_token.isdigit() and not bool_found:
            float_caliber = float(str_token)
            bool_found = True
    dict_caliber[list_products[int_index]] = float_caliber

dict_calibers_by_family = {}
for str_product in list_products:
    str_family = dict_family[str_product]
    if str_family not in dict_calibers_by_family:
        dict_calibers_by_family[str_family] = []
    if dict_caliber[str_product] not in dict_calibers_by_family[str_family]:
        dict_calibers_by_family[str_family].append(dict_caliber[str_product])
for str_family in dict_calibers_by_family:
    dict_calibers_by_family[str_family] = sorted(dict_calibers_by_family[str_family])

dict_caliber_rank = {}
for str_product in list_products:
    dict_caliber_rank[str_product] = dict_calibers_by_family[dict_family[str_product]].index(
        dict_caliber[str_product])

dict_form_setup = {}
for str_from in list_products:
    for str_to in list_products:
        if str_from == str_to:
            dict_form_setup[(str_from, str_to)] = 0.0
        else:
            float_hours = 0.0
            if dict_model_of_product[str_from] != dict_model_of_product[str_to]:
                float_hours = FORM_SETUP_BASE
                if dict_family[str_from] != dict_family[str_to]:
                    float_hours += FORM_SETUP_FAMILY_CHANGE
                else:
                    float_hours += FORM_SETUP_CALIBER_STEP * abs(
                        dict_caliber_rank[str_from] - dict_caliber_rank[str_to])
                if dict_caliber[str_to] > dict_caliber[str_from]:
                    float_hours += FORM_SETUP_LARGER_PENALTY
            if str_from.split('-')[-1] != str_to.split('-')[-1]:
                float_hours += FORM_SETUP_TYPE_CHANGE
            dict_form_setup[(str_from, str_to)] = float_hours

dict_colors_by_product = {}
for str_product in list_products:
    int_position = dict_volume_rank[str_product]
    if int_position < 4:
        int_colors = 7
    elif int_position < 9:
        int_colors = 5
    elif int_position < 13:
        int_colors = 4
    else:
        int_colors = 3
    if str_product.split('-')[-1] != 'LISO':
        int_colors = 3
    list_colors = []
    for int_index in range(int_colors):
        list_colors.append(COLOR_POPULARITY[int_index])
    dict_colors_by_product[str_product] = list_colors

dict_color_mix = {}
for str_product in list_products:
    dict_mix = {}
    float_total = 0.0
    for str_color in dict_colors_by_product[str_product]:
        float_base = 1.0 / ((COLOR_POPULARITY.index(str_color) + 1) ** 0.7)
        float_noise = rng.uniform(0.80, 1.20)
        dict_mix[str_color] = float_base * float_noise
        float_total += dict_mix[str_color]
    for str_color in dict_mix:
        dict_mix[str_color] = dict_mix[str_color] / float_total
    dict_color_mix[str_product] = dict_mix

list_used_colors = []
for str_product in list_products:
    for str_color in dict_colors_by_product[str_product]:
        if str_color not in list_used_colors:
            list_used_colors.append(str_color)
list_colors_by_darkness = []
for str_color in COLOR_DARKNESS:
    if str_color in list_used_colors:
        list_colors_by_darkness.append(str_color)
list_used_colors = list_colors_by_darkness

dict_color_setup = {}
for str_from in list_used_colors:
    for str_to in list_used_colors:
        if str_from != str_to:
            bool_forbidden = False
            for tuple_pair in FORBIDDEN_COLOR_TRANSITIONS:
                if tuple_pair == (str_from, str_to):
                    bool_forbidden = True
            if bool_forbidden:
                dict_color_setup[(str_from, str_to)] = None
            else:
                int_gap = COLOR_DARKNESS[str_to] - COLOR_DARKNESS[str_from]
                if int_gap > 0:
                    dict_color_setup[(str_from, str_to)] = (
                        COLOR_SETUP_BASE + COLOR_SETUP_DARKENING_STEP * int_gap)
                else:
                    dict_color_setup[(str_from, str_to)] = (
                        COLOR_SETUP_PURGE_BASE + COLOR_SETUP_LIGHTENING_STEP * (-int_gap))

dict_min_lot = {}
for str_product in list_products:
    float_slowest_rate = None
    for str_machine in dict_productivity[str_product]:
        float_rate = dict_productivity[str_product][str_machine]
        if float_slowest_rate is None or float_rate < float_slowest_rate:
            float_slowest_rate = float_rate
    float_lot = dict_average_weekly_demand[str_product] * MIN_LOT_DEMAND_FRACTION
    float_cap = MIN_LOT_SHIFT_CAP * float_slowest_rate * HOURS_PER_SHIFT
    if float_lot > float_cap:
        float_lot = float_cap
    dict_min_lot[str_product] = float_lot

list_customers = []
list_customer_weights = []
for int_index in range(NUMBER_OF_CUSTOMERS):
    list_customers.append(f'CLI{int_index + 1:02d}')
    list_customer_weights.append(1.0 / ((int_index + 1) ** 0.9))
float_weight_total = 0.0
for float_weight in list_customer_weights:
    float_weight_total += float_weight
for int_index in range(len(list_customer_weights)):
    list_customer_weights[int_index] = list_customer_weights[int_index] / float_weight_total

list_order_headers = []
list_order_items = []
int_order_counter = 0
for int_week_index in range(len(list_weeks)):
    timestamp_week = list_weeks[int_week_index]
    float_confirmed_fraction = CONFIRMED_FRACTION_START * np.exp(-int_week_index / ORDER_DECAY_TAU)
    if float_confirmed_fraction >= 0.01:
        list_pending_lines = []
        for int_index in range(len(list_products)):
            str_product = list_products[int_index]
            float_confirmed_mass = dict_weekly_demand[str_product][timestamp_week] * float_confirmed_fraction
            for str_color in dict_color_mix[str_product]:
                float_color_mass = float_confirmed_mass * dict_color_mix[str_product][str_color]
                if float_color_mass >= ORDER_MIN_LINE_KG:
                    int_chunks = int(rng.integers(1, 3))
                    array_split = rng.dirichlet(np.ones(int_chunks))
                    for int_chunk in range(int_chunks):
                        list_pending_lines.append({
                            'model': list_models[int_index],
                            'type': list_types[int_index],
                            'color': str_color,
                            'quantity': float_color_mass * float(array_split[int_chunk]),
                        })
        rng.shuffle(list_pending_lines)

        int_cursor = 0
        while int_cursor < len(list_pending_lines):
            int_items = int(rng.integers(MIN_ITEMS_PER_ORDER, MAX_ITEMS_PER_ORDER + 1))
            int_end = int_cursor + int_items
            if int_end > len(list_pending_lines):
                int_end = len(list_pending_lines)
            int_order_counter += 1
            str_order_id = f'OC{int_order_counter:05d}'
            int_due_offset = int(rng.integers(0, WORKING_DAYS_PER_WEEK))
            timestamp_due = timestamp_week + pd.Timedelta(days=int_due_offset)
            timestamp_issue = timestamp_due - pd.Timedelta(days=int(rng.integers(7, 31)))
            str_customer = str(rng.choice(list_customers, p=list_customer_weights))
            list_order_headers.append({
                'PEDIDO_ID': str_order_id,
                'CLIENTE': str_customer,
                'DATA_EMISSAO': timestamp_issue,
                'DATA_VENCIMENTO': timestamp_due,
            })
            for int_line in range(int_cursor, int_end):
                dict_line = list_pending_lines[int_line]
                list_order_items.append({
                    'PEDIDO_ID': str_order_id,
                    'MODELO': dict_line['model'],
                    'TIPO': dict_line['type'],
                    'COR': dict_line['color'],
                    'QUANTIDADE': dict_line['quantity'],
                })
            int_cursor = int_end

dict_weekly_availability = {}
for str_machine in list_machines:
    dict_weekly_availability[str_machine] = {}
    for timestamp_week in list_weeks:
        dict_weekly_availability[str_machine][timestamp_week] = 1.0

list_shutdown_weeks = []
list_carnival_weeks = []
for timestamp_week in list_weeks:
    if timestamp_week.month == 12 and timestamp_week.day >= 22:
        list_shutdown_weeks.append(timestamp_week)
    if timestamp_week.month == 1 and timestamp_week.day <= 7:
        list_shutdown_weeks.append(timestamp_week)
    if timestamp_week.month == 2 and 8 <= timestamp_week.day <= 21:
        list_carnival_weeks.append(timestamp_week)

int_weeks_per_year = 52
for str_machine in list_machines:
    int_block_start = 0
    while int_block_start < len(list_weeks):
        int_block_end = int_block_start + int_weeks_per_year
        if int_block_end > len(list_weeks):
            int_block_end = len(list_weeks)
        int_block_size = int_block_end - int_block_start
        int_stops = MAINTENANCE_WEEKS_PER_YEAR
        if int_stops > int_block_size:
            int_stops = int_block_size
        array_stop_offsets = rng.choice(int_block_size, size=int_stops, replace=False)
        for int_offset in array_stop_offsets:
            timestamp_stop = list_weeks[int_block_start + int(int_offset)]
            dict_weekly_availability[str_machine][timestamp_stop] = float(rng.uniform(
                MAINTENANCE_AVAILABILITY_LOW, MAINTENANCE_AVAILABILITY_HIGH))
        int_block_start = int_block_end

for str_machine in list_machines:
    for timestamp_week in list_carnival_weeks:
        dict_weekly_availability[str_machine][timestamp_week] = CARNIVAL_AVAILABILITY
    for timestamp_week in list_shutdown_weeks:
        dict_weekly_availability[str_machine][timestamp_week] = COLLECTIVE_SHUTDOWN_AVAILABILITY

list_color_inventory = []
for int_index in range(len(list_products)):
    str_product = list_products[int_index]
    for str_color in dict_colors_by_product[str_product]:
        float_share = dict_color_mix[str_product][str_color]
        list_color_inventory.append({
            'MODELO': list_models[int_index],
            'TIPO': list_types[int_index],
            'COR': str_color,
            'ESTOQUE_INICIAL': dict_initial_inventory[str_product] * float_share,
        })

list_week_labels = []
for timestamp_week in list_weeks:
    list_week_labels.append(timestamp_week.strftime('%Y-%m-%d'))

dict_productivity_columns = {}
for str_machine in list_machines:
    list_column = []
    for str_product in list_products:
        if str_machine in dict_productivity[str_product]:
            list_column.append(dict_productivity[str_product][str_machine])
        else:
            list_column.append(np.nan)
    dict_productivity_columns[str_machine] = list_column
df_productivity = pd.DataFrame(dict_productivity_columns)
df_productivity.insert(0, 'TIPO', list_types)
df_productivity.insert(0, 'MODELO', list_models)

dict_demand_columns = {}
for int_week_index in range(len(list_weeks)):
    list_column = []
    for str_product in list_products:
        list_column.append(dict_weekly_demand[str_product][list_weeks[int_week_index]])
    dict_demand_columns[list_week_labels[int_week_index]] = list_column
df_demand = pd.DataFrame(dict_demand_columns)
df_demand.insert(0, 'TIPO', list_types)
df_demand.insert(0, 'MODELO', list_models)

list_opening_inventory = []
for str_product in list_products:
    list_opening_inventory.append(dict_initial_inventory[str_product])
str_previous_week = (timestamp_first_week - pd.Timedelta(days=7)).strftime('%Y-%m-%d')
df_inventory = pd.DataFrame({str_previous_week: list_opening_inventory})
df_inventory.insert(0, 'TIPO', list_types)
df_inventory.insert(0, 'MODELO', list_models)

list_costs_column = []
list_prices_column = []
for str_product in list_products:
    list_costs_column.append(dict_unit_cost[str_product])
    list_prices_column.append(dict_sale_price[str_product])
df_costs = pd.DataFrame({
    'MODELO': list_models,
    'TIPO': list_types,
    'CUSTO_UNITARIO': list_costs_column,
    'PRECO_VENDA': list_prices_column,
})

dict_availability_columns = {}
for str_machine in list_machines:
    list_column = []
    for timestamp_week in list_weeks:
        list_column.append(dict_weekly_availability[str_machine][timestamp_week])
    dict_availability_columns[str_machine] = list_column
df_availability = pd.DataFrame(dict_availability_columns)
df_availability.insert(0, 'DATA', list_week_labels)

df_order_headers = pd.DataFrame(list_order_headers)
df_order_items = pd.DataFrame(list_order_items)
df_color_inventory = pd.DataFrame(list_color_inventory)

list_min_lot_rows = []
for int_index in range(len(list_products)):
    list_min_lot_rows.append({
        'MODELO': list_models[int_index],
        'TIPO': list_types[int_index],
        'LOTE_MINIMO_KG': dict_min_lot[list_products[int_index]],
    })
df_min_lot = pd.DataFrame(list_min_lot_rows)

dict_color_rows = {}
for str_from in list_used_colors:
    dict_row = {}
    for str_to in list_used_colors:
        if str_from == str_to:
            dict_row[str_to] = np.nan
        else:
            float_time = dict_color_setup[(str_from, str_to)]
            if float_time is None:
                dict_row[str_to] = np.nan
            else:
                dict_row[str_to] = float_time
    dict_color_rows[str_from] = dict_row
df_color_setup = pd.DataFrame(dict_color_rows).T.reset_index().rename(columns={'index': 'DE'})

dict_form_rows = {}
for str_from in list_products:
    dict_row = {}
    for str_to in list_products:
        dict_row[str_to] = dict_form_setup[(str_from, str_to)]
    dict_form_rows[str_from] = dict_row
df_form_setup = pd.DataFrame(dict_form_rows).T.reset_index().rename(columns={'index': 'DE'})

with pd.ExcelWriter(OUTPUT_PATH, engine='openpyxl') as writer:
    df_productivity.to_excel(writer, sheet_name='Produtividade', index=False, startrow=1)
    df_demand.to_excel(writer, sheet_name='Demanda', index=False, startrow=1)
    df_inventory.to_excel(writer, sheet_name='Estoque', index=False, startrow=1)
    df_costs.to_excel(writer, sheet_name='Custos', index=False)
    df_availability.to_excel(writer, sheet_name='Disponibilidade de maquinas', index=False)
    df_order_headers.to_excel(writer, sheet_name='Pedidos', index=False)
    df_order_items.to_excel(writer, sheet_name='Itens_Pedido', index=False)
    df_color_inventory.to_excel(writer, sheet_name='Estoque_Cor', index=False)
    df_color_setup.to_excel(writer, sheet_name='De_Para_Cores', index=False)
    df_form_setup.to_excel(writer, sheet_name='De_Para_Formas', index=False)
    df_min_lot.to_excel(writer, sheet_name='Lote_Minimo', index=False)
    df_source_invoiced.to_excel(writer, sheet_name='Faturado', index=False, startrow=1)
    df_source_produced.to_excel(writer, sheet_name='Produzido', index=False, startrow=1)

print(f'gerado: {os.path.basename(OUTPUT_PATH)}')
print(f'produtos: {len(list_products)}  maquinas: {len(list_machines)}  semanas: {len(list_weeks)}')
print(f'pedidos: {len(list_order_headers)}  itens: {len(list_order_items)}  cores: {len(list_used_colors)}')
