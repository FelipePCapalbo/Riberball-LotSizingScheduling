import os
import tempfile

import gurobipy
from ortools.linear_solver.python import model_builder


def solve_problem(problem, str_solver_name, int_time_limit, int_threads):
    with tempfile.TemporaryDirectory() as str_directory:
        str_mps_path = os.path.join(str_directory, 'problem.mps')
        problem.writeMPS(str_mps_path)
        dict_values = {}

        if str_solver_name.upper() == 'GUROBI':
            gurobi_environment = gurobipy.Env(params={'OutputFlag': 0})
            gurobi_model = gurobipy.read(str_mps_path, env=gurobi_environment)
            gurobi_model.Params.TimeLimit = int_time_limit
            if int_threads:
                gurobi_model.Params.Threads = int_threads
            gurobi_model.optimize()
            if gurobi_model.SolCount > 0:
                for gurobi_variable in gurobi_model.getVars():
                    dict_values[gurobi_variable.VarName] = gurobi_variable.X
            if gurobi_model.Status == gurobipy.GRB.OPTIMAL:
                str_status = 'Optimal'
            elif gurobi_model.SolCount > 0:
                str_status = 'Feasible'
            elif gurobi_model.Status == gurobipy.GRB.INFEASIBLE:
                str_status = 'Infeasible'
            else:
                str_status = 'Not Solved'
            bool_hit_time_limit = gurobi_model.Status == gurobipy.GRB.TIME_LIMIT
            gurobi_model.dispose()
            gurobi_environment.dispose()

        else:
            ortools_model = model_builder.Model()
            ortools_model.import_from_mps_file(str_mps_path)
            ortools_solver = model_builder.Solver('scip')
            ortools_solver.set_time_limit_in_seconds(int_time_limit)
            ortools_status = ortools_solver.solve(ortools_model)
            if ortools_status in (model_builder.SolveStatus.OPTIMAL, model_builder.SolveStatus.FEASIBLE):
                for int_index in range(ortools_model.num_variables):
                    ortools_variable = ortools_model.var_from_index(int_index)
                    dict_values[ortools_variable.name] = ortools_solver.value(ortools_variable)
            if ortools_status == model_builder.SolveStatus.OPTIMAL:
                str_status = 'Optimal'
            elif ortools_status == model_builder.SolveStatus.FEASIBLE:
                str_status = 'Feasible'
            elif ortools_status == model_builder.SolveStatus.INFEASIBLE:
                str_status = 'Infeasible'
            else:
                str_status = 'Not Solved'
            bool_hit_time_limit = ortools_status in (model_builder.SolveStatus.FEASIBLE,
                                                     model_builder.SolveStatus.NOT_SOLVED)

    problem.assignVarsVals(dict_values)
    return str_status, bool_hit_time_limit
