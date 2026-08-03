export interface KpiItem {
  label: string;
  value: string | number | null | undefined;
  small?: boolean;
}

interface KpiBarProps {
  items: KpiItem[];
}

export default function KpiBar({ items }: KpiBarProps) {
  return (
    <div className="kpi-bar">
      {items.map((item) => (
        <div className="kpi-item" key={item.label}>
          <span className="kpi-label">{item.label}</span>
          <span className={item.small ? 'kpi-value kpi-value--small' : 'kpi-value'}>{item.value ?? '—'}</span>
        </div>
      ))}
    </div>
  );
}
