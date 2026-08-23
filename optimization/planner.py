from optimization.weekly_model import build_weekly_scenario, solve_weekly_model
from optimization.daily_model import build_daily_scenario, solve_daily_model


def run_weekly_plan(dict_settings, dict_instance):
    dict_scenario = build_weekly_scenario(dict_instance, dict_settings)
    return solve_weekly_model(dict_scenario, dict_settings)


def run_daily_plan(dict_settings, dict_instance, dict_weekly_result):
    dict_scenario = build_daily_scenario(dict_instance, dict_settings, dict_weekly_result)
    return solve_daily_model(dict_scenario, dict_settings)
