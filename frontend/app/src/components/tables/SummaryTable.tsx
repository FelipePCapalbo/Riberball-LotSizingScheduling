import { downloadCSV } from '../../csv';
import { fmtCSV, fmtN, formatDate } from '../../format';
import type { SummaryRow } from '../../types';

interface SummaryTableProps {
  data: SummaryRow[];
}

export default function SummaryTable({ data }: SummaryTableProps) {
  const sorted = [...data].sort((a, b) => a.Period.localeCompare(b.Period));

  const handleExport = () => {
    downloadCSV(
      sorted,
      ['Mês', 'Estoque', 'Utilização', 'Demanda', 'Perda', 'Produzido'],
      (row) => [formatDate(row.Period), fmtCSV(row.Inventory), fmtCSV(row.Utilization * 100), fmtCSV(row.Demand), fmtCSV(row.Lost), fmtCSV(row.Production)],
      'resumo_mensal.csv',
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
              <th>Mês</th>
              <th className="text-end">Estoque (Kg)</th>
              <th className="text-end">Utilização</th>
              <th className="text-end">Demanda (Kg)</th>
              <th className="text-end">Perda (Kg)</th>
              <th className="text-end">Produzido (Kg)</th>
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr className="table-empty">
                <td colSpan={6}>Execute o planejamento para visualizar os dados.</td>
              </tr>
            ) : (
              sorted.map((row) => (
                <tr key={row.Period}>
                  <td>{formatDate(row.Period)}</td>
                  <td className="text-end">{fmtN(row.Inventory, 0)}</td>
                  <td className="text-end">{(row.Utilization * 100).toFixed(1)}%</td>
                  <td className="text-end">{fmtN(row.Demand, 0)}</td>
                  <td className="text-end">{fmtN(row.Lost, 0)}</td>
                  <td className="text-end">{fmtN(row.Production, 0)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
