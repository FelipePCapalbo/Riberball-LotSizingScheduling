import { useState } from 'react';
import type { ChangeDecision, UploadReview } from '../types';

const TABLE_LABELS: Record<string, string> = {
  products: 'Balões',
  sku_classes: 'Classe MTS/MTO por SKU',
  machines: 'Máquinas',
  productivity: 'Produtividade',
  form_setup: 'Setup de forma',
  color_setup: 'Setup de cor',
  availability: 'Disponibilidade',
};

const COLUMN_LABELS: Record<string, string> = {
  unit_cost: 'custo unitário',
  sale_price: 'preço de venda',
  min_lot_kg: 'lote mínimo',
  is_mts: 'MTS',
  is_active: 'ativa',
  setup_hourly_cost: 'custo de setup (R$/h)',
  kg_per_hour: 'kg/h',
  hours: 'horas',
  availability: 'disponibilidade',
};

interface UploadReviewPanelProps {
  review: UploadReview;
  busy: boolean;
  onApply: (decisions: Record<string, ChangeDecision>) => void;
  onDiscard: () => void;
}

export default function UploadReviewPanel({ review, busy, onApply, onDiscard }: UploadReviewPanelProps) {
  const initialDecisions: Record<string, ChangeDecision> = {};
  for (const conflict of review.conflicts) {
    initialDecisions[String(conflict.change_id)] = 'rejected';
  }
  const [decisions, setDecisions] = useState<Record<string, ChangeDecision>>(initialDecisions);

  const setAll = (decision: ChangeDecision) => {
    const next: Record<string, ChangeDecision> = {};
    for (const conflict of review.conflicts) {
      next[String(conflict.change_id)] = decision;
    }
    setDecisions(next);
  };

  const toggle = (changeId: number) => {
    const key = String(changeId);
    const next = { ...decisions };
    if (next[key] === 'approved') {
      next[key] = 'rejected';
    } else {
      next[key] = 'approved';
    }
    setDecisions(next);
  };

  const insertLines: string[] = [];
  for (const table of Object.keys(review.insert_counts)) {
    let label = table;
    if (TABLE_LABELS[table]) {
      label = TABLE_LABELS[table];
    }
    insertLines.push(`${label}: ${review.insert_counts[table]}`);
  }

  const conflictRows: { changeId: number; table: string; record: string; change: string }[] = [];
  for (const conflict of review.conflicts) {
    const keyParts: string[] = [];
    for (const value of Object.values(conflict.record_key)) {
      keyParts.push(String(value));
    }
    let change = 'Ausente no Excel: o registro sai do cadastro.';
    if (conflict.change_type === 'update' && conflict.old_values && conflict.new_values) {
      const changeParts: string[] = [];
      for (const column of Object.keys(conflict.new_values)) {
        let columnLabel = column;
        if (COLUMN_LABELS[column]) {
          columnLabel = COLUMN_LABELS[column];
        }
        changeParts.push(`${columnLabel}: ${String(conflict.old_values[column])} → ${String(conflict.new_values[column])}`);
      }
      change = changeParts.join('; ');
    }
    let tableLabel = conflict.table_name;
    if (TABLE_LABELS[conflict.table_name]) {
      tableLabel = TABLE_LABELS[conflict.table_name];
    }
    conflictRows.push({ changeId: conflict.change_id, table: tableLabel, record: keyParts.join(' → '), change });
  }

  let approvedCount = 0;
  for (const key of Object.keys(decisions)) {
    if (decisions[key] === 'approved') {
      approvedCount += 1;
    }
  }

  return (
    <div className="modal-overlay">
      <div className="modal-panel">
        <div className="modal-title">Revisão do upload: {review.source_file}</div>

        <div className="modal-section">
          <div className="sb-label">Fotografia de planejamento</div>
          {review.snapshot_sheets.length > 0 && (
            <div className="small">
              Uma nova fotografia será criada e ativada com as abas: {review.snapshot_sheets.join(', ')}.
            </div>
          )}
          {review.snapshot_sheets.length === 0 && (
            <div className="small">O arquivo não traz abas de demanda, carteira ou estoque; a fotografia ativa não muda.</div>
          )}
        </div>

        <div className="modal-section">
          <div className="sb-label">Registros novos no cadastro (entram sem aprovação)</div>
          {insertLines.length > 0 && <div className="small">{insertLines.join(' · ')}</div>}
          {insertLines.length === 0 && <div className="small">Nenhum.</div>}
        </div>

        <div className="modal-section">
          <div className="sb-label">Conflitos com o cadastro ({review.conflicts.length})</div>
          {review.conflicts.length === 0 && <div className="small">Nenhum conflito.</div>}
          {review.conflicts.length > 0 && (
            <>
              <div className="table-toolbar">
                <span className="table-count">{approvedCount} aprovados</span>
                <div>
                  <button type="button" className="btn btn-sm btn-outline-secondary me-2" onClick={() => setAll('approved')}>
                    Aprovar todos
                  </button>
                  <button type="button" className="btn btn-sm btn-outline-secondary" onClick={() => setAll('rejected')}>
                    Rejeitar todos
                  </button>
                </div>
              </div>
              <div className="table-scroll modal-table">
                <table className="data-table w-100">
                  <thead>
                    <tr>
                      <th>Aprovar</th>
                      <th>Cadastro</th>
                      <th>Registro</th>
                      <th>Mudança</th>
                    </tr>
                  </thead>
                  <tbody>
                    {conflictRows.map((row) => (
                      <tr key={row.changeId}>
                        <td>
                          <input
                            type="checkbox"
                            checked={decisions[String(row.changeId)] === 'approved'}
                            onChange={() => toggle(row.changeId)}
                          />
                        </td>
                        <td>{row.table}</td>
                        <td>{row.record}</td>
                        <td className="small">{row.change}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>

        <div className="modal-actions">
          <button type="button" className="btn btn-sm btn-outline-secondary" onClick={onDiscard} disabled={busy}>
            Descartar upload
          </button>
          <button type="button" className="btn-run" onClick={() => onApply(decisions)} disabled={busy}>
            {busy && 'Aplicando...'}
            {!busy && 'Aplicar'}
          </button>
        </div>
      </div>
    </div>
  );
}
