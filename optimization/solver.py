import os
import tempfile
import time

import gurobipy
import pulp
from ortools.linear_solver.python import model_builder


def solve_problem(problem, str_solver_name, float_time_limit, int_threads, int_seed, str_log_file,
                  bool_require_solution):
    dict_start = {}
    for variable in problem.variables():
        if variable.varValue is not None:
            dict_start[variable.name] = variable.varValue

    dict_outcome = {'values': {}, 'objective': None, 'bound': None, 'status': 'Not Solved', 'hit_time_limit': False,
                    'work': None, 'nodes': None, 'simplex_iterations': None, 'variables': None, 'binaries': None,
                    'integers': None, 'constraints': None, 'nonzeros': None}
    with tempfile.TemporaryDirectory() as str_directory:
        str_mps_path = os.path.join(str_directory, 'problem.mps')
        problem.writeMPS(str_mps_path)

        if str_solver_name.upper() == 'GUROBI':
            if str_log_file:
                gurobi_environment = gurobipy.Env(params={'OutputFlag': 1, 'LogToConsole': 0,
                                                          'LogFile': str_log_file})
            else:
                gurobi_environment = gurobipy.Env(params={'OutputFlag': 0})
            gurobi_model = gurobipy.read(str_mps_path, env=gurobi_environment)
            gurobi_model.Params.TimeLimit = float_time_limit
            gurobi_model.Params.Seed = int_seed
            if int_threads:
                gurobi_model.Params.Threads = int_threads
            for gurobi_variable in gurobi_model.getVars():
                if gurobi_variable.VarName in dict_start:
                    gurobi_variable.Start = dict_start[gurobi_variable.VarName]
            gurobi_model.optimize()
            dict_outcome['hit_time_limit'] = gurobi_model.Status == gurobipy.GRB.TIME_LIMIT
            if bool_require_solution and gurobi_model.SolCount == 0 and gurobi_model.Status == gurobipy.GRB.TIME_LIMIT:
                gurobi_model.Params.TimeLimit = gurobipy.GRB.INFINITY
                gurobi_model.Params.SolutionLimit = 1
                gurobi_model.optimize()
            if gurobi_model.SolCount > 0:
                for gurobi_variable in gurobi_model.getVars():
                    dict_outcome['values'][gurobi_variable.VarName] = gurobi_variable.X
                dict_outcome['objective'] = gurobi_model.ObjVal
                dict_outcome['bound'] = gurobi_model.ObjBound
            if gurobi_model.Status == gurobipy.GRB.OPTIMAL:
                dict_outcome['status'] = 'Optimal'
            elif gurobi_model.SolCount > 0:
                dict_outcome['status'] = 'Feasible'
            elif gurobi_model.Status == gurobipy.GRB.INFEASIBLE:
                dict_outcome['status'] = 'Infeasible'
            else:
                dict_outcome['status'] = 'Not Solved'
            dict_outcome['work'] = gurobi_model.Work
            dict_outcome['nodes'] = gurobi_model.NodeCount
            dict_outcome['simplex_iterations'] = gurobi_model.IterCount
            dict_outcome['variables'] = gurobi_model.NumVars
            dict_outcome['binaries'] = gurobi_model.NumBinVars
            dict_outcome['integers'] = gurobi_model.NumIntVars
            dict_outcome['constraints'] = gurobi_model.NumConstrs
            dict_outcome['nonzeros'] = gurobi_model.NumNZs
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
            ortools_solver.set_time_limit_in_seconds(float_time_limit)
            ortools_status = ortools_solver.solve(ortools_model)
            if ortools_status in (model_builder.SolveStatus.OPTIMAL, model_builder.SolveStatus.FEASIBLE):
                for int_index in range(ortools_model.num_variables):
                    ortools_variable = ortools_model.var_from_index(int_index)
                    dict_outcome['values'][ortools_variable.name] = ortools_solver.value(ortools_variable)
                dict_outcome['objective'] = ortools_solver.objective_value
                dict_outcome['bound'] = ortools_solver.best_objective_bound
            if ortools_status == model_builder.SolveStatus.OPTIMAL:
                dict_outcome['status'] = 'Optimal'
            elif ortools_status == model_builder.SolveStatus.FEASIBLE:
                dict_outcome['status'] = 'Feasible'
            elif ortools_status == model_builder.SolveStatus.INFEASIBLE:
                dict_outcome['status'] = 'Infeasible'
            else:
                dict_outcome['status'] = 'Not Solved'
            dict_outcome['hit_time_limit'] = ortools_status in (model_builder.SolveStatus.FEASIBLE,
                                                                model_builder.SolveStatus.NOT_SOLVED)
            dict_outcome['variables'] = ortools_model.num_variables
            dict_outcome['constraints'] = ortools_model.num_constraints
    return dict_outcome


