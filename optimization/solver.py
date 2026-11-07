import os
import tempfile
import time

import gurobipy
import pulp
from ortools.linear_solver.python import model_builder


def solve_lexicographic(problem, list_stage_expressions, str_solver_name, int_time_limit, int_threads, int_seed,
                        str_log_file):
    list_stage_values = []
    list_stage_reports = []
    float_started_at = time.perf_counter()
    str_status = 'Optimal'
    bool_hit_time_limit = False
    bool_continue = True
    int_stage = 0
    while int_stage < len(list_stage_expressions) and bool_continue:
        float_stage_started_at = time.perf_counter()
        float_remaining = int_time_limit - (float_stage_started_at - float_started_at)
        int_stage_time_limit = int(float_remaining / (len(list_stage_expressions) - int_stage))
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
                gurobi_model.optimize()
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
