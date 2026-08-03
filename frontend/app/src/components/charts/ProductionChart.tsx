import { useState } from 'react';
import { BarElement, CategoryScale, Chart as ChartJS, Legend, LinearScale, Tooltip } from 'chart.js';
import { Bar } from 'react-chartjs-2';
import { formatDate } from '../../format';
import type { ProductionRow } from '../../types';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

const PALETTE = [
  '#2563eb', '#16a34a', '#dc2626', '#d97706', '#7c3aed',
  '#0891b2', '#be185d', '#65a30d', '#ea580c', '#6366f1',
  '#0f766e', '#b45309', '#9333ea', '#0284c7', '#15803d',
];

interface ProductionChartProps {
  data: ProductionRow[];
}

export default function ProductionChart({ data }: ProductionChartProps) {
  const [selectedMachines, setSelectedMachines] = useState<Set<string>>(new Set());

  const periods = Array.from(new Set(data.map((row) => row.Period))).sort();
  const allMachines = Array.from(new Set(data.map((row) => row.Machine))).sort(
    (a, b) => (parseInt(a, 10) || 0) - (parseInt(b, 10) || 0),
  );
  const colorOf = (machine: string) => PALETTE[allMachines.indexOf(machine) % PALETTE.length];

  const toggleMachine = (machine: string) => {
    const next = new Set(selectedMachines);
    if (next.has(machine)) {
      next.delete(machine);
    } else {
      next.add(machine);
    }
    setSelectedMachines(next);
  };

  const showingAggregate = selectedMachines.size === 0;

  let datasets;
  if (showingAggregate) {
    datasets = [
      {
        label: 'Total',
        data: periods.map((period) => data.filter((row) => row.Period === period).reduce((sum, row) => sum + row.Kg, 0)),
        backgroundColor: '#2563eb',
      },
    ];
  } else {
    datasets = Array.from(selectedMachines).map((machine) => ({
      label: `M${machine}`,
      data: periods.map((period) =>
        data.filter((row) => row.Period === period && row.Machine === machine).reduce((sum, row) => sum + row.Kg, 0),
      ),
      backgroundColor: colorOf(machine),
    }));
  }

  return (
    <div>
      <div className="chart-card-header">
        <span className="chart-title">Produção Agregada (Kg)</span>
        <div className="prod-filter">
          <button
            className={showingAggregate ? 'filter-chip active' : 'filter-chip'}
            onClick={() => setSelectedMachines(new Set())}
          >
            Todas
          </button>
          <div className="d-flex flex-wrap gap-1">
            {allMachines.map((machine) => (
              <button
                key={machine}
                className={selectedMachines.has(machine) ? 'filter-chip selected' : 'filter-chip'}
                onClick={() => toggleMachine(machine)}
              >
                M{machine}
              </button>
            ))}
          </div>
        </div>
      </div>
      <div className="chart-box">
        <Bar
          data={{ labels: periods.map(formatDate), datasets }}
          options={{
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: !showingAggregate, position: 'bottom', labels: { boxWidth: 10, font: { size: 10 } } } },
            scales: {
              x: { stacked: !showingAggregate },
              y: { stacked: !showingAggregate, title: { display: true, text: 'Kg' } },
            },
          }}
        />
      </div>
    </div>
  );
}
