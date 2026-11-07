import os

import pandas as pd

from processing.database import MASTER_TABLES, SNAPSHOT_TABLES, connect_database, fetch_rows

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, 'data')

REQUIRED_SHEETS = ['Produtividade', 'Demanda', 'Estoque', 'Custos', 'Disponibilidade de maquinas',
                   'Pedidos', 'Itens_Pedido', 'Estoque_Cor', 'De_Para_Cores', 'De_Para_Formas',
                   'Lote_Minimo']

SNAPSHOT_SHEETS = ['Demanda', 'Previsao_Manual', 'MAPE', 'Mix_Cores', 'Pedidos', 'Itens_Pedido',
                   'Estoque', 'Estoque_Cor', 'Forma_Inicial']


def list_data_files():
    list_files = []
    for str_name in sorted(os.listdir(DATA_DIR)):
        if str_name.endswith('.xlsx') and not str_name.startswith('~'):
            list_sheets = pd.ExcelFile(os.path.join(DATA_DIR, str_name)).sheet_names
            bool_complete = True
            for str_sheet in REQUIRED_SHEETS:
                if str_sheet not in list_sheets:
                    bool_complete = False
            if bool_complete:
                list_files.append(str_name)
    return list_files


def read_workbook_tables(source):
    excel_file = pd.ExcelFile(source)
    list_sheets = excel_file.sheet_names
    dict_tables = {}
    list_complete_tables = []
    dict_product_rows = {}
    list_product_order = []

    if 'Produtividade' in list_sheets:
        df_productivity = pd.read_excel(excel_file, sheet_name='Produtividade', header=1)
        list_machine_columns = []
        for str_column in df_productivity.columns:
            if str_column not in ('MODELO', 'TIPO'):
                list_machine_columns.append((str_column, str(int(float(str_column)))))
        dict_tables['productivity'] = []
        list_complete_tables.append('productivity')
        list_complete_tables.append('products')
        for int_row in range(len(df_productivity)):
            series_row = df_productivity.iloc[int_row]
            str_product = f"{series_row['MODELO']}-{series_row['TIPO']}"
            if str_product not in dict_product_rows:
                dict_product_rows[str_product] = {'product': str_product, 'model': str(series_row['MODELO']),
                                                  'type': str(series_row['TIPO'])}
                list_product_order.append(str_product)
            for tuple_column in list_machine_columns:
                float_rate = series_row[tuple_column[0]]
                if pd.notna(float_rate) and float_rate > 0:
                    dict_tables['productivity'].append({'product': str_product, 'machine': tuple_column[1],
                                                        'kg_per_hour': float(float_rate)})
        if 'Maquinas' not in list_sheets:
            dict_tables['machines'] = []
            for tuple_column in list_machine_columns:
                dict_tables['machines'].append({'machine': tuple_column[1]})

    if 'Custos' in list_sheets:
        df_costs = pd.read_excel(excel_file, sheet_name='Custos')
        for int_row in range(len(df_costs)):
            series_row = df_costs.iloc[int_row]
            str_product = f"{series_row['MODELO']}-{series_row['TIPO']}"
            if str_product not in dict_product_rows:
                dict_product_rows[str_product] = {'product': str_product, 'model': str(series_row['MODELO']),
                                                  'type': str(series_row['TIPO'])}
                list_product_order.append(str_product)
            dict_product_rows[str_product]['unit_cost'] = float(series_row['CUSTO_UNITARIO'])
            dict_product_rows[str_product]['sale_price'] = float(series_row['PRECO_VENDA'])

    if 'Lote_Minimo' in list_sheets:
        df_min_lot = pd.read_excel(excel_file, sheet_name='Lote_Minimo')
        for int_row in range(len(df_min_lot)):
            series_row = df_min_lot.iloc[int_row]
            str_product = f"{series_row['MODELO']}-{series_row['TIPO']}"
            if str_product not in dict_product_rows:
                dict_product_rows[str_product] = {'product': str_product, 'model': str(series_row['MODELO']),
                                                  'type': str(series_row['TIPO'])}
                list_product_order.append(str_product)
            dict_product_rows[str_product]['min_lot_kg'] = float(series_row['LOTE_MINIMO_KG'])

    if 'MTS_MTO' in list_sheets:
        df_classes = pd.read_excel(excel_file, sheet_name='MTS_MTO')
        dict_tables['sku_classes'] = []
        list_complete_tables.append('sku_classes')
        for int_row in range(len(df_classes)):
            series_row = df_classes.iloc[int_row]
            str_product = f"{series_row['MODELO']}-{series_row['TIPO']}"
            int_is_mts = 0
            if str(series_row['CLASSE']).strip().upper() == 'MTS':
                int_is_mts = 1
            if pd.isna(series_row['COR']) or str(series_row['COR']).strip() == '':
                if str_product not in dict_product_rows:
                    dict_product_rows[str_product] = {'product': str_product, 'model': str(series_row['MODELO']),
                                                      'type': str(series_row['TIPO'])}
                    list_product_order.append(str_product)
                dict_product_rows[str_product]['is_mts'] = int_is_mts
            else:
                dict_tables['sku_classes'].append({'product': str_product, 'color': str(series_row['COR']).strip(),
                                                   'is_mts': int_is_mts})

    if list_product_order:
        dict_tables['products'] = []
        for str_product in list_product_order:
            dict_tables['products'].append(dict_product_rows[str_product])

    if 'Maquinas' in list_sheets:
        df_machines = pd.read_excel(excel_file, sheet_name='Maquinas')
        dict_tables['machines'] = []
        list_complete_tables.append('machines')
        for int_row in range(len(df_machines)):
            series_row = df_machines.iloc[int_row]
            int_is_active = 0
            if str(series_row['ATIVA']).strip().upper() == 'SIM':
                int_is_active = 1
            dict_tables['machines'].append({'machine': str(int(float(series_row['MAQUINA']))),
                                            'is_active': int_is_active,
                                            'setup_hourly_cost': float(series_row['CUSTO_SETUP_HORA'])})

    if 'De_Para_Formas' in list_sheets:
        df_form_setup = pd.read_excel(excel_file, sheet_name='De_Para_Formas')
        dict_tables['form_setup'] = []
        list_complete_tables.append('form_setup')
        for int_row in range(len(df_form_setup)):
            series_row = df_form_setup.iloc[int_row]
            for str_column in df_form_setup.columns:
                if str_column != 'DE' and pd.notna(series_row[str_column]):
                    dict_tables['form_setup'].append({'from_product': str(series_row['DE']),
                                                      'to_product': str(str_column),
                                                      'hours': float(series_row[str_column])})

    if 'De_Para_Cores' in list_sheets:
        df_color_setup = pd.read_excel(excel_file, sheet_name='De_Para_Cores')
        dict_tables['color_setup'] = []
        list_complete_tables.append('color_setup')
        for int_row in range(len(df_color_setup)):
            series_row = df_color_setup.iloc[int_row]
            for str_column in df_color_setup.columns:
                if str_column != 'DE' and pd.notna(series_row[str_column]):
                    dict_tables['color_setup'].append({'from_color': str(series_row['DE']),
                                                       'to_color': str(str_column),
                                                       'hours': float(series_row[str_column])})

    if 'Disponibilidade de maquinas' in list_sheets:
        df_availability = pd.read_excel(excel_file, sheet_name='Disponibilidade de maquinas')
        dict_tables['availability'] = []
        list_complete_tables.append('availability')
        for int_row in range(len(df_availability)):
            series_row = df_availability.iloc[int_row]
            str_week = pd.Timestamp(series_row['DATA']).strftime('%Y-%m-%d')
            for str_column in df_availability.columns:
                if str_column != 'DATA':
                    dict_tables['availability'].append({'week': str_week,
                                                        'machine': str(int(float(str_column))),
                                                        'availability': float(series_row[str_column])})

    for str_sheet in ['Demanda', 'Previsao_Manual']:
        if str_sheet in list_sheets:
            df_forecast = pd.read_excel(excel_file, sheet_name=str_sheet, header=1)
            str_source = 'statistical'
            if str_sheet == 'Previsao_Manual':
                str_source = 'manual'
            if 'forecast' not in dict_tables:
                dict_tables['forecast'] = []
            for int_row in range(len(df_forecast)):
                series_row = df_forecast.iloc[int_row]
                str_product = f"{series_row['MODELO']}-{series_row['TIPO']}"
                for str_column in df_forecast.columns:
                    if str_column not in ('MODELO', 'TIPO') and pd.notna(series_row[str_column]):
                        dict_tables['forecast'].append({'product': str_product,
                                                        'week': pd.Timestamp(str_column).strftime('%Y-%m-%d'),
                                                        'quantity': float(series_row[str_column]),
                                                        'source': str_source})

    if 'MAPE' in list_sheets:
        df_accuracy = pd.read_excel(excel_file, sheet_name='MAPE')
        dict_tables['forecast_accuracy'] = []
        for int_row in range(len(df_accuracy)):
            series_row = df_accuracy.iloc[int_row]
            dict_tables['forecast_accuracy'].append({'product': f"{series_row['MODELO']}-{series_row['TIPO']}",
                                                     'mape': float(series_row['MAPE'])})

    if 'Mix_Cores' in list_sheets:
        df_mix = pd.read_excel(excel_file, sheet_name='Mix_Cores')
        dict_tables['color_mix'] = []
        for int_row in range(len(df_mix)):
            series_row = df_mix.iloc[int_row]
            dict_tables['color_mix'].append({'product': f"{series_row['MODELO']}-{series_row['TIPO']}",
                                             'color': str(series_row['COR']),
                                             'share': float(series_row['PARTICIPACAO'])})

    if 'Pedidos' in list_sheets:
        df_orders = pd.read_excel(excel_file, sheet_name='Pedidos')
        dict_tables['orders'] = []
        for int_row in range(len(df_orders)):
            series_row = df_orders.iloc[int_row]
            dict_tables['orders'].append({'order_id': str(series_row['PEDIDO_ID']),
                                          'customer': str(series_row['CLIENTE']),
                                          'issue_date': pd.Timestamp(series_row['DATA_EMISSAO']).strftime('%Y-%m-%d'),
                                          'due_date': pd.Timestamp(series_row['DATA_VENCIMENTO']).strftime('%Y-%m-%d')})

    if 'Itens_Pedido' in list_sheets:
        df_items = pd.read_excel(excel_file, sheet_name='Itens_Pedido')
        dict_tables['order_items'] = []
        for int_row in range(len(df_items)):
            series_row = df_items.iloc[int_row]
            dict_tables['order_items'].append({'order_id': str(series_row['PEDIDO_ID']),
                                               'product': f"{series_row['MODELO']}-{series_row['TIPO']}",
                                               'color': str(series_row['COR']),
                                               'quantity': float(series_row['QUANTIDADE'])})

    if 'Estoque' in list_sheets:
        df_stock = pd.read_excel(excel_file, sheet_name='Estoque', header=1)
        str_stock_column = None
        for str_column in df_stock.columns:
            if str_column not in ('MODELO', 'TIPO'):
                str_stock_column = str_column
        dict_tables['product_stock'] = []
        for int_row in range(len(df_stock)):
            series_row = df_stock.iloc[int_row]
            dict_tables['product_stock'].append({'product': f"{series_row['MODELO']}-{series_row['TIPO']}",
                                                 'quantity': float(series_row[str_stock_column])})

    if 'Estoque_Cor' in list_sheets:
        df_sku_stock = pd.read_excel(excel_file, sheet_name='Estoque_Cor')
        dict_tables['sku_stock'] = []
        for int_row in range(len(df_sku_stock)):
            series_row = df_sku_stock.iloc[int_row]
            dict_tables['sku_stock'].append({'product': f"{series_row['MODELO']}-{series_row['TIPO']}",
                                             'color': str(series_row['COR']),
                                             'quantity': float(series_row['ESTOQUE_INICIAL'])})

    if 'Forma_Inicial' in list_sheets:
        df_initial_form = pd.read_excel(excel_file, sheet_name='Forma_Inicial')
        dict_tables['initial_form'] = []
        for int_row in range(len(df_initial_form)):
            series_row = df_initial_form.iloc[int_row]
            str_initial_color = None
            if 'COR' in df_initial_form.columns and not pd.isna(series_row['COR']):
                str_initial_color = str(series_row['COR']).strip()
            dict_tables['initial_form'].append({'machine': str(int(float(series_row['MAQUINA']))),
                                                'product': f"{series_row['MODELO']}-{series_row['TIPO']}",
                                                'color': str_initial_color})

    return dict_tables, list_complete_tables, list_sheets


