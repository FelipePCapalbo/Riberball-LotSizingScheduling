export interface SolverOption {
  value: string;
  label: string;
}

export interface EnvironmentConfig {
  name: string;
  solverOptions: SolverOption[];
}

const ORTOOLS_OPTION: SolverOption = { value: 'ORTOOLS', label: 'OR-Tools' };
const GUROBI_OPTION: SolverOption = { value: 'GUROBI', label: 'Gurobi' };

const ENVIRONMENTS: Record<string, EnvironmentConfig> = {
  main: { name: 'main', solverOptions: [ORTOOLS_OPTION] },
  dev: { name: 'dev', solverOptions: [ORTOOLS_OPTION, GUROBI_OPTION] },
};

export const ENVIRONMENT = ENVIRONMENTS[import.meta.env.MODE];
