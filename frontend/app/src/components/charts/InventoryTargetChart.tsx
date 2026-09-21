import { CategoryScale, Chart as ChartJS, Legend, LinearScale, LineElement, PointElement, Tooltip } from 'chart.js';
import { Line } from 'react-chartjs-2';
import { CATEGORICAL } from '../../palette';
import { fmtN, formatDate } from '../../format';
import type { WeeklyInventoryRow } from '../../types';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

interface InventoryTargetChartProps {
  data: WeeklyInventoryRow[];
}

export default function InventoryTargetChart({ data }: InventoryTargetChartProps) {
  const weeks = Array.from(new Set(data.map((row) => row.week))).sort();
  const inventory: number[] = [];
  for (const week of weeks) {
    let i = 0;
    for (const row of data) {
      if (row.week === week) {
        i += row.inventory;
      }
    }
    inventory.push(i);
  }

  return (
    <Line
      data={{
        labels: weeks.map(formatDate),
        datasets: [
          { label: 'Estoque projetado', data: inventory, borderColor: CATEGORICAL[0], backgroundColor: CATEGORICAL[0], borderWidth: 2, pointRadius: 4, tension: 0.2 },
        ],
      }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        scales: { y: { min: 0, title: { display: true, text: 'kg' } }, x: { grid: { display: false } } },
        plugins: {
          legend: { position: 'bottom' },
          tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${fmtN(ctx.parsed.y, 0)} kg` } },
        },
      }}
    />
  );
}
