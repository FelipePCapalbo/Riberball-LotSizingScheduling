import { useMemo, useState } from 'react';
import { downloadCSV } from '../../csv';
import { fmtCSV, fmtN, formatDate } from '../../format';
import type { ScheduleRow } from '../../types';

interface OperationsTableProps {
  data: ScheduleRow[];
}

function natureOf(row: ScheduleRow): string {
  if (row.form_setup_hours > 0) {
    return 'Troca de forma';
  } else if (row.color_setup_hours > 0) {
    return 'Troca de cor';
  } else {
    return 'Produção contínua';
  }
}

export default function OperationsTable({ data }: OperationsTableProps) {
  const [machineFilter, setMachineFilter] = useState('');
  const machines = useMemo(
    () => Array.from(new Set(data.map((row) => row.machine))).sort((a, b) => parseInt(a, 10) - parseInt(b, 10)),
    [data],
  );
  const rows = useMemo(() => {
    const filtered = machineFilter ? data.filter((row) => row.machine === machineFilter) : data;
    return filtered.slice().sort(
      (a, b) =>
        a.shift_index - b.shift_index ||
        parseInt(a.machine, 10) - parseInt(b.machine, 10) ||
        a.position - b.position,
    );
  }, [data, machineFilter]);

  return (
    <div>
      <div className="table-toolbar">
        <label>
          Máquina
          <select value={machineFilter} onChange={(e) => setMachineFilter(e.target.value)}>
            <option value="">Todas</option>
            {machines.map((m) => (
              <option key={m} value={m}>
                M{m}
              </option>
            ))}
          </select>
        </label>
        <span className="table-count">{rows.length} operações</span>
        <button
          type="button" className="btn btn-sm btn-outline-secondary"
          onClick={() =>
            downloadCSV(
              rows,
              ['Data', 'Turno', 'Maquina', 'Posicao', 'Balao', 'Cor', 'Kg', 'Horas producao', 'Horas setup forma', 'Horas setup cor', 'Natureza'],
              (row) => [
                formatDate(row.date),
                row.shift,
                `M${row.machine}`,
                row.position,
                row.product,
                row.color,
                fmtCSV(row.kg),
                fmtCSV(row.production_hours),
                fmtCSV(row.form_setup_hours),
                fmtCSV(row.color_setup_hours),
                natureOf(row),
              ],
              'programacao_por_turno.csv',
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
              <th>Máquina</th>
              <th>Pos.</th>
              <th>Balão</th>
              <th>Cor</th>
              <th className="text-end">kg</th>
              <th className="text-end">h produção</th>
              <th className="text-end">h setup forma</th>
              <th className="text-end">h setup cor</th>
              <th>Natureza</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.machine}-${row.shift_index}-${row.position}`}>
                <td>{formatDate(row.date)}</td>
                <td>T{row.shift}</td>
                <td>M{row.machine}</td>
                <td>{row.position}</td>
                <td>{row.product}</td>
                <td>{row.color}</td>
                <td className="text-end">{fmtN(row.kg, 0)}</td>
                <td className="text-end">{fmtN(row.production_hours, 2)}</td>
                <td className="text-end">{row.form_setup_hours > 0 ? fmtN(row.form_setup_hours, 2) : '—'}</td>
                <td className="text-end">{row.color_setup_hours > 0 ? fmtN(row.color_setup_hours, 2) : '—'}</td>
                <td>{natureOf(row)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
