import { downloadCSV } from '../../csv';
import { fmtCSV, fmtN, formatDate } from '../../format';
import type { WeeklyDemandRow, WeeklyInventoryRow, WeeklyProductionRow } from '../../types';

interface WeeklyPlanTableProps {
  demand: WeeklyDemandRow[];
  inventory: WeeklyInventoryRow[];
  production: WeeklyProductionRow[];
}

export default function WeeklyPlanTable({ demand, inventory, production }: WeeklyPlanTableProps) {
  const weeks = Array.from(new Set(demand.map((row) => row.week))).sort();
  const rows = weeks.map((week) => {
    let orders = 0;
    let forecast = 0;
    let backlog = 0;
    let lost = 0;
    for (const row of demand) {
      if (row.week === week) {
        orders += row.orders;
        forecast += row.forecast;
        backlog += row.backlog;
        lost += row.lost;
      }
    }
    let stock = 0;
    let target = 0;
    for (const row of inventory) {
      if (row.week === week) {
        stock += row.inventory;
        target += row.target;
      }
    }
    let produced = 0;
    let setupHours = 0;
    for (const row of production) {
      if (row.week === week) {
        produced += row.kg;
        setupHours += row.setup_hours;
      }
    }
    return { week, orders, forecast, backlog, lost, stock, target, produced, setupHours };
  });

  return (
    <div>
      <div className="table-toolbar">
        <span className="table-count">{rows.length} semanas</span>
        <button
          type="button" className="btn btn-sm btn-outline-secondary"
          onClick={() =>
            downloadCSV(
              rows,
              ['Semana', 'Carteira', 'Previsao', 'Produzido', 'Atraso carteira', 'Venda perdida', 'Estoque', 'Meta cobertura', 'Horas setup'],
              (row) => [
                formatDate(row.week),
                fmtCSV(row.orders),
                fmtCSV(row.forecast),
                fmtCSV(row.produced),
                fmtCSV(row.backlog),
                fmtCSV(row.lost),
                fmtCSV(row.stock),
                fmtCSV(row.target),
                fmtCSV(row.setupHours),
              ],
              'plano_semanal.csv',
            )
          }
        >
          Exportar CSV
        </button>
      </div>
      <div className="table-scroll">
        <table className="data-table w-100">
          <thead>
            <tr>
              <th>Semana</th>
              <th className="text-end">Carteira</th>
              <th className="text-end">Previsão</th>
              <th className="text-end">Produzido</th>
              <th className="text-end">Atraso carteira</th>
              <th className="text-end">Venda perdida</th>
              <th className="text-end">Estoque</th>
              <th className="text-end">Meta cobertura</th>
              <th className="text-end">h setup</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.week}>
                <td>{formatDate(row.week)}</td>
                <td className="text-end">{fmtN(row.orders, 0)}</td>
                <td className="text-end">{fmtN(row.forecast, 0)}</td>
                <td className="text-end">{fmtN(row.produced, 0)}</td>
                <td className={row.backlog > 0.5 ? 'text-end cell-bad' : 'text-end'}>{fmtN(row.backlog, 0)}</td>
                <td className={row.lost > 0.5 ? 'text-end cell-warn' : 'text-end'}>{fmtN(row.lost, 0)}</td>
                <td className="text-end">{fmtN(row.stock, 0)}</td>
                <td className="text-end">{fmtN(row.target, 0)}</td>
                <td className="text-end">{fmtN(row.setupHours, 1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
