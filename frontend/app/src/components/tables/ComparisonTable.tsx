import type { HistoryRun } from '../../types';

interface ComparisonTableProps {
  runs: HistoryRun[];
  onRefresh: () => void;
  onSelectRun: (runId: string) => void;
}

export default function ComparisonTable({ runs, onRefresh, onSelectRun }: ComparisonTableProps) {
  return (
    <>
      <div className="table-toolbar">
        <span className="text-muted small">Clique em uma linha para carregar o cenário na aba Resultados.</span>
        <button className="btn btn-sm btn-outline-secondary" onClick={onRefresh}>
          Atualizar
        </button>
      </div>
      <div className="table-responsive">
        <table className="table table-sm table-hover data-table">
          <thead>
            <tr>
              <th>Cenário</th>
              <th>Data/Hora</th>
              <th>Horizonte</th>
              <th className="text-center">Máquinas</th>
              <th>Solver</th>
              <th className="text-end">Tempo (s)</th>
              <th className="text-end">Custo Total (R$)</th>
              <th className="text-end">Serviço (%)</th>
              <th className="text-end">Estoque Médio (Kg)</th>
              <th className="text-end">Giro de Estoque</th>
            </tr>
          </thead>
          <tbody>
            {runs.length === 0 ? (
              <tr className="table-empty">
                <td colSpan={10}>Nenhuma execução registrada.</td>
              </tr>
            ) : (
              runs.map((run) => {
                const kpis = run.kpis || {};
                const start = run.start_period ? run.start_period.split(' ')[0] : '—';
                const end = run.end_period ? run.end_period.split(' ')[0] : '—';
                const dateTime = run.timestamp ? run.timestamp.replace('T', ' ') : '—';
                const cost = kpis.total_cost != null ? 'R$ ' + kpis.total_cost.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : '—';
                const service = kpis.service_level != null ? kpis.service_level.toFixed(1) + '%' : '—';
                const inventory = kpis.avg_inventory != null ? kpis.avg_inventory.toLocaleString('pt-BR', { maximumFractionDigits: 0 }) : '—';
                const turnover = kpis.inventory_turnover != null ? kpis.inventory_turnover.toFixed(2) + 'x' : '—';
                const duration = run.duration_seconds != null ? run.duration_seconds.toFixed(1) + ' s' : '—';

                return (
                  <tr className="comparison-row" key={run.id} onClick={() => onSelectRun(run.id)}>
                    <td>{run.label || run.id}</td>
                    <td>{dateTime}</td>
                    <td>
                      {start} → {end}
                    </td>
                    <td className="text-center">{run.active_machines_count ?? '—'}</td>
                    <td>{run.solver_name || '—'}</td>
                    <td className="text-end">{duration}</td>
                    <td className="text-end">{cost}</td>
                    <td className="text-end">{service}</td>
                    <td className="text-end">{inventory}</td>
                    <td className="text-end">{turnover}</td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
