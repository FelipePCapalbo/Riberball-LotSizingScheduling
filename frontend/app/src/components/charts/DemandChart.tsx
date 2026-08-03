import { BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, LineElement, PointElement, Tooltip } from 'chart.js';
import { Chart } from 'react-chartjs-2';
import { formatDate } from '../../format';
import type { DemandRow } from '../../types';

ChartJS.register(CategoryScale, LinearScale, BarElement, PointElement, LineElement, Tooltip, Legend);

interface DemandChartProps {
  data: DemandRow[];
}

export default function DemandChart({ data }: DemandChartProps) {
  const periods = Array.from(new Set(data.map((row) => row.Period))).sort();
  const met = new Map<string, number>();
  const lost = new Map<string, number>();
  const total = new Map<string, number>();
  for (const period of periods) {
    met.set(period, 0);
    lost.set(period, 0);
    total.set(period, 0);
  }
  for (const row of data) {
    met.set(row.Period, (met.get(row.Period) ?? 0) + row.Met);
    lost.set(row.Period, (lost.get(row.Period) ?? 0) + row.Lost);
    total.set(row.Period, (total.get(row.Period) ?? 0) + row.Demand);
  }

  return (
    <Chart
      type="bar"
      data={{
        labels: periods.map(formatDate),
        datasets: [
          { label: 'Atendida', data: periods.map((p) => met.get(p) ?? 0), backgroundColor: '#198754' },
          { label: 'Perdida', data: periods.map((p) => lost.get(p) ?? 0), backgroundColor: '#dc3545' },
          {
            type: 'line' as const,
            label: 'Total',
            data: periods.map((p) => total.get(p) ?? 0),
            borderColor: '#000',
            borderWidth: 2,
            pointRadius: 0,
          },
        ],
      }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        scales: { x: { stacked: true }, y: { stacked: true } },
      }}
    />
  );
}
