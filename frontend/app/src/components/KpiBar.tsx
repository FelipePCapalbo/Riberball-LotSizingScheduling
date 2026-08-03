import type { Kpis } from '../types';

interface KpiBarProps {
  visible: boolean;
  kpis: Kpis | undefined;
  durationSeconds: number | undefined;
  dataFile: string | null | undefined;
}

export default function KpiBar({ visible, kpis, durationSeconds, dataFile }: KpiBarProps) {
  const cost = kpis?.total_cost != null ? 'R$ ' + kpis.total_cost.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : '—';
  const service = kpis?.service_level != null ? kpis.service_level.toFixed(1) + '%' : '—';
  const inventory = kpis?.avg_inventory != null ? kpis.avg_inventory.toLocaleString('pt-BR', { maximumFractionDigits: 0 }) + ' Kg' : '—';
  const duration = durationSeconds != null ? durationSeconds.toFixed(1) + ' s' : '—';

  return (
    <div className={visible ? 'kpi-bar' : 'kpi-bar d-none'}>
      <div className="kpi-item">
        <span className="kpi-label">Custo Total</span>
        <span className="kpi-value">{cost}</span>
      </div>
      <div className="kpi-item">
        <span className="kpi-label">Nível de Serviço</span>
        <span className="kpi-value">{service}</span>
      </div>
      <div className="kpi-item">
        <span className="kpi-label">Estoque Médio</span>
        <span className="kpi-value">{inventory}</span>
      </div>
      <div className="kpi-item">
        <span className="kpi-label">Tempo de Execução</span>
        <span className="kpi-value">{duration}</span>
      </div>
      <div className="kpi-item">
        <span className="kpi-label">Input</span>
        <span className="kpi-value kpi-value--small">{dataFile || '—'}</span>
      </div>
    </div>
  );
}
