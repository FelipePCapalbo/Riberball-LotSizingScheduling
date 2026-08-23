import { BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, Tooltip } from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { SETUP_FORM, SETUP_COLOR, CATEGORICAL } from '../../palette';
import { fmtN } from '../../format';
import type { ScheduleRow } from '../../types';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

interface MachineSetupChartProps {
  data: ScheduleRow[];
}

/* Um segmento empilhado de valor zero com borderWidth quebra a geometria do Chart.js;
   emitir null faz o ponto ser ignorado e preserva o espaçador de 2px entre segmentos. */
function orNull(value: number): number | null {
  return value > 1e-6 ? value : null;
}

export default function MachineSetupChart({ data }: MachineSetupChartProps) {
  const machines = Array.from(new Set(data.map((row) => row.machine))).sort(
    (a, b) => parseInt(a, 10) - parseInt(b, 10),
  );
  const production: (number | null)[] = [];
  const formSetup: (number | null)[] = [];
  const colorSetup: (number | null)[] = [];
  for (const machine of machines) {
    let p = 0;
    let f = 0;
    let c = 0;
    for (const row of data) {
      if (row.machine === machine) {
        p += row.production_hours;
        f += row.form_setup_hours;
        c += row.color_setup_hours;
      }
    }
    production.push(orNull(p));
    formSetup.push(orNull(f));
    colorSetup.push(orNull(c));
  }

  const base = { borderWidth: 2, borderColor: '#fcfcfb', borderRadius: 4 };

  return (
    <Bar
      data={{
        labels: machines.map((m) => `M${m}`),
        datasets: [
          { label: 'Produção', data: production, backgroundColor: CATEGORICAL[0], ...base },
          { label: 'Setup de forma', data: formSetup, backgroundColor: SETUP_FORM, ...base },
          { label: 'Setup de cor', data: colorSetup, backgroundColor: SETUP_COLOR, ...base },
        ],
      }}
      options={{
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { stacked: true, grid: { display: false } },
          y: { stacked: true, min: 0, title: { display: true, text: 'horas' } },
        },
        plugins: {
          legend: { position: 'bottom' },
          tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${fmtN(ctx.parsed.y, 2)} h` } },
        },
      }}
    />
  );
}