def compute_gap(float_objective, float_bound):
    if float_objective is None or float_bound is None:
        float_gap = None
    elif abs(float_objective) > 1.0:
        float_gap = (float_objective - float_bound) / abs(float_objective)
    else:
        float_gap = float_objective - float_bound
    return float_gap


def add_effort(dict_total, dict_outcome):
    for str_key in ['work', 'nodes', 'simplex_iterations']:
        if dict_outcome[str_key] is not None:
            if dict_total[str_key] is None:
                dict_total[str_key] = dict_outcome[str_key]
            else:
                dict_total[str_key] += dict_outcome[str_key]


def solve_lexicographic(problem, list_stage_expressions, str_solver_name, int_time_limit, int_threads, int_seed,
                        str_log_file, dict_partitions, str_decomposition, int_block_size, float_fo_time_share):
    list_stage_values = []
    list_stage_reports = []
    float_started_at = time.perf_counter()
    str_status = 'Optimal'
    bool_hit_time_limit = False
    bool_continue = True

    if str_decomposition is not None:
        dict_variables = problem.variablesDict()
        list_blocks = []
        list_current_block = []
        int_units_in_block = 0
        for list_unit in dict_partitions[str_decomposition]:
            for str_name in list_unit:
                list_current_block.append(str_name)
            int_units_in_block += 1
            if int_units_in_block == int_block_size:
                list_blocks.append(list_current_block)
                list_current_block = []
                int_units_in_block = 0
        if len(list_current_block) > 0:
            list_blocks.append(list_current_block)

    int_stage = 0
    while int_stage < len(list_stage_expressions) and bool_continue:
        float_stage_started_at = time.perf_counter()
        float_remaining = int_time_limit - (float_stage_started_at - float_started_at)
        int_stage_time_limit = int(float_remaining / (len(list_stage_expressions) - int_stage))
        if int_stage_time_limit < 1:
            int_stage_time_limit = 1
        problem.setObjective(list_stage_expressions[int_stage])
        dict_extra = {}

        if str_decomposition is None:
            dict_outcome = solve_problem(problem, str_solver_name, int_stage_time_limit, int_threads, int_seed,
                                         str_log_file, False)
            problem.assignVarsVals(dict_outcome['values'])
            str_stage_status = dict_outcome['status']
            bool_stage_hit_time_limit = dict_outcome['hit_time_limit']
            float_objective = dict_outcome['objective']
            float_bound = dict_outcome['bound']
            dict_effort = dict_outcome

        else:
            float_stage_deadline = float_stage_started_at + int_stage_time_limit
            dict_effort = {'work': None, 'nodes': None, 'simplex_iterations': None}
            int_subproblems = 0
            bool_stage_hit_time_limit = False

            dict_incumbent = {}
            bool_has_incumbent = False
            list_integer_variables = []
            int_binaries = 0
            for variable in problem.variables():
                if variable.varValue is not None:
                    dict_incumbent[variable.name] = variable.varValue
                    bool_has_incumbent = True
                if variable.cat == pulp.LpInteger:
                    list_integer_variables.append(variable)
                    if variable.lowBound == 0 and variable.upBound == 1:
                        int_binaries += 1

            for variable in list_integer_variables:
                variable.cat = pulp.LpContinuous
            float_relaxation_limit = float_stage_deadline - time.perf_counter()
            if float_relaxation_limit < 1.0:
                float_relaxation_limit = 1.0
            dict_relaxation = solve_problem(problem, str_solver_name, float_relaxation_limit, int_threads, int_seed,
                                            str_log_file, False)
            for variable in list_integer_variables:
                variable.cat = pulp.LpInteger
            add_effort(dict_effort, dict_relaxation)
            bool_relaxation_integral = False
            if dict_relaxation['status'] == 'Optimal':
                float_bound = dict_relaxation['objective']
                bool_relaxation_integral = True
                for variable in list_integer_variables:
                    float_value = dict_relaxation['values'][variable.name]
                    if abs(float_value - round(float_value)) > 1e-6:
                        bool_relaxation_integral = False
            else:
                float_bound = None
            dict_effort['variables'] = dict_relaxation['variables']
            dict_effort['binaries'] = int_binaries
            dict_effort['integers'] = len(list_integer_variables)
            dict_effort['constraints'] = dict_relaxation['constraints']
            dict_effort['nonzeros'] = dict_relaxation['nonzeros']

            float_rf_started_at = time.perf_counter()
            float_rf_deadline = float_rf_started_at + (float_stage_deadline - float_rf_started_at) * (
                1.0 - float_fo_time_share)
            if bool_relaxation_integral:
                problem.assignVarsVals(dict_relaxation['values'])
                int_rf_iterations = 0
            else:
                int_rf_iterations = len(list_blocks) - 1
                if int_rf_iterations < 1:
                    int_rf_iterations = 1
            bool_rf_complete = True
            int_iteration = 0
            while int_iteration < int_rf_iterations and bool_rf_complete:
                float_stage_share = (float_stage_deadline - time.perf_counter()) / (int_rf_iterations - int_iteration)
                if bool_has_incumbent and float_stage_share < 1.0:
                    bool_rf_complete = False
                    bool_stage_hit_time_limit = True
                else:
                    int_block = 0
                    while int_block < len(list_blocks):
                        for str_name in list_blocks[int_block]:
                            variable = dict_variables[str_name]
                            if int_block < int_iteration:
                                variable.cat = pulp.LpInteger
                                variable.lowBound = round(variable.varValue)
                                variable.upBound = round(variable.varValue)
                            elif int_block <= int_iteration + 1:
                                variable.cat = pulp.LpInteger
                                variable.lowBound = 0
                                variable.upBound = 1
                            else:
                                variable.cat = pulp.LpContinuous
                                variable.lowBound = 0
                                variable.upBound = 1
                        int_block += 1
                    float_subproblem_limit = ((float_rf_deadline - time.perf_counter())
                                              / (int_rf_iterations - int_iteration))
                    if float_subproblem_limit < 1.0:
                        float_subproblem_limit = 1.0
                    dict_outcome = solve_problem(problem, str_solver_name, float_subproblem_limit, int_threads,
                                                 int_seed, str_log_file, not bool_has_incumbent)
                    int_subproblems += 1
                    add_effort(dict_effort, dict_outcome)
                    if dict_outcome['hit_time_limit']:
                        bool_stage_hit_time_limit = True
                    if dict_outcome['status'] in ('Optimal', 'Feasible'):
                        problem.assignVarsVals(dict_outcome['values'])
                    else:
                        bool_rf_complete = False
                int_iteration += 1

            for variable in list_integer_variables:
                variable.cat = pulp.LpInteger
                variable.lowBound = 0
                variable.upBound = 1

            if bool_rf_complete:
                bool_has_solution = True
            elif bool_has_incumbent:
                problem.assignVarsVals(dict_incumbent)
                bool_has_solution = True
            else:
                float_fallback_limit = float_stage_deadline - time.perf_counter()
                if float_fallback_limit < 1.0:
                    float_fallback_limit = 1.0
                dict_outcome = solve_problem(problem, str_solver_name, float_fallback_limit, int_threads, int_seed,
                                             str_log_file, True)
                int_subproblems += 1
                add_effort(dict_effort, dict_outcome)
                if dict_outcome['hit_time_limit']:
                    bool_stage_hit_time_limit = True
                problem.assignVarsVals(dict_outcome['values'])
                bool_has_solution = dict_outcome['status'] in ('Optimal', 'Feasible')
            float_rf_seconds = time.perf_counter() - float_rf_started_at

            float_fo_started_at = time.perf_counter()
            bool_fo_continue = False
            if bool_has_solution:
                float_objective = pulp.value(list_stage_expressions[int_stage])
                float_gap = compute_gap(float_objective, float_bound)
                if float_gap is None or float_gap > 1e-4:
                    bool_fo_continue = True
            else:
                float_objective = None
            while bool_fo_continue:
                bool_pass_improved = False
                int_free_block = 0
                while int_free_block < len(list_blocks) and bool_fo_continue:
                    float_left = float_stage_deadline - time.perf_counter()
                    if float_left < 1.0:
                        bool_fo_continue = False
                        bool_stage_hit_time_limit = True
                    else:
                        int_block = 0
                        while int_block < len(list_blocks):
                            for str_name in list_blocks[int_block]:
                                variable = dict_variables[str_name]
                                if int_block == int_free_block:
                                    variable.lowBound = 0
                                    variable.upBound = 1
                                else:
                                    variable.lowBound = round(variable.varValue)
                                    variable.upBound = round(variable.varValue)
                            int_block += 1
                        dict_saved = {}
                        for variable in problem.variables():
                            dict_saved[variable.name] = variable.varValue
                        dict_outcome = solve_problem(problem, str_solver_name,
                                                     float_left / (len(list_blocks) - int_free_block), int_threads,
                                                     int_seed, str_log_file, False)
                        int_subproblems += 1
                        add_effort(dict_effort, dict_outcome)
                        if dict_outcome['hit_time_limit']:
                            bool_stage_hit_time_limit = True
                        bool_accepted = False
                        if dict_outcome['status'] in ('Optimal', 'Feasible'):
                            problem.assignVarsVals(dict_outcome['values'])
                            float_candidate = pulp.value(list_stage_expressions[int_stage])
                            if float_objective - float_candidate > 1e-6 * (1.0 + abs(float_objective)):
                                bool_accepted = True
                        if bool_accepted:
                            float_objective = float_candidate
                            bool_pass_improved = True
                            float_gap = compute_gap(float_objective, float_bound)
                            if float_gap is not None and float_gap <= 1e-4:
                                bool_fo_continue = False
                        else:
                            problem.assignVarsVals(dict_saved)
                    int_free_block += 1
                if not bool_pass_improved:
                    bool_fo_continue = False

            for variable in list_integer_variables:
                variable.lowBound = 0
                variable.upBound = 1
            float_fo_seconds = time.perf_counter() - float_fo_started_at

            if float_objective is None:
                str_stage_status = dict_outcome['status']
            else:
                float_gap = compute_gap(float_objective, float_bound)
                if float_gap is not None and float_gap <= 1e-4:
                    str_stage_status = 'Optimal'
                else:
                    str_stage_status = 'Feasible'
            dict_extra = {'subproblems': int_subproblems, 'rf_seconds': float_rf_seconds,
                          'fo_seconds': float_fo_seconds, 'rf_complete': bool_rf_complete}

        if bool_stage_hit_time_limit:
            bool_hit_time_limit = True

        dict_report = {
            'stage': int_stage + 1,
            'status': str_stage_status,
            'objective': float_objective,
            'bound': float_bound,
            'gap': compute_gap(float_objective, float_bound),
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
        }
        for str_key in dict_extra:
            dict_report[str_key] = dict_extra[str_key]
        list_stage_reports.append(dict_report)

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
