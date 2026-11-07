import os
import tempfile
import time

import gurobipy
import pulp
from ortools.linear_solver.python import model_builder


def solve_lexicographic(problem, list_stage_expressions, str_solver_name, int_time_limit, int_threads, int_seed,
                        str_log_file, float_heuristic_seconds):
    list_stage_values = []
    list_stage_reports = []
    bool_heuristic = float_heuristic_seconds is not None
    float_spent_on_heuristic = 0.0
    if bool_heuristic:
        float_spent_on_heuristic = float_heuristic_seconds
    float_started_at = time.perf_counter() - float_spent_on_heuristic
    list_heuristic_objective = None
    bool_heuristic_feasible = None
    bool_heuristic_used = None
    str_status = 'Optimal'
    bool_hit_time_limit = False
    bool_continue = True
    int_stage = 0
    while int_stage < len(list_stage_expressions) and bool_continue:
        float_stage_started_at = time.perf_counter()
        if int_stage == 0:
            float_stage_started_at = float_started_at
        if int_stage == 0 and bool_heuristic:
            list_heuristic_objective = []
            for expression_stage in list_stage_expressions:
                list_heuristic_objective.append(pulp.value(expression_stage))
            bool_heuristic_feasible = problem.valid(1e-6)
        float_remaining = int_time_limit - (time.perf_counter() - float_started_at)
        if int_stage == 0:
            float_stage_budget = ((float_remaining + float_spent_on_heuristic) / len(list_stage_expressions)
                                  - float_spent_on_heuristic)
        else:
            float_stage_budget = float_remaining / (len(list_stage_expressions) - int_stage)
        int_stage_time_limit = int(float_stage_budget)
        if int_stage_time_limit < 1:
            int_stage_time_limit = 1
        problem.setObjective(list_stage_expressions[int_stage])

        dict_start = {}
        for variable in problem.variables():
            if variable.varValue is not None:
                dict_start[variable.name] = variable.varValue

        with tempfile.TemporaryDirectory() as str_directory:
            str_mps_path = os.path.join(str_directory, 'problem.mps')
            problem.writeMPS(str_mps_path)
            dict_values = {}
            float_objective = None
            float_bound = None
            dict_effort = {'work': None, 'nodes': None, 'simplex_iterations': None, 'variables': None,
                           'binaries': None, 'integers': None, 'constraints': None, 'nonzeros': None}

            if str_solver_name.upper() == 'GUROBI':
                if str_log_file:
                    gurobi_environment = gurobipy.Env(params={'OutputFlag': 1, 'LogToConsole': 0,
                                                              'LogFile': str_log_file})
                else:
                    gurobi_environment = gurobipy.Env(params={'OutputFlag': 0})
                gurobi_model = gurobipy.read(str_mps_path, env=gurobi_environment)
                gurobi_model.Params.TimeLimit = int_stage_time_limit
                gurobi_model.Params.Seed = int_seed
                if int_threads:
                    gurobi_model.Params.Threads = int_threads
                for gurobi_variable in gurobi_model.getVars():
                    if gurobi_variable.VarName in dict_start:
                        gurobi_variable.Start = dict_start[gurobi_variable.VarName]
                bool_read_start_log = int_stage == 0 and bool_heuristic
                if bool_read_start_log:
                    if str_log_file:
                        str_start_log = str_log_file
                        int_log_offset = os.path.getsize(str_log_file)
                    else:
                        str_start_log = os.path.join(str_directory, 'gurobi.log')
                        int_log_offset = 0
                        gurobi_model.Params.LogToConsole = 0
                        gurobi_model.Params.LogFile = str_start_log
                        gurobi_model.Params.OutputFlag = 1
                gurobi_model.optimize()
                if bool_read_start_log:
                    with open(str_start_log, encoding='utf-8', errors='replace') as file_log:
                        file_log.seek(int_log_offset)
                        str_stage_log = file_log.read()
                    bool_heuristic_used = 'Loaded user MIP start' in str_stage_log
                if gurobi_model.SolCount > 0:
                    for gurobi_variable in gurobi_model.getVars():
                        dict_values[gurobi_variable.VarName] = gurobi_variable.X
                    float_objective = gurobi_model.ObjVal
                    float_bound = gurobi_model.ObjBound
                if gurobi_model.Status == gurobipy.GRB.OPTIMAL:
                    str_stage_status = 'Optimal'
                elif gurobi_model.SolCount > 0:
                    str_stage_status = 'Feasible'
                elif gurobi_model.Status == gurobipy.GRB.INFEASIBLE:
                    str_stage_status = 'Infeasible'
                else:
                    str_stage_status = 'Not Solved'
                bool_stage_hit_time_limit = gurobi_model.Status == gurobipy.GRB.TIME_LIMIT
                dict_effort['work'] = gurobi_model.Work
                dict_effort['nodes'] = gurobi_model.NodeCount
                dict_effort['simplex_iterations'] = gurobi_model.IterCount
                dict_effort['variables'] = gurobi_model.NumVars
                dict_effort['binaries'] = gurobi_model.NumBinVars
                dict_effort['integers'] = gurobi_model.NumIntVars
                dict_effort['constraints'] = gurobi_model.NumConstrs
                dict_effort['nonzeros'] = gurobi_model.NumNZs
                gurobi_model.dispose()
                gurobi_environment.dispose()

            else:
                ortools_model = model_builder.Model()
                ortools_model.import_from_mps_file(str_mps_path)
                for int_index in range(ortools_model.num_variables):
                    ortools_variable = ortools_model.var_from_index(int_index)
                    if ortools_variable.name in dict_start:
                        ortools_model.add_hint(ortools_variable, dict_start[ortools_variable.name])
                ortools_solver = model_builder.Solver('scip')
                ortools_solver.set_time_limit_in_seconds(int_stage_time_limit)
                ortools_status = ortools_solver.solve(ortools_model)
                if ortools_status in (model_builder.SolveStatus.OPTIMAL, model_builder.SolveStatus.FEASIBLE):
                    for int_index in range(ortools_model.num_variables):
                        ortools_variable = ortools_model.var_from_index(int_index)
                        dict_values[ortools_variable.name] = ortools_solver.value(ortools_variable)
                    float_objective = ortools_solver.objective_value
                    float_bound = ortools_solver.best_objective_bound
                if ortools_status == model_builder.SolveStatus.OPTIMAL:
                    str_stage_status = 'Optimal'
                elif ortools_status == model_builder.SolveStatus.FEASIBLE:
                    str_stage_status = 'Feasible'
                elif ortools_status == model_builder.SolveStatus.INFEASIBLE:
                    str_stage_status = 'Infeasible'
                else:
                    str_stage_status = 'Not Solved'
                bool_stage_hit_time_limit = ortools_status in (model_builder.SolveStatus.FEASIBLE,
                                                               model_builder.SolveStatus.NOT_SOLVED)
                dict_effort['variables'] = ortools_model.num_variables
                dict_effort['constraints'] = ortools_model.num_constraints

        problem.assignVarsVals(dict_values)
        if bool_stage_hit_time_limit:
            bool_hit_time_limit = True

        if float_objective is None:
            float_gap = None
        elif abs(float_objective) > 1.0:
            float_gap = (float_objective - float_bound) / abs(float_objective)
        else:
            float_gap = float_objective - float_bound
        list_stage_reports.append({
            'stage': int_stage + 1,
            'status': str_stage_status,
            'objective': float_objective,
            'bound': float_bound,
            'gap': float_gap,
            'hit_time_limit': bool_stage_hit_time_limit,
            'seconds': time.perf_counter() - float_stage_started_at,
            'work': dict_effort['work'],
            'nodes': dict_effort['nodes'],
            'simplex_iterations': dict_effort['simplex_iterations'],
            'variables': dict_effort['variables'],
            'binaries': dict_effort['binaries'],
            'integers': dict_effort['integers'],
            'constraints': dict_effort['constraints'],
            'nonzeros': dict_effort['nonzeros'],
        })
        if int_stage == 0:
            list_stage_reports[0]['heuristic_seconds'] = float_heuristic_seconds
            list_stage_reports[0]['heuristic_objective'] = list_heuristic_objective
            list_stage_reports[0]['heuristic_feasible'] = bool_heuristic_feasible
            list_stage_reports[0]['heuristic_used'] = bool_heuristic_used

        if str_stage_status in ('Optimal', 'Feasible'):
            float_stage_value = pulp.value(list_stage_expressions[int_stage])
            list_stage_values.append(float_stage_value)
            problem += (list_stage_expressions[int_stage] <= float_stage_value, f'trava_{int_stage + 1}')
            if str_stage_status == 'Feasible':
                str_status = 'Feasible'
        else:
            bool_continue = False
            if len(list_stage_values) == 0:
                str_status = str_stage_status
            else:
                str_status = 'Feasible'
        int_stage += 1
    return str_status, bool_hit_time_limit, list_stage_values, list_stage_reports
