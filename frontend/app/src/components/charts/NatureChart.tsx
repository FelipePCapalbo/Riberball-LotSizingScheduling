import { BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, Tooltip } from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { NATURE_COLORS } from '../../palette';
import { fmtN, formatDate } from '../../format';
import type { WeeklyDemandRow, WeeklyProductionRow } from '../../types';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

interface NatureChartProps {
  demand: WeeklyDemandRow[];
  production: WeeklyProductionRow[];
}

export default function NatureChart({ demand, production }: NatureChartProps) {
  /* Um segmento empilhado de valor zero com borderWidth quebra a geometria do Chart.js;
     emitir null faz o ponto ser ignorado e preserva o espacador de 2px entre segmentos. */
  const orNull = (value: number) => (value > 1e-6 ? value : null);
  const weeks = Array.from(new Set(demand.map((row) => row.week))).sort();
  const toOrders: (number | null)[] = [];
  const toForecast: (number | null)[] = [];
  const toStock: (number | null)[] = [];

  for (const week of weeks) {
    let produced = 0;
    for (const row of production) {
      if (row.week === week) {
        produced += row.kg;
      }
    }
    let deliveredOrders = 0;
    let deliveredForecast = 0;
    for (const row of demand) {
      if (row.week === week) {
        deliveredOrders += row.delivered_orders;
        deliveredForecast += row.delivered_forecast;
      }
    }
    const a = Math.min(produced, deliveredOrders);
    const b = Math.min(produced - a, deliveredForecast);
    toOrders.push(orNull(a));
    toForecast.push(orNull(b));
    toStock.push(orNull(Math.max(0, produced - a - b)));
  }

  return (
    <Bar
      data={{
        labels: weeks.map(formatDate),
        datasets: [
          { label: 'Contra pedido', data: toOrders, backgroundColor: NATURE_COLORS.order, borderWidth: 2, borderColor: '#fcfcfb', borderRadius: 4 },
          { label: 'Contra previsão', data: toForecast, backgroundColor: NATURE_COLORS.forecast, borderWidth: 2, borderColor: '#fcfcfb', borderRadius: 4 },
          { label: 'Contra estoque', data: toStock, backgroundColor: NATURE_COLORS.stock, borderWidth: 2, borderColor: '#fcfcfb', borderRadius: 4 },
        ],
      }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, min: 0, title: { display: true, text: 'kg produzidos' } } },
        plugins: {
          legend: { position: 'bottom' },
          tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${fmtN(ctx.parsed.y, 0)} kg` } },
        },
      }}
    />
  );
}
