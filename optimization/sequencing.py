import itertools
import time

from optimization.daily_model import build_daily_result


def evaluate_sequence(dict_scenario, dict_plan, dict_state, list_machines, bool_check_stock):
    dict_violation = {
        'seq_capacidade': 0.0,
        'seq_forma': 0.0,
        'seq_lote': 0.0,
        'seq_antecipacao': 0.0,
        'seq_armazem': 0.0,
    }
    int_last_shift = len(dict_scenario['shifts']) - 1
    dict_cells = {}
    dict_run_color_hours = {}
    dict_run_previous_color = {}
    float_setup_cost = 0.0
    float_weighted_hours = 0.0

    for str_machine in list_machines:
        str_entry = '0'
        if str_machine in dict_scenario['initial_form'] and str_machine in dict_scenario['initial_color']:
            str_entry = f"{dict_scenario['initial_form'][str_machine]}-{dict_scenario['initial_color'][str_machine]}"
        float_hourly_cost = dict_scenario['setup_hourly_cost'][str_machine]
        float_previous_pending = 0.0
        for dict_shift in dict_scenario['shifts']:
            int_shift = dict_shift['index']
            tuple_cell = (str_machine, int_shift)
            str_form = dict_plan['form'][tuple_cell]
            float_pending = dict_plan['pending'][tuple_cell]
            float_form_hours = float_previous_pending - float_pending
            if tuple_cell in dict_plan['form_change']:
                str_entry = None
                float_form_hours += dict_plan['form_change'][tuple_cell][1]
            float_previous_pending = float_pending

            str_previous = str_entry
            float_production_hours = 0.0
            float_color_hours = 0.0
            float_form_violation = 0.0
            float_lot_violation = 0.0
            for str_sku in dict_state['sequence'][tuple_cell]:
                tuple_run = (str_sku, str_machine, int_shift)
                float_quantity = dict_state['quantity'][tuple_run]
                str_product = dict_scenario['product_of_sku'][str_sku]
                if str_machine in dict_scenario['productivity'][str_product]:
                    float_hours = float_quantity / dict_scenario['productivity'][str_product][str_machine]
                    float_production_hours += float_hours
                    float_weighted_hours += (int_shift + 1) * float_hours
                    if str_product != str_form or float_pending > 0.0:
                        float_form_violation += float_quantity
                else:
                    float_form_violation += float_quantity

                float_change = 0.0
                if str_previous is None:
                    dict_run_previous_color[tuple_run] = '-'
                else:
                    if str_previous == '0':
                        str_previous_color = '0'
                    else:
                        str_previous_color = dict_scenario['color_of_sku'][str_previous]
                    dict_run_previous_color[tuple_run] = str_previous_color
                    float_change = dict_scenario['color_setup'][(str_previous_color,
                                                                 dict_scenario['color_of_sku'][str_sku])]
                dict_run_color_hours[tuple_run] = float_change
                float_color_hours += float_change

                float_min_lot = dict_scenario['min_lot'][str_product]
                if float_min_lot - float_quantity > 1e-4:
                    float_lot_violation += float_min_lot - float_quantity
                str_previous = str_sku

            if len(dict_state['sequence'][tuple_cell]) > 0:
                str_entry = str_previous

            float_available = dict_scenario['shift_capacity'][tuple_cell]
            float_used = float_production_hours + float_color_hours + float_form_hours
            float_capacity_violation = 0.0
            if float_used - float_available > 1e-6:
                float_capacity_violation = float_used - float_available
            float_setup_cost += float_hourly_cost * float_color_hours

            dict_violation['seq_capacidade'] += float_capacity_violation
            dict_violation['seq_forma'] += float_form_violation
            dict_violation['seq_lote'] += float_lot_violation
            dict_cells[tuple_cell] = {
                'form': str_form,
                'production_hours': float_production_hours,
                'color_setup_hours': float_color_hours,
                'form_setup_hours': float_form_hours,
                'available_hours': float_available,
                'idle_hours': float_available - float_used,
                'seq_capacidade': float_capacity_violation,
                'seq_forma': float_form_violation,
                'seq_lote': float_lot_violation,
            }

    if bool_check_stock:
        dict_production = {}
        dict_planned = {}
        for tuple_run in dict_state['quantity']:
            tuple_key = (tuple_run[0], tuple_run[2])
            if tuple_key not in dict_production:
                dict_production[tuple_key] = 0.0
            dict_production[tuple_key] += dict_state['quantity'][tuple_run]
        for tuple_run in dict_plan['quantity']:
            tuple_key = (tuple_run[0], tuple_run[2])
            if tuple_key not in dict_planned:
                dict_planned[tuple_key] = 0.0
            dict_planned[tuple_key] += dict_plan['quantity'][tuple_run]

        dict_total_stock = {}
        for dict_shift in dict_scenario['shifts']:
            dict_total_stock[dict_shift['index']] = 0.0
        for str_product in dict_scenario['products']:
            for str_sku in dict_scenario['skus_of_product'][str_product]:
                float_cumulative = 0.0
                float_cumulative_planned = 0.0
                float_net_position = dict_scenario['initial_stock'][str_sku]
                for dict_shift in dict_scenario['shifts']:
                    int_shift = dict_shift['index']
                    if (str_sku, int_shift) in dict_production:
                        float_cumulative += dict_production[(str_sku, int_shift)]
                        float_net_position += dict_production[(str_sku, int_shift)]
                    if (str_sku, int_shift) in dict_planned:
                        float_cumulative_planned += dict_planned[(str_sku, int_shift)]
                    float_net_position -= dict_scenario['orders'][(str_sku, int_shift)]
                    if int_shift == int_last_shift:
                        if abs(float_cumulative - float_cumulative_planned) > 1e-6:
                            dict_violation['seq_antecipacao'] += abs(float_cumulative - float_cumulative_planned)
                    elif float_cumulative_planned - float_cumulative > 1e-6:
                        dict_violation['seq_antecipacao'] += float_cumulative_planned - float_cumulative
                    if float_net_position > 0.0:
                        dict_total_stock[int_shift] += float_net_position
        if dict_scenario['warehouse_capacity'] is not None:
            for int_shift in dict_total_stock:
                if dict_total_stock[int_shift] - dict_scenario['warehouse_capacity'] > 1e-6:
                    dict_violation['seq_armazem'] += dict_total_stock[int_shift] - dict_scenario['warehouse_capacity']

    float_total_violation = 0.0
    for str_name in dict_violation:
        float_total_violation += dict_violation[str_name]

    return {
        'violation': dict_violation,
        'total_violation': float_total_violation,
        'setup_cost': float_setup_cost,
        'weighted_hours': float_weighted_hours,
        'cells': dict_cells,
        'run_color_hours': dict_run_color_hours,
        'run_previous_color': dict_run_previous_color,
    }


