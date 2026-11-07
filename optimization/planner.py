from optimization.weekly_model import build_weekly_scenario, solve_weekly_model
from optimization.daily_model import build_daily_scenario, solve_daily_model
from optimization.sequencing import sequence_daily_plan


def run_weekly_plan(dict_settings, dict_instance):
    dict_scenario = build_weekly_scenario(dict_instance, dict_settings)
    return solve_weekly_model(dict_scenario, dict_settings)


def run_daily_plan(dict_settings, dict_instance, dict_weekly_result):
    dict_scenario = build_daily_scenario(dict_instance, dict_settings, dict_weekly_result)
    dict_mip_result = solve_daily_model(dict_scenario, dict_settings)
    if dict_mip_result['status'] in ('Optimal', 'Feasible'):
        dict_result = sequence_daily_plan(dict_scenario, dict_settings, dict_mip_result)
    else:
        dict_result = dict_mip_result
    return dict_result