def fill_master_defaults(str_table, dict_row):
    dict_filled = dict(MASTER_TABLES[str_table]['defaults'])
    for str_column in dict_row:
        dict_filled[str_column] = dict_row[str_column]
    return dict_filled


def build_instance(dict_tables, str_source):
    list_products = []
    dict_unit_cost = {}
    dict_margin = {}
    dict_min_lot = {}
    dict_product_is_mts = {}
    for dict_row in dict_tables.get('products', []):
        str_product = dict_row['product']
        list_products.append(str_product)
        dict_unit_cost[str_product] = float(dict_row['unit_cost'])
        dict_margin[str_product] = float(dict_row['sale_price']) - float(dict_row['unit_cost'])
        dict_min_lot[str_product] = float(dict_row['min_lot_kg'])
        dict_product_is_mts[str_product] = bool(dict_row['is_mts'])

    dict_productivity = {}
    for str_product in list_products:
        dict_productivity[str_product] = {}
    for dict_row in dict_tables.get('productivity', []):
        if dict_row['product'] not in dict_productivity:
            dict_productivity[dict_row['product']] = {}
        dict_productivity[dict_row['product']][dict_row['machine']] = float(dict_row['kg_per_hour'])

    list_all_machines = []
    list_machines = []
    dict_setup_hourly_cost = {}
    for dict_row in dict_tables.get('machines', []):
        list_all_machines.append(dict_row['machine'])
        dict_setup_hourly_cost[dict_row['machine']] = float(dict_row['setup_hourly_cost'])
        if dict_row['is_active']:
            list_machines.append(dict_row['machine'])

    list_week_labels = []
    for dict_row in dict_tables.get('forecast', []):
        if dict_row['week'] not in list_week_labels:
            list_week_labels.append(dict_row['week'])
    list_week_labels.sort()
    list_weeks = []
    for str_week in list_week_labels:
        list_weeks.append(pd.Timestamp(str_week))

    dict_demand = {}
    for str_product in list_products:
        dict_demand[str_product] = {}
        for timestamp_week in list_weeks:
            dict_demand[str_product][timestamp_week] = 0.0
    for str_source_kind in ['statistical', 'manual']:
        for dict_row in dict_tables.get('forecast', []):
            if dict_row['source'] == str_source_kind:
                if dict_row['product'] not in dict_demand:
                    dict_demand[dict_row['product']] = {}
                    for timestamp_week in list_weeks:
                        dict_demand[dict_row['product']][timestamp_week] = 0.0
                dict_demand[dict_row['product']][pd.Timestamp(dict_row['week'])] = float(dict_row['quantity'])

    dict_initial_inventory = {}
    for str_product in list_products:
        dict_initial_inventory[str_product] = 0.0
    for dict_row in dict_tables.get('product_stock', []):
        dict_initial_inventory[dict_row['product']] = float(dict_row['quantity'])

    dict_availability = {}
    for str_machine in list_all_machines:
        dict_availability[str_machine] = {}
        for timestamp_week in list_weeks:
            dict_availability[str_machine][timestamp_week] = 1.0
    for dict_row in dict_tables.get('availability', []):
        if dict_row['machine'] not in dict_availability:
            dict_availability[dict_row['machine']] = {}
        dict_availability[dict_row['machine']][pd.Timestamp(dict_row['week'])] = float(dict_row['availability'])

    dict_items_by_order = {}
    for dict_row in dict_tables.get('order_items', []):
        if dict_row['order_id'] not in dict_items_by_order:
            dict_items_by_order[dict_row['order_id']] = []
        dict_items_by_order[dict_row['order_id']].append({
            'product': dict_row['product'],
            'color': dict_row['color'],
            'sku': f"{dict_row['product']}-{dict_row['color']}",
            'quantity': float(dict_row['quantity']),
        })
    list_orders = []
    for dict_row in dict_tables.get('orders', []):
        list_items = []
        if dict_row['order_id'] in dict_items_by_order:
            list_items = dict_items_by_order[dict_row['order_id']]
        list_orders.append({
            'order_id': dict_row['order_id'],
            'customer': dict_row['customer'],
            'issue_date': pd.Timestamp(dict_row['issue_date']),
            'due_date': pd.Timestamp(dict_row['due_date']),
            'items': list_items,
        })

    dict_color_initial_stock = {}
    for dict_row in dict_tables.get('sku_stock', []):
        dict_color_initial_stock[f"{dict_row['product']}-{dict_row['color']}"] = float(dict_row['quantity'])

    dict_color_setup = {}
    for dict_row in dict_tables.get('color_setup', []):
        dict_color_setup[(dict_row['from_color'], dict_row['to_color'])] = float(dict_row['hours'])

    dict_form_setup = {}
    for dict_row in dict_tables.get('form_setup', []):
        dict_form_setup[(dict_row['from_product'], dict_row['to_product'])] = float(dict_row['hours'])

    dict_colors_by_product = {}
    list_color_sources = []
    for dict_row in dict_tables.get('sku_stock', []):
        list_color_sources.append((dict_row['product'], dict_row['color']))
    for dict_order in list_orders:
        for dict_item in dict_order['items']:
            list_color_sources.append((dict_item['product'], dict_item['color']))
    for dict_row in dict_tables.get('color_mix', []):
        list_color_sources.append((dict_row['product'], dict_row['color']))
    for tuple_source in list_color_sources:
        if tuple_source[0] not in dict_colors_by_product:
            dict_colors_by_product[tuple_source[0]] = []
        if tuple_source[1] not in dict_colors_by_product[tuple_source[0]]:
            dict_colors_by_product[tuple_source[0]].append(tuple_source[1])

    dict_class_overrides = {}
    for dict_row in dict_tables.get('sku_classes', []):
        dict_class_overrides[f"{dict_row['product']}-{dict_row['color']}"] = bool(dict_row['is_mts'])
    dict_sku_is_mts = {}
    for str_product in dict_colors_by_product:
        for str_color in dict_colors_by_product[str_product]:
            str_sku = f'{str_product}-{str_color}'
            if str_sku in dict_class_overrides:
                dict_sku_is_mts[str_sku] = dict_class_overrides[str_sku]
            elif str_product in dict_product_is_mts:
                dict_sku_is_mts[str_sku] = dict_product_is_mts[str_product]
            else:
                dict_sku_is_mts[str_sku] = True

    dict_color_mix = {}
    for dict_row in dict_tables.get('color_mix', []):
        if dict_row['product'] not in dict_color_mix:
            dict_color_mix[dict_row['product']] = {}
        dict_color_mix[dict_row['product']][dict_row['color']] = float(dict_row['share'])
    for str_product in dict_colors_by_product:
        if str_product not in dict_color_mix:
            dict_color_mix[str_product] = {}
            float_total = 0.0
            for dict_order in list_orders:
                for dict_item in dict_order['items']:
                    if dict_item['product'] == str_product:
                        if dict_item['color'] not in dict_color_mix[str_product]:
                            dict_color_mix[str_product][dict_item['color']] = 0.0
                        dict_color_mix[str_product][dict_item['color']] += dict_item['quantity']
                        float_total += dict_item['quantity']
            if float_total > 0.0:
                for str_color in dict_color_mix[str_product]:
                    dict_color_mix[str_product][str_color] = dict_color_mix[str_product][str_color] / float_total
            else:
                list_colors = dict_colors_by_product[str_product]
                for str_color in list_colors:
                    dict_color_mix[str_product][str_color] = 1.0 / len(list_colors)

    dict_mape = {}
    for str_product in list_products:
        dict_mape[str_product] = 0.0
    for dict_row in dict_tables.get('forecast_accuracy', []):
        dict_mape[dict_row['product']] = float(dict_row['mape'])

    dict_initial_form = {}
    dict_initial_color = {}
    for dict_row in dict_tables.get('initial_form', []):
        dict_initial_form[dict_row['machine']] = dict_row['product']
        if dict_row['color'] is not None:
            dict_initial_color[dict_row['machine']] = dict_row['color']

    return {
        'source': str_source,
        'products': list_products,
        'machines': list_machines,
        'all_machines': list_all_machines,
        'weeks': list_weeks,
        'productivity': dict_productivity,
        'demand': dict_demand,
        'initial_inventory': dict_initial_inventory,
        'unit_cost': dict_unit_cost,
        'margin': dict_margin,
        'availability': dict_availability,
        'orders': list_orders,
        'color_initial_stock': dict_color_initial_stock,
        'color_setup': dict_color_setup,
        'form_setup': dict_form_setup,
        'min_lot': dict_min_lot,
        'colors_by_product': dict_colors_by_product,
        'setup_hourly_cost': dict_setup_hourly_cost,
        'sku_is_mts': dict_sku_is_mts,
        'color_mix': dict_color_mix,
        'mape': dict_mape,
        'initial_form': dict_initial_form,
        'initial_color': dict_initial_color,
    }


