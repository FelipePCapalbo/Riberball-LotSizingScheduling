import { CategoryScale, Chart as ChartJS, Legend, LinearScale, LineElement, PointElement, Tooltip } from 'chart.js';
import { Line } from 'react-chartjs-2';
import { formatDate } from '../../format';
import type { InventoryRow } from '../../types';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

interface InventoryChartProps {
  data: InventoryRow[];
}

export default function InventoryChart({ data }: InventoryChartProps) {
  const periods = Array.from(new Set(data.map((row) => row.Period))).sort();
  const totals = new Map<string, number>();
  for (const period of periods) {
    totals.set(period, 0);
  }
  for (const row of data) {
    totals.set(row.Period, (totals.get(row.Period) ?? 0) + row.Inventory);
  }

  return (
    <Line
      data={{
        labels: periods.map(formatDate),
        datasets: [
          {
            label: 'Estoque (Kg)',
            data: periods.map((period) => totals.get(period) ?? 0),
            borderColor: '#00215D',
            fill: false,
            tension: 0.2,
          },
        ],
      }}
      options={{ responsive: true, maintainAspectRatio: false, scales: { y: { min: 0 } }, plugins: { legend: { display: false } } }}
    />
  );
}
