import { downloadCSV } from '../../csv';
import { fmtCSV, fmtN, formatDate } from '../../format';
import type { ProductionRow } from '../../types';

interface DetailedTableProps {
  data: ProductionRow[];
}

export default function DetailedTable({ data }: DetailedTableProps) {
  const sorted = [...data].sort((a, b) => {
    let result;
    if (a.Period !== b.Period) {
      result = a.Period.localeCompare(b.Period);
    } else {
      const machineA = parseInt(a.Machine, 10) || 0;
      const machineB = parseInt(b.Machine, 10) || 0;
      result = machineA !== machineB ? machineA - machineB : a.Product.localeCompare(b.Product);
    }
    return result;
  });

  const handleExport = () => {
    downloadCSV(
      sorted,
      ['Período', 'Máquina', 'Produto', 'Horas', 'Dias', 'kg'],
      (row) => [formatDate(row.Period), `M${row.Machine}`, row.Product, fmtCSV(row.Hours), fmtCSV(row.Hours / 24), fmtCSV(row.Kg)],
      'producao_detalhada.csv',
    );
  };

  return (
    <>
      <div className="table-toolbar">
        <button className="btn btn-sm btn-outline-secondary" onClick={handleExport}>
          Exportar CSV
        </button>
      </div>
      <div className="table-responsive table-scroll">
        <table className="table table-sm table-hover data-table">
          <thead>
            <tr>
              <th>Período</th>
              <th>Máquina</th>
              <th>Produto</th>
              <th className="text-end">Horas</th>
              <th className="text-end">Dias</th>
              <th className="text-end">kg</th>
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr className="table-empty">
                <td colSpan={6}>Execute o planejamento para visualizar os dados.</td>
              </tr>
            ) : (
              sorted.map((row, index) => (
                <tr key={`${row.Period}-${row.Machine}-${row.Product}-${index}`}>
                  <td>{formatDate(row.Period)}</td>
                  <td>M{row.Machine}</td>
                  <td>{row.Product}</td>
                  <td className="text-end">{row.Hours.toFixed(1)} h</td>
                  <td className="text-end">{(row.Hours / 24).toFixed(1)} d</td>
                  <td className="text-end">{fmtN(row.Kg, 2)} kg</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
