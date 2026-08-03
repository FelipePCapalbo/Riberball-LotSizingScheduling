import { downloadCSV } from '../../csv';
import { fmtCSV, fmtN, formatDate } from '../../format';
import type { SetupRow } from '../../types';

interface SetupsTableProps {
  data: SetupRow[];
}

export default function SetupsTable({ data }: SetupsTableProps) {
  const sorted = [...data].sort((a, b) => {
    let result;
    if (a.Period !== b.Period) {
      result = a.Period.localeCompare(b.Period);
    } else {
      result = (parseInt(a.Machine, 10) || 0) - (parseInt(b.Machine, 10) || 0);
    }
    return result;
  });

  const handleExport = () => {
    downloadCSV(
      sorted,
      ['Período', 'Máquina', 'De', 'Para', 'Custo (R$)'],
      (row) => [formatDate(row.Period), `M${row.Machine}`, row.From, row.To, fmtCSV(row.Cost || 0)],
      'setups_detalhado.csv',
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
              <th>De</th>
              <th>Para</th>
              <th className="text-end">Custo (R$)</th>
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr className="table-empty">
                <td colSpan={5}>Nenhum setup.</td>
              </tr>
            ) : (
              sorted.map((row, index) => (
                <tr key={`${row.Period}-${row.Machine}-${row.Day}-${index}`}>
                  <td>{formatDate(row.Period)}</td>
                  <td>M{row.Machine}</td>
                  <td>{row.From}</td>
                  <td>{row.To}</td>
                  <td className="text-end">R$ {fmtN(row.Cost || 0, 2)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