def load_instance(str_data_file):
    dict_tables, list_complete_tables, list_sheets = read_workbook_tables(str_data_file)
    for str_table in MASTER_TABLES:
        if str_table in dict_tables:
            list_filled_rows = []
            for dict_row in dict_tables[str_table]:
                list_filled_rows.append(fill_master_defaults(str_table, dict_row))
            dict_tables[str_table] = list_filled_rows
    return build_instance(dict_tables, os.path.basename(str_data_file))


def load_snapshot_instance(int_snapshot_id):
    connection = connect_database()
    dict_tables = {}
    for str_table in MASTER_TABLES:
        dict_tables[str_table] = fetch_rows(connection, f'SELECT * FROM {str_table} ORDER BY rowid', ())
    for str_table in SNAPSHOT_TABLES:
        dict_tables[str_table] = fetch_rows(
            connection, f'SELECT * FROM {str_table} WHERE snapshot_id = ? ORDER BY rowid', (int_snapshot_id,))
    list_snapshot_rows = fetch_rows(connection, 'SELECT * FROM snapshots WHERE snapshot_id = ?', (int_snapshot_id,))
    connection.close()
    dict_snapshot = list_snapshot_rows[0]
    str_source = f"#{dict_snapshot['snapshot_id']} {dict_snapshot['source_file']} ({dict_snapshot['created_at']})"
    dict_instance = build_instance(dict_tables, str_source)
    dict_instance['snapshot_id'] = int_snapshot_id
    return dict_instance
