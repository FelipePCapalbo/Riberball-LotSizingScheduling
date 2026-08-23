import os
import numpy as np
import pandas as pd

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(ROOT_DIR, 'data')

COLOR_POOL = ['AZUL', 'VERMELHO', 'VERDE', 'BRANCO', 'AMARELO', 'PRETO']

PROFILES = {
    'micro': {
        'n_products': 2, 'n_machines': 3, 'n_weeks': 8,
        'prod_density': 0.90, 'demand_level': 0.50, 'demand_cv': 0.10, 'seasonality_amp': 0.0,
        'initial_coverage_weeks': 1.0, 'cost_min': 10.0, 'cost_max': 10.0,
        'margin_min': 0.30, 'margin_max': 0.30,
        'n_stops': 0, 'avail_mean': 1.00,
        'min_colors': 2, 'max_colors': 2,
        'color_block_prob': 0.0, 'color_setup_min': 0.5, 'color_setup_max': 1.0,
        'form_setup_min': 3.0, 'form_setup_max': 3.0,
        'confirmed_fraction_0': 0.95, 'order_decay_tau': 4.0,
        'min_items_per_order': 1, 'max_items_per_order': 2,
        'min_lot_fraction': 0.05,
    },
    'pequeno': {
        'n_products': 4, 'n_machines': 6, 'n_weeks': 13,
        'prod_density': 0.70, 'demand_level': 0.60, 'demand_cv': 0.15, 'seasonality_amp': 0.0,
        'initial_coverage_weeks': 1.0, 'cost_min': 5.0, 'cost_max': 20.0,
        'margin_min': 0.20, 'margin_max': 0.45,
        'n_stops': 0, 'avail_mean': 1.00,
        'min_colors': 2, 'max_colors': 3,
        'color_block_prob': 0.10, 'color_setup_min': 0.5, 'color_setup_max': 1.5,
        'form_setup_min': 3.0, 'form_setup_max': 5.0,
        'confirmed_fraction_0': 0.95, 'order_decay_tau': 5.0,
        'min_items_per_order': 1, 'max_items_per_order': 3,
        'min_lot_fraction': 0.05,
    },
    'medio': {
        'n_products': 8, 'n_machines': 12, 'n_weeks': 13,
        'prod_density': 0.50, 'demand_level': 0.75, 'demand_cv': 0.20, 'seasonality_amp': 0.25,
        'initial_coverage_weeks': 1.0, 'cost_min': 5.0, 'cost_max': 20.0,
        'margin_min': 0.20, 'margin_max': 0.45,
        'n_stops': 1, 'avail_mean': 0.90,
        'min_colors': 2, 'max_colors': 4,
        'color_block_prob': 0.20, 'color_setup_min': 0.5, 'color_setup_max': 2.0,
        'form_setup_min': 3.0, 'form_setup_max': 7.0,
        'confirmed_fraction_0': 0.95, 'order_decay_tau': 5.0,
        'min_items_per_order': 1, 'max_items_per_order': 4,
        'min_lot_fraction': 0.08,
    },
    'grande': {
        'n_products': 12, 'n_machines': 20, 'n_weeks': 26,
        'prod_density': 0.40, 'demand_level': 0.85, 'demand_cv': 0.25, 'seasonality_amp': 0.35,
        'initial_coverage_weeks': 0.5, 'cost_min': 5.0, 'cost_max': 30.0,
        'margin_min': 0.20, 'margin_max': 0.50,
        'n_stops': 2, 'avail_mean': 0.85,
        'min_colors': 2, 'max_colors': 4,
        'color_block_prob': 0.25, 'color_setup_min': 0.5, 'color_setup_max': 2.0,
        'form_setup_min': 3.0, 'form_setup_max': 7.0,
        'confirmed_fraction_0': 0.95, 'order_decay_tau': 6.0,
        'min_items_per_order': 1, 'max_items_per_order': 4,
        'min_lot_fraction': 0.08,
    },
    'real': {
        'n_products': 17, 'n_machines': 28, 'n_weeks': 26,
        'prod_density': 0.40, 'demand_level': 0.90, 'demand_cv': 0.30, 'seasonality_amp': 0.40,
        'initial_coverage_weeks': 0.5, 'cost_min': 5.0, 'cost_max': 30.0,
        'margin_min': 0.20, 'margin_max': 0.50,
        'n_stops': 2, 'avail_mean': 0.80,
        'min_colors': 2, 'max_colors': 4,
        'color_block_prob': 0.25, 'color_setup_min': 0.5, 'color_setup_max': 2.0,
        'form_setup_min': 3.0, 'form_setup_max': 7.0,
        'confirmed_fraction_0': 0.95, 'order_decay_tau': 8.0,
        'min_items_per_order': 1, 'max_items_per_order': 4,
        'min_lot_fraction': 0.08,
    },
}