def is_better(dict_candidate, dict_reference):
    bool_better = False
    if dict_candidate['total_violation'] < dict_reference['total_violation'] - 1e-6:
        bool_better = True
    elif dict_candidate['total_violation'] <= dict_reference['total_violation'] + 1e-6:
        if dict_candidate['setup_cost'] < dict_reference['setup_cost'] - 1e-6:
            bool_better = True
        elif dict_candidate['setup_cost'] <= dict_reference['setup_cost'] + 1e-6:
            if dict_candidate['weighted_hours'] < dict_reference['weighted_hours'] - 1e-6:
                bool_better = True
    return bool_better


def order_shift(dict_scenario, dict_plan, dict_state, str_machine, int_shift):
    tuple_cell = (str_machine, int_shift)
    list_runs = list(dict_state['sequence'][tuple_cell])
    if len(list_runs) >= 2:
        if len(list_runs) <= 6:
            list_best = None
            dict_best = None
            for tuple_order in itertools.permutations(list_runs):
                dict_state['sequence'][tuple_cell] = list(tuple_order)
                dict_evaluation = evaluate_sequence(dict_scenario, dict_plan, dict_state, [str_machine], False)
                if dict_best is None or is_better(dict_evaluation, dict_best):
                    list_best = list(tuple_order)
                    dict_best = dict_evaluation
            dict_state['sequence'][tuple_cell] = list_best
        else:
            list_built = []
            list_remaining = list(list_runs)
            while len(list_remaining) > 0:
                str_best = None
                dict_best = None
                for str_sku in list_remaining:
                    dict_state['sequence'][tuple_cell] = list_built + [str_sku]
                    dict_evaluation = evaluate_sequence(dict_scenario, dict_plan, dict_state, [str_machine], False)
                    if dict_best is None or is_better(dict_evaluation, dict_best):
                        str_best = str_sku
                        dict_best = dict_evaluation
                list_built.append(str_best)
                list_remaining.remove(str_best)
            dict_state['sequence'][tuple_cell] = list_built
            dict_best = evaluate_sequence(dict_scenario, dict_plan, dict_state, [str_machine], False)

            bool_improved = True
            while bool_improved:
                bool_improved = False
                for int_from in range(len(list_built)):
                    for int_to in range(len(list_built)):
                        if int_from != int_to:
                            list_swapped = list(dict_state['sequence'][tuple_cell])
                            str_moved = list_swapped[int_from]
                            list_swapped[int_from] = list_swapped[int_to]
                            list_swapped[int_to] = str_moved
                            list_relocated = list(dict_state['sequence'][tuple_cell])
                            str_moved = list_relocated.pop(int_from)
                            list_relocated.insert(int_to, str_moved)
                            for list_neighbor in [list_swapped, list_relocated]:
                                list_current = dict_state['sequence'][tuple_cell]
                                dict_state['sequence'][tuple_cell] = list_neighbor
                                dict_evaluation = evaluate_sequence(dict_scenario, dict_plan, dict_state,
                                                                    [str_machine], False)
                                if is_better(dict_evaluation, dict_best):
                                    dict_best = dict_evaluation
                                    bool_improved = True
                                else:
                                    dict_state['sequence'][tuple_cell] = list_current


