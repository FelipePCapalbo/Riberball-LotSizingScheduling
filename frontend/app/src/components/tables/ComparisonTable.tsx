import { fmtN } from '../../format';
import type { HistoryRun } from '../../types';

interface ComparisonTableProps {
  runs: HistoryRun[];
  onRefresh: () => void;
  onSelectRun: (runId: string) => void;
}

export default function ComparisonTable({ runs, onRefresh, onSelectRun }: ComparisonTableProps) {
  return (
    <div>
      <div className="table-toolbar">
        <span className="table-count">{runs.length} execuções</span>
        <button type="button" className="btn btn-sm btn-outline-secondary" onClick={onRefresh}>
          Atualizar
        </button>
      </div>
      <div className="table-scroll">
        <table className="data-table w-100">
          <thead>
            <tr>
              <th rowSpan={2}>Cenário</th>
              <th rowSpan={2}>Quando</th>
              <th rowSpan={2}>Input</th>
              <th colSpan={5} className="group-head">Plano semanal</th>
              <th colSpan={4} className="group-head">Programação por turno</th>
            </tr>
            <tr>
              <th className="text-end">Custo</th>
              <th className="text-end">SL carteira</th>
              <th className="text-end">SL previsão</th>
              <th className="text-end">Giro</th>
              <th className="text-end">Tempo</th>
              <th className="text-end">Custo</th>
              <th className="text-end">SL carteira</th>
              <th className="text-end">h setup</th>
              <th className="text-end">Tempo</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id} onClick={() => onSelectRun(run.id)} className="clickable">
                <td>{run.label}</td>
                <td>{run.timestamp.replace('T', ' ').slice(0, 16)}</td>
                <td className="small">{run.data_file}</td>
                <td className="text-end">{fmtN(run.weekly_kpis.total_cost, 0)}</td>
                <td className="text-end">{fmtN(run.weekly_kpis.order_service_level, 2)}%</td>
                <td className="text-end">{fmtN(run.weekly_kpis.forecast_service_level, 2)}%</td>
                <td className="text-end">{fmtN(run.weekly_kpis.inventory_turnover, 2)}</td>
                <td className="text-end">{fmtN(run.weekly_duration, 1)}s</td>
                <td className="text-end">{run.daily_kpis ? fmtN(run.daily_kpis.total_cost, 0) : '—'}</td>
                <td className="text-end">{run.daily_kpis ? `${fmtN(run.daily_kpis.order_service_level, 2)}%` : '—'}</td>
                <td className="text-end">
                  {run.daily_kpis ? fmtN(run.daily_kpis.form_setup_hours + run.daily_kpis.color_setup_hours, 1) : '—'}
                </td>
                <td className="text-end">{run.daily_duration != null ? `${fmtN(run.daily_duration, 1)}s` : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
