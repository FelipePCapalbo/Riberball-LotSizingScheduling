import { useMemo, useState } from 'react';
import { downloadCSV } from '../../csv';
import { fmtCSV, fmtN, formatDate } from '../../format';
import type { DailyOrderRow } from '../../types';

interface OrdersTableProps {
  data: DailyOrderRow[];
}

export default function OrdersTable({ data }: OrdersTableProps) {
  const [onlyDue, setOnlyDue] = useState(true);
  const rows = useMemo(() => {
    const filtered = onlyDue ? data.filter((row) => row.orders > 0.001) : data;
    return filtered.slice().sort((a, b) => a.shift_index - b.shift_index || a.sku.localeCompare(b.sku));
  }, [data, onlyDue]);

  let totalOrders = 0;
  let totalDelivered = 0;
  for (const row of data) {
    totalOrders += row.orders;
    totalDelivered += row.delivered_orders;
  }

  return (
    <div>
      <div className="table-toolbar">
        <label className="checkbox">
          <input type="checkbox" checked={onlyDue} onChange={(e) => setOnlyDue(e.target.checked)} />
          Só turnos com vencimento
        </label>
        <span className="table-count">
          {fmtN(totalDelivered, 0)} de {fmtN(totalOrders, 0)} kg entregues
        </span>
        <button
          type="button" className="btn btn-sm btn-outline-secondary"
          onClick={() =>
            downloadCSV(
              rows,
              ['Data', 'Turno', 'SKU', 'Carteira vencendo', 'Entregue', 'Em atraso', 'Previsao', 'Venda perdida', 'Estoque'],
              (row) => [
                formatDate(row.date),
                row.shift,
                row.sku,
                fmtCSV(row.orders),
                fmtCSV(row.delivered_orders),
                fmtCSV(row.backlog),
                fmtCSV(row.forecast),
                fmtCSV(row.lost),
                fmtCSV(row.inventory),
              ],
              'carteira_por_turno.csv',
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
              <th>Data</th>
              <th>Turno</th>
              <th>SKU</th>
              <th className="text-end">Vencendo</th>
              <th className="text-end">Entregue</th>
              <th className="text-end">Em atraso</th>
              <th className="text-end">Previsão</th>
              <th className="text-end">Perdida</th>
              <th className="text-end">Estoque</th>
              <th>Situação</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.sku}-${row.shift_index}`}>
                <td>{formatDate(row.date)}</td>
                <td>T{row.shift}</td>
                <td>{row.sku}</td>
                <td className="text-end">{fmtN(row.orders, 0)}</td>
                <td className="text-end">{fmtN(row.delivered_orders, 0)}</td>
                <td className={row.backlog > 0.5 ? 'text-end cell-bad' : 'text-end'}>{fmtN(row.backlog, 0)}</td>
                <td className="text-end">{fmtN(row.forecast, 0)}</td>
                <td className={row.lost > 0.5 ? 'text-end cell-warn' : 'text-end'}>{fmtN(row.lost, 0)}</td>
                <td className="text-end">{fmtN(row.inventory, 0)}</td>
                <td>{row.backlog > 0.5 ? 'Em atraso' : 'No prazo'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
