import os
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, 'data')


def list_data_files():
    list_files = []
    for str_name in sorted(os.listdir(DATA_DIR)):
        if str_name.endswith('.xlsx') and not str_name.startswith('~'):
            list_files.append(str_name)
    return list_files


def load_instance(str_data_file):
    df_productivity = pd.read_excel(str_data_file, sheet_name='Produtividade', header=1)
    df_demand = pd.read_excel(str_data_file, sheet_name='Demanda', header=1)
    df_inventory = pd.read_excel(str_data_file, sheet_name='Estoque', header=1)
    df_costs = pd.read_excel(str_data_file, sheet_name='Custos')
    df_availability = pd.read_excel(str_data_file, sheet_name='Disponibilidade de maquinas')
    df_order_headers = pd.read_excel(str_data_file, sheet_name='Pedidos')
    df_order_items = pd.read_excel(str_data_file, sheet_name='Itens_Pedido')
    df_color_inventory = pd.read_excel(str_data_file, sheet_name='Estoque_Cor')
    df_color_setup = pd.read_excel(str_data_file, sheet_name='De_Para_Cores')
    df_form_setup = pd.read_excel(str_data_file, sheet_name='De_Para_Formas')
    df_min_lot = pd.read_excel(str_data_file, sheet_name='Lote_Minimo')

    list_products = []
    dict_productivity = {}
    list_machines = []
    for str_column in df_productivity.columns:
        if str_column not in ('MODELO', 'TIPO'):
            list_machines.append(str(int(float(str_column))))
    for int_row in range(len(df_productivity)):
        series_row = df_productivity.iloc[int_row]
        str_product = f"{series_row['MODELO']}-{series_row['TIPO']}"
        list_products.append(str_product)
        dict_productivity[str_product] = {}
        int_column = 0
        for str_column in df_productivity.columns:
            if str_column not in ('MODELO', 'TIPO'):
                float_rate = series_row[str_column]
                if pd.notna(float_rate) and float_rate > 0:
                    dict_productivity[str_product][list_machines[int_column]] = float(float_rate)
                int_column += 1

    list_weeks = []
    for str_column in df_demand.columns:
        if str_column not in ('MODELO', 'TIPO'):
            list_weeks.append(pd.Timestamp(str_column))

    dict_demand = {}
    for int_row in range(len(df_demand)):
        series_row = df_demand.iloc[int_row]
        str_product = f"{series_row['MODELO']}-{series_row['TIPO']}"
        dict_demand[str_product] = {}
        int_column = 0
        for str_column in df_demand.columns:
            if str_column not in ('MODELO', 'TIPO'):
                dict_demand[str_product][list_weeks[int_column]] = float(series_row[str_column])
                int_column += 1

    dict_initial_inventory = {}
    str_inventory_column = None
    for str_column in df_inventory.columns:
        if str_column not in ('MODELO', 'TIPO'):
            str_inventory_column = str_column
    for int_row in range(len(df_inventory)):
        series_row = df_inventory.iloc[int_row]
        str_product = f"{series_row['MODELO']}-{series_row['TIPO']}"
        dict_initial_inventory[str_product] = float(series_row[str_inventory_column])

    dict_unit_cost = {}
    dict_margin = {}
    for int_row in range(len(df_costs)):
        series_row = df_costs.iloc[int_row]
        str_product = f"{series_row['MODELO']}-{series_row['TIPO']}"
        dict_unit_cost[str_product] = float(series_row['CUSTO_UNITARIO'])
        dict_margin[str_product] = float(series_row['PRECO_VENDA']) - float(series_row['CUSTO_UNITARIO'])

    dict_availability = {}
    for str_machine in list_machines:
        dict_availability[str_machine] = {}
    for int_row in range(len(df_availability)):
        series_row = df_availability.iloc[int_row]
        timestamp_week = pd.Timestamp(series_row['DATA'])
        int_column = 0
        for str_column in df_availability.columns:
            if str_column != 'DATA':
                dict_availability[list_machines[int_column]][timestamp_week] = float(series_row[str_column])
                int_column += 1

    dict_items_by_order = {}
    for int_row in range(len(df_order_items)):
        series_row = df_order_items.iloc[int_row]
        str_order_id = series_row['PEDIDO_ID']
        str_product = f"{series_row['MODELO']}-{series_row['TIPO']}"
        if str_order_id not in dict_items_by_order:
            dict_items_by_order[str_order_id] = []
        dict_items_by_order[str_order_id].append({
            'product': str_product,
            'color': series_row['COR'],
            'sku': f"{str_product}-{series_row['COR']}",
            'quantity': float(series_row['QUANTIDADE']),
        })

    list_orders = []
    for int_row in range(len(df_order_headers)):
        series_row = df_order_headers.iloc[int_row]
        str_order_id = series_row['PEDIDO_ID']
        list_orders.append({
            'order_id': str_order_id,
            'customer': series_row['CLIENTE'],
            'issue_date': pd.Timestamp(series_row['DATA_EMISSAO']),
            'due_date': pd.Timestamp(series_row['DATA_VENCIMENTO']),
            'items': dict_items_by_order[str_order_id],
        })

    dict_color_initial_stock = {}
    for int_row in range(len(df_color_inventory)):
        series_row = df_color_inventory.iloc[int_row]
        str_sku = f"{series_row['MODELO']}-{series_row['TIPO']}-{series_row['COR']}"
        dict_color_initial_stock[str_sku] = float(series_row['ESTOQUE_INICIAL'])

    dict_color_setup = {}
    for int_row in range(len(df_color_setup)):
        series_row = df_color_setup.iloc[int_row]
        for str_column in df_color_setup.columns:
            if str_column != 'DE':
                float_time = series_row[str_column]
                if pd.notna(float_time):
                    dict_color_setup[(series_row['DE'], str_column)] = float(float_time)

    dict_form_setup = {}
    for int_row in range(len(df_form_setup)):
        series_row = df_form_setup.iloc[int_row]
        for str_column in df_form_setup.columns:
            if str_column != 'DE':
                float_time = series_row[str_column]
                if pd.notna(float_time):
                    dict_form_setup[(series_row['DE'], str_column)] = float(float_time)

    dict_min_lot = {}
    for int_row in range(len(df_min_lot)):
        series_row = df_min_lot.iloc[int_row]
        str_product = f"{series_row['MODELO']}-{series_row['TIPO']}"
        dict_min_lot[str_product] = float(series_row['LOTE_MINIMO_KG'])

    dict_colors_by_product = {}
    for str_sku in dict_color_initial_stock:
        list_parts = str_sku.split('-')
        str_product = f'{list_parts[0]}-{list_parts[1]}'
        if str_product not in dict_colors_by_product:
            dict_colors_by_product[str_product] = []
        if list_parts[2] not in dict_colors_by_product[str_product]:
            dict_colors_by_product[str_product].append(list_parts[2])
    for dict_order in list_orders:
        for dict_item in dict_order['items']:
            str_product = dict_item['product']
            if str_product not in dict_colors_by_product:
                dict_colors_by_product[str_product] = []
            if dict_item['color'] not in dict_colors_by_product[str_product]:
                dict_colors_by_product[str_product].append(dict_item['color'])

    return {
        'data_file': str_data_file,
        'products': list_products,
        'machines': list_machines,
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
    }