def sequence_daily_plan(dict_scenario, dict_settings, dict_mip_result):
    float_started_at = time.perf_counter()
    dict_plan = dict_mip_result['plan']
    list_shifts = dict_scenario['shifts']
    list_machines = dict_scenario['machines']

    dict_state = {'quantity': dict(dict_plan['quantity']), 'sequence': {}}
    for tuple_cell in dict_plan['sequence']:
        dict_state['sequence'][tuple_cell] = list(dict_plan['sequence'][tuple_cell])

    float_anticipated = 0.0
    for dict_shift in list_shifts:
        int_shift = dict_shift['index']
        for str_machine in list_machines:
            tuple_cell = (str_machine, int_shift)
            order_shift(dict_scenario, dict_plan, dict_state, str_machine, int_shift)
            str_form = dict_plan['form'][tuple_cell]
            float_rate = dict_scenario['productivity'][str_form][str_machine]
            float_min_lot = dict_scenario['min_lot'][str_form]

            list_candidates = []
            for dict_future in list_shifts:
                if dict_future['index'] > int_shift:
                    for str_source_machine in dict_scenario['machines_of_product'][str_form]:
                        for str_sku in dict_scenario['skus_of_product'][str_form]:
                            if (str_sku, str_source_machine, dict_future['index']) in dict_state['quantity']:
                                list_candidates.append((str_sku, str_source_machine, dict_future['index']))

            for tuple_source in list_candidates:
                if tuple_source in dict_state['quantity']:
                    str_sku, str_source_machine, int_source_shift = tuple_source
                    tuple_source_cell = (str_source_machine, int_source_shift)
                    tuple_target = (str_sku, str_machine, int_shift)
                    list_scope = [str_machine]
                    if str_source_machine != str_machine:
                        list_scope.append(str_source_machine)
                    dict_reference = evaluate_sequence(dict_scenario, dict_plan, dict_state, list_scope, True)

                    float_source = dict_state['quantity'][tuple_source]
                    float_partial = dict_reference['cells'][tuple_cell]['idle_hours'] * float_rate
                    list_amounts = [float_source]
                    if float_partial < float_source - float_min_lot:
                        if float_partial > 1e-6:
                            list_amounts.append(float_partial)
                    elif float_source - float_min_lot > 1e-6:
                        list_amounts.append(float_source - float_min_lot)

                    list_target_before = list(dict_state['sequence'][tuple_cell])
                    list_source_before = list(dict_state['sequence'][tuple_source_cell])
                    float_target_before = 0.0
                    if tuple_target in dict_state['quantity']:
                        float_target_before = dict_state['quantity'][tuple_target]
                    list_positions = [None]
                    if str_sku not in list_target_before:
                        list_positions = list(range(len(list_target_before) + 1))

                    dict_best = dict_reference
                    tuple_best_move = None
                    for float_amount in list_amounts:
                        for int_position in list_positions:
                            dict_state['quantity'][tuple_target] = float_target_before + float_amount
                            if float_source - float_amount > 1e-6:
                                dict_state['quantity'][tuple_source] = float_source - float_amount
                                dict_state['sequence'][tuple_source_cell] = list(list_source_before)
                            else:
                                del dict_state['quantity'][tuple_source]
                                list_source_after = list(list_source_before)
                                list_source_after.remove(str_sku)
                                dict_state['sequence'][tuple_source_cell] = list_source_after
                            list_target_after = list(dict_state['sequence'][tuple_cell])
                            if int_position is not None:
                                list_target_after = list(list_target_before)
                                list_target_after.insert(int_position, str_sku)
                            dict_state['sequence'][tuple_cell] = list_target_after
                            dict_evaluation = evaluate_sequence(dict_scenario, dict_plan, dict_state, list_scope, True)
                            if is_better(dict_evaluation, dict_best):
                                dict_best = dict_evaluation
                                tuple_best_move = (float_amount, int_position)

                            dict_state['quantity'][tuple_source] = float_source
                            dict_state['sequence'][tuple_source_cell] = list(list_source_before)
                            dict_state['sequence'][tuple_cell] = list(list_target_before)
                            if float_target_before > 0.0:
                                dict_state['quantity'][tuple_target] = float_target_before
                            else:
                                del dict_state['quantity'][tuple_target]

                    if tuple_best_move is not None:
                        float_amount, int_position = tuple_best_move
                        dict_state['quantity'][tuple_target] = float_target_before + float_amount
                        if float_source - float_amount > 1e-6:
                            dict_state['quantity'][tuple_source] = float_source - float_amount
                        else:
                            del dict_state['quantity'][tuple_source]
                            dict_state['sequence'][tuple_source_cell].remove(str_sku)
                        if int_position is not None:
                            dict_state['sequence'][tuple_cell].insert(int_position, str_sku)
                        float_anticipated += float_amount

            order_shift(dict_scenario, dict_plan, dict_state, str_machine, int_shift)

    dict_final = evaluate_sequence(dict_scenario, dict_plan, dict_state, list_machines, True)
    dict_sequenced_plan = {
        'quantity': dict_state['quantity'],
        'sequence': dict_state['sequence'],
        'form': dict_plan['form'],
        'form_change': dict_plan['form_change'],
        'pending': dict_plan['pending'],
        'color_hours': dict_final['run_color_hours'],
        'previous_color': dict_final['run_previous_color'],
    }
    dict_result = build_daily_result(dict_scenario, dict_settings, dict_sequenced_plan)

    list_report_rows = []
    for str_machine in list_machines:
        for dict_shift in list_shifts:
            dict_cell = dict_final['cells'][(str_machine, dict_shift['index'])]
            list_report_rows.append({
                'machine': str_machine,
                'shift_index': dict_shift['index'],
                'date': dict_shift['date'].strftime('%Y-%m-%d'),
                'shift': dict_shift['shift_number'],
                'form': dict_cell['form'],
                'production_hours': dict_cell['production_hours'],
                'color_setup_hours': dict_cell['color_setup_hours'],
                'form_setup_hours': dict_cell['form_setup_hours'],
                'available_hours': dict_cell['available_hours'],
                'idle_hours': dict_cell['idle_hours'],
                'seq_capacidade': dict_cell['seq_capacidade'],
                'seq_forma': dict_cell['seq_forma'],
                'seq_lote': dict_cell['seq_lote'],
            })

    dict_result['status'] = dict_mip_result['status']
    dict_result['stage_objectives'] = dict_mip_result['stage_objectives']
    dict_result['stage_reports'] = dict_mip_result['stage_reports']
    dict_result['mip_kpis'] = dict_mip_result['kpis']
    dict_result['sequencing_report'] = list_report_rows
    dict_result['sequencing_violations'] = dict_final['violation']
    dict_result['kpis']['anticipated_kg'] = float_anticipated
    dict_result['kpis']['sequencing_seconds'] = time.perf_counter() - float_started_at
    dict_result['kpis']['solve_seconds'] = dict_mip_result['kpis']['solve_seconds']
    dict_result['kpis']['hit_time_limit'] = dict_mip_result['kpis']['hit_time_limit']
    return dict_result