START_WEEK = pd.Timestamp('2024-01-01')
SHIFTS_PER_DAY = 3
HOURS_PER_SHIFT = 8
WORKING_DAYS_PER_WEEK = 6


def generate_instance(str_name, dict_profile, int_seed):
    rng = np.random.default_rng(int_seed)

    int_products = dict_profile['n_products']
    int_machines = dict_profile['n_machines']
    int_weeks = dict_profile['n_weeks']
    float_hours_per_week = WORKING_DAYS_PER_WEEK * SHIFTS_PER_DAY * HOURS_PER_SHIFT
    float_hours_per_shift = float(HOURS_PER_SHIFT)

    list_models = []
    list_types = []
    list_products = []
    for int_index in range(int_products):
        str_model = f'P{int_index + 1:02d}'
        str_type = 'LISO'
        list_models.append(str_model)
        list_types.append(str_type)
        list_products.append(f'{str_model}-{str_type}')

    list_machines = []
    for int_index in range(int_machines):
        list_machines.append(str(int_index + 1))

    list_weeks = []
    for int_index in range(int_weeks):
        list_weeks.append(START_WEEK + pd.Timedelta(days=7 * int_index))

    matrix_compatible = rng.random((int_products, int_machines)) < dict_profile['prod_density']
    for int_i in range(int_products):
        bool_has_machine = False
        for int_j in range(int_machines):
            if matrix_compatible[int_i, int_j]:
                bool_has_machine = True
        if not bool_has_machine:
            matrix_compatible[int_i, rng.integers(0, int_machines)] = True
    matrix_rates = rng.uniform(20.0, 80.0, (int_products, int_machines))
    matrix_rates = np.where(matrix_compatible, matrix_rates, np.nan)

    float_average_rate = float(np.nanmean(matrix_rates))
    float_weekly_capacity = int_machines * float_hours_per_week * float_average_rate
    float_base_demand = float_weekly_capacity * dict_profile['demand_level'] / int_products

    matrix_demand = np.zeros((int_products, int_weeks))
    for int_i in range(int_products):
        for int_t in range(int_weeks):
            float_seasonal = 1.0 + dict_profile['seasonality_amp'] * np.sin(2 * np.pi * int_t / 52.0)
            float_noise = rng.normal(1.0, dict_profile['demand_cv'])
            if float_noise < 0.1:
                float_noise = 0.1
            matrix_demand[int_i, int_t] = float_base_demand * float_seasonal * float_noise

    list_unit_costs = []
    list_sale_prices = []
    for int_i in range(int_products):
        float_cost = rng.uniform(dict_profile['cost_min'], dict_profile['cost_max'])
        float_margin_rate = rng.uniform(dict_profile['margin_min'], dict_profile['margin_max'])
        list_unit_costs.append(float_cost)
        list_sale_prices.append(float_cost * (1.0 + float_margin_rate))

    matrix_availability = np.ones((int_machines, int_weeks))
    for int_j in range(int_machines):
        if dict_profile['n_stops'] > 0:
            array_stop_weeks = rng.choice(int_weeks, size=dict_profile['n_stops'], replace=False)
            for int_t in array_stop_weeks:
                float_low = max(0.50, dict_profile['avail_mean'] - 0.20)
                float_high = min(0.99, dict_profile['avail_mean'] + 0.05)
                matrix_availability[int_j, int_t] = rng.uniform(float_low, float_high)

    dict_color_mix = {}
    for int_i in range(int_products):
        int_colors = int(rng.integers(dict_profile['min_colors'], dict_profile['max_colors'] + 1))
        array_colors = rng.choice(COLOR_POOL, size=int_colors, replace=False)
        array_weights = rng.dirichlet(np.ones(int_colors))
        dict_mix = {}
        for int_c in range(int_colors):
            dict_mix[str(array_colors[int_c])] = float(array_weights[int_c])
        dict_color_mix[list_products[int_i]] = dict_mix

    list_used_colors = []
    for str_product in dict_color_mix:
        for str_color in dict_color_mix[str_product]:
            if str_color not in list_used_colors:
                list_used_colors.append(str_color)
    list_used_colors = sorted(list_used_colors)

    dict_color_setup = {}
    for str_from in list_used_colors:
        for str_to in list_used_colors:
            if str_from != str_to:
                if rng.random() < dict_profile['color_block_prob']:
                    dict_color_setup[(str_from, str_to)] = None
                else:
                    dict_color_setup[(str_from, str_to)] = float(rng.uniform(
                        dict_profile['color_setup_min'], dict_profile['color_setup_max']))

    for str_color in list_used_colors:
        int_out = 0
        int_in = 0
        for str_other in list_used_colors:
            if str_other != str_color:
                if dict_color_setup[(str_color, str_other)] is not None:
                    int_out += 1
                if dict_color_setup[(str_other, str_color)] is not None:
                    int_in += 1
        if int_out == 0:
            for str_other in list_used_colors:
                if str_other != str_color and int_out == 0:
                    dict_color_setup[(str_color, str_other)] = float(rng.uniform(
                        dict_profile['color_setup_min'], dict_profile['color_setup_max']))
                    int_out = 1
        if int_in == 0:
            for str_other in list_used_colors:
                if str_other != str_color and int_in == 0:
                    dict_color_setup[(str_other, str_color)] = float(rng.uniform(
                        dict_profile['color_setup_min'], dict_profile['color_setup_max']))
                    int_in = 1

    dict_form_setup = {}
    for str_from in list_products:
        for str_to in list_products:
            if str_from == str_to:
                dict_form_setup[(str_from, str_to)] = 0.0
            else:
                dict_form_setup[(str_from, str_to)] = float(rng.uniform(
                    dict_profile['form_setup_min'], dict_profile['form_setup_max']))

    list_order_headers = []
    list_order_items = []
    int_order_counter = 0
    matrix_confirmed = np.zeros((int_products, int_weeks))
    for int_t in range(int_weeks):
        float_confirmed_fraction = dict_profile['confirmed_fraction_0'] * np.exp(
            -int_t / dict_profile['order_decay_tau'])
        list_pending_lines = []
        for int_i in range(int_products):
            float_confirmed_mass = matrix_demand[int_i, int_t] * float_confirmed_fraction
            matrix_confirmed[int_i, int_t] = float_confirmed_mass
            dict_mix = dict_color_mix[list_products[int_i]]
            for str_color in dict_mix:
                float_color_mass = float_confirmed_mass * dict_mix[str_color]
                if float_color_mass > 1.0:
                    int_chunks = int(rng.integers(1, 4))
                    array_split = rng.dirichlet(np.ones(int_chunks))
                    for int_chunk in range(int_chunks):
                        list_pending_lines.append({
                            'model': list_models[int_i],
                            'type': list_types[int_i],
                            'color': str_color,
                            'quantity': float_color_mass * float(array_split[int_chunk]),
                        })
        rng.shuffle(list_pending_lines)

        int_cursor = 0
        while int_cursor < len(list_pending_lines):
            int_items = int(rng.integers(dict_profile['min_items_per_order'],
                                         dict_profile['max_items_per_order'] + 1))
            int_end = int_cursor + int_items
            if int_end > len(list_pending_lines):
                int_end = len(list_pending_lines)
            int_order_counter += 1
            str_order_id = f'OC{int_order_counter:05d}'
            int_due_offset = int(rng.integers(0, WORKING_DAYS_PER_WEEK))
            timestamp_due = list_weeks[int_t] + pd.Timedelta(days=int_due_offset)
            timestamp_issue = timestamp_due - pd.Timedelta(days=int(rng.integers(7, 31)))
            list_order_headers.append({
                'PEDIDO_ID': str_order_id,
                'CLIENTE': f'CLI{int(rng.integers(1, 21)):02d}',
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

    array_initial_inventory = matrix_demand.mean(axis=1) * dict_profile['initial_coverage_weeks']

    dict_confirmed_color_share = {}
    for dict_item in list_order_items:
        str_sku = f"{dict_item['MODELO']}-{dict_item['TIPO']}-{dict_item['COR']}"
        if str_sku not in dict_confirmed_color_share:
            dict_confirmed_color_share[str_sku] = 0.0
        dict_confirmed_color_share[str_sku] += dict_item['QUANTIDADE']

    list_color_inventory = []
    for int_i in range(int_products):
        str_product = list_products[int_i]
        dict_mix = dict_color_mix[str_product]
        float_product_confirmed = 0.0
        for str_color in dict_mix:
            str_sku = f'{str_product}-{str_color}'
            if str_sku in dict_confirmed_color_share:
                float_product_confirmed += dict_confirmed_color_share[str_sku]
        for str_color in dict_mix:
            str_sku = f'{str_product}-{str_color}'
            if float_product_confirmed > 0.0 and str_sku in dict_confirmed_color_share:
                float_share = dict_confirmed_color_share[str_sku] / float_product_confirmed
            else:
                float_share = dict_mix[str_color]
            list_color_inventory.append({
                'MODELO': list_models[int_i],
                'TIPO': list_types[int_i],
                'COR': str_color,
                'ESTOQUE_INICIAL': array_initial_inventory[int_i] * float_share,
            })

    list_min_lot = []
    for int_i in range(int_products):
        float_shift_capacity = float('inf')
        for int_j in range(int_machines):
            if matrix_compatible[int_i, int_j]:
                float_candidate = matrix_rates[int_i, int_j] * float_hours_per_shift
                if float_candidate < float_shift_capacity:
                    float_shift_capacity = float_candidate
        float_lot = matrix_demand[int_i].mean() * dict_profile['min_lot_fraction']
        if float_lot > 0.5 * float_shift_capacity:
            float_lot = 0.5 * float_shift_capacity
        list_min_lot.append({
            'MODELO': list_models[int_i],
            'TIPO': list_types[int_i],
            'LOTE_MINIMO_KG': float_lot,
        })

    list_week_labels = []
    for timestamp_week in list_weeks:
        list_week_labels.append(timestamp_week.strftime('%Y-%m-%d'))

    df_productivity = pd.DataFrame(matrix_rates, columns=list_machines)
    df_productivity.insert(0, 'TIPO', list_types)
    df_productivity.insert(0, 'MODELO', list_models)

    df_demand = pd.DataFrame(matrix_demand, columns=list_week_labels)
    df_demand.insert(0, 'TIPO', list_types)
    df_demand.insert(0, 'MODELO', list_models)

    str_previous_week = (START_WEEK - pd.Timedelta(days=7)).strftime('%Y-%m-%d')
    df_inventory = pd.DataFrame({str_previous_week: array_initial_inventory})
    df_inventory.insert(0, 'TIPO', list_types)
    df_inventory.insert(0, 'MODELO', list_models)

    df_costs = pd.DataFrame({
        'MODELO': list_models,
        'TIPO': list_types,
        'CUSTO_UNITARIO': list_unit_costs,
        'PRECO_VENDA': list_sale_prices,
    })

    df_availability = pd.DataFrame(matrix_availability.T, columns=list_machines)
    df_availability.insert(0, 'DATA', list_week_labels)

    df_order_headers = pd.DataFrame(list_order_headers)
    df_order_items = pd.DataFrame(list_order_items)
    df_color_inventory = pd.DataFrame(list_color_inventory)
    df_min_lot = pd.DataFrame(list_min_lot)

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

    str_output = os.path.join(
        DATA_DIR, f'instance_{str_name}_P{int_products}_M{int_machines}_T{int_weeks}.xlsx')
    with pd.ExcelWriter(str_output, engine='openpyxl') as writer:
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

    return str_output, matrix_demand, matrix_confirmed, list_products, list_weeks


if __name__ == '__main__':
    for str_profile_name in PROFILES:
        str_path, _, _, _, _ = generate_instance(str_profile_name, PROFILES[str_profile_name], 42)
        print(f'gerado: {os.path.basename(str_path)}')
