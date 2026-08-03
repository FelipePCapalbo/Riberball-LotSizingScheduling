import { useState } from 'react';
import KpiBar from '../KpiBar';
import Tabs from '../Tabs';
import { fmtN } from '../../format';
import type { ColorRunResult } from '../../types';

interface ColorTabProps {
  result: ColorRunResult | null;
  statusText: string;
  statusColor: string;
}

export default function ColorTab({ result, statusText, statusColor }: ColorTabProps) {
  const [subTab, setSubTab] = useState('schedule');

  const colorSchedule = result?.color_schedule ?? [];
  const colorOrders = result?.orders ?? [];
  const colorSetups = result?.color_setups ?? [];

  const scheduleSorted = [...colorSchedule].sort((a, b) => {
    let comparison;
    if (a.day !== b.day) {
      comparison = a.day - b.day;
    } else {
      comparison = (parseInt(a.machine, 10) || 0) - (parseInt(b.machine, 10) || 0);
    }
    return comparison;
  });
  const ordersSorted = [...colorOrders].sort((a, b) => a.due_day - b.due_day);
  const setupsSorted = [...colorSetups].sort((a, b) => {
    let comparison;
    if (a.day !== b.day) {
      comparison = a.day - b.day;
    } else {
      comparison = (parseInt(a.machine, 10) || 0) - (parseInt(b.machine, 10) || 0);
    }
    return comparison;
  });

  const kpiItems = [
    { label: 'Nível de Serviço (Cor)', value: result?.kpis?.service_level != null ? result.kpis.service_level.toFixed(1) + '%' : null },
    { label: 'Custo de Atraso', value: result?.kpis?.delay_cost != null ? 'R$ ' + result.kpis.delay_cost.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : null },
    { label: 'Custo de Troca', value: result?.kpis?.setup_cost != null ? 'R$ ' + result.kpis.setup_cost.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : null },
    { label: 'Trocas de Cor', value: result?.kpis?.total_setups ?? null },
    { label: 'Tempo de Execução', value: result?.duration_seconds != null ? result.duration_seconds.toFixed(1) + ' s' : null },
    { label: 'Método', value: result ? (result.method === 'milp' ? 'Modelo matemático' : 'Heurística') : null, small: true },
  ];

  return (
    <div>
      <div className="table-toolbar">
        <div className="run-status" style={{ color: statusColor }}>
          {statusText}
        </div>
      </div>

      {result ? <KpiBar items={kpiItems} /> : null}

      <Tabs
        variant="sub"
        activeKey={subTab}
        onChange={setSubTab}
        tabs={[
          {
            key: 'schedule',
            label: 'Sequência',
            content: (
              <div className="table-responsive table-scroll">
                <table className="table table-sm table-hover data-table">
                  <thead>
                    <tr>
                      <th>Dia</th>
                      <th>Máquina</th>
                      <th>Produto</th>
                      <th>Cor</th>
                      <th className="text-end">Horas</th>
                      <th className="text-end">Kg</th>
                    </tr>
                  </thead>
                  <tbody>
                    {scheduleSorted.length === 0 ? (
                      <tr className="table-empty">
                        <td colSpan={6}>Nenhum dado.</td>
                      </tr>
                    ) : (
                      scheduleSorted.map((row, index) => (
                        <tr key={`${row.day}-${row.machine}-${row.product}-${index}`}>
                          <td>{row.day}</td>
                          <td>M{row.machine}</td>
                          <td>{row.product}</td>
                          <td>{row.color}</td>
                          <td className="text-end">{row.hours.toFixed(1)} h</td>
                          <td className="text-end">{fmtN(row.kg, 2)} kg</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            ),
          },
          {
            key: 'orders',
            label: 'Pedidos',
            content: (
              <div className="table-responsive table-scroll">
                <table className="table table-sm table-hover data-table">
                  <thead>
                    <tr>
                      <th>SKU</th>
                      <th className="text-end">Prazo (dia)</th>
                      <th className="text-end">Quantidade</th>
                      <th className="text-end">Atraso</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ordersSorted.length === 0 ? (
                      <tr className="table-empty">
                        <td colSpan={5}>Nenhum dado.</td>
                      </tr>
                    ) : (
                      ordersSorted.map((row, index) => (
                        <tr key={`${row.sku}-${row.due_day}-${index}`}>
                          <td>{row.sku}</td>
                          <td className="text-end">{row.due_day}</td>
                          <td className="text-end">{fmtN(row.quantity, 0)}</td>
                          <td className="text-end">{fmtN(row.delayed_qty, 0)}</td>
                          <td>
                            {row.delayed_qty <= 0.001 ? (
                              <span className="badge badge-success">No prazo</span>
                            ) : (
                              <span className="badge badge-danger">Atrasado</span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            ),
          },
          {
            key: 'setups',
            label: 'Trocas de Cor',
            content: (
              <div className="table-responsive table-scroll">
                <table className="table table-sm table-hover data-table">
                  <thead>
                    <tr>
                      <th>Dia</th>
                      <th>Máquina</th>
                      <th>Produto</th>
                      <th>De</th>
                      <th>Para</th>
                      <th className="text-end">Setup (h)</th>
                      <th className="text-end">Custo (R$)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {setupsSorted.length === 0 ? (
                      <tr className="table-empty">
                        <td colSpan={7}>Nenhuma troca.</td>
                      </tr>
                    ) : (
                      setupsSorted.map((row, index) => (
                        <tr key={`${row.day}-${row.machine}-${index}`}>
                          <td>{row.day}</td>
                          <td>M{row.machine}</td>
                          <td>{row.product}</td>
                          <td>{row.from_color}</td>
                          <td>{row.to_color}</td>
                          <td className="text-end">{row.setup_time.toFixed(2)}</td>
                          <td className="text-end">R$ {fmtN(row.cost || 0, 2)}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            ),
          },
        ]}
      />
    </div>
  );
}
