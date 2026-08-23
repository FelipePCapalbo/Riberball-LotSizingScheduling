import { useMemo, useState } from 'react';
import type { ReactElement } from 'react';
import { buildColorMap, rankByVolume, OTHER, SETUP_FORM, SETUP_COLOR } from '../../palette';
import { fmtN, formatDate } from '../../format';
import type { ScheduleRow } from '../../types';

interface GanttChartProps {
  data: ScheduleRow[];
  hoursPerShift: number;
  shiftsPerDay: number;
}

const ROW_HEIGHT = 26;
const ROW_GAP = 4;
const COL_WIDTH = 46;
const LABEL_WIDTH = 52;
const HEADER_HEIGHT = 38;

export default function GanttChart({ data, hoursPerShift, shiftsPerDay }: GanttChartProps) {
  const [hover, setHover] = useState<{ x: number; y: number; text: string[] } | null>(null);

  const model = useMemo(() => {
    const machines = Array.from(new Set(data.map((row) => row.machine))).sort(
      (a, b) => parseInt(a, 10) - parseInt(b, 10),
    );
    const shiftIndexes = Array.from(new Set(data.map((row) => row.shift_index))).sort((a, b) => a - b);
    const maxShift = shiftIndexes.length ? shiftIndexes[shiftIndexes.length - 1] : 0;
    const columns: number[] = [];
    for (let i = 0; i <= maxShift; i += 1) {
      columns.push(i);
    }
    const shiftMeta = new Map<number, { date: string; shift: number }>();
    for (const row of data) {
      shiftMeta.set(row.shift_index, { date: row.date, shift: row.shift });
    }
    const ranked = rankByVolume(data, (row) => row.product, (row) => row.kg);
    const colorMap = buildColorMap(ranked);
    const byCell = new Map<string, ScheduleRow[]>();
    for (const row of data) {
      const key = `${row.machine}|${row.shift_index}`;
      const list = byCell.get(key) ?? [];
      list.push(row);
      byCell.set(key, list);
    }
    for (const list of byCell.values()) {
      list.sort((a, b) => a.position - b.position);
    }
    return { machines, columns, shiftMeta, colorMap, ranked, byCell };
  }, [data]);

  if (!data.length) {
    return <div className="empty-state">Nenhuma programação para exibir.</div>;
  }

  const width = LABEL_WIDTH + model.columns.length * COL_WIDTH;
  const height = HEADER_HEIGHT + model.machines.length * (ROW_HEIGHT + ROW_GAP);
  const legendKeys = model.ranked.slice(0, 8);
  const hasOther = model.ranked.length > 8;

  return (
    <div className="gantt-wrapper">
      <div className="gantt-legend">
        {legendKeys.map((key) => (
          <span className="gantt-legend-item" key={key}>
            <span className="gantt-swatch" style={{ background: model.colorMap.get(key) }} />
            {key}
          </span>
        ))}
        {hasOther ? (
          <span className="gantt-legend-item">
            <span className="gantt-swatch" style={{ background: OTHER }} />
            Outros
          </span>
        ) : null}
        <span className="gantt-legend-item">
          <span className="gantt-swatch gantt-swatch--form" />
          Setup de forma
        </span>
        <span className="gantt-legend-item">
          <span className="gantt-swatch gantt-swatch--color" />
          Setup de cor
        </span>
      </div>

      <div className="gantt-scroll">
        <svg width={width} height={height} role="img" aria-label="Programação por máquina e turno">
          <defs>
            <pattern id="hatch-form" width="6" height="6" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
              <rect width="6" height="6" fill={SETUP_FORM} />
              <line x1="0" y1="0" x2="0" y2="6" stroke="#ffffff" strokeWidth="2.5" />
            </pattern>
            <pattern id="hatch-color" width="6" height="6" patternTransform="rotate(135)" patternUnits="userSpaceOnUse">
              <rect width="6" height="6" fill={SETUP_COLOR} />
              <line x1="0" y1="0" x2="0" y2="6" stroke="#ffffff" strokeWidth="2.5" />
            </pattern>
          </defs>

          {model.columns.map((shiftIndex) => {
            const x = LABEL_WIDTH + shiftIndex * COL_WIDTH;
            const meta = model.shiftMeta.get(shiftIndex);
            const isDayStart = shiftIndex % shiftsPerDay === 0;
            return (
              <g key={`hdr-${shiftIndex}`}>
                {isDayStart ? (
                  <line x1={x} y1={0} x2={x} y2={height} stroke="#d6d5cf" strokeWidth="1" />
                ) : null}
                {isDayStart && meta ? (
                  <text x={x + 3} y={13} className="gantt-daylabel">
                    {formatDate(meta.date)}
                  </text>
                ) : null}
                <text x={x + COL_WIDTH / 2} y={30} textAnchor="middle" className="gantt-shiftlabel">
                  T{(shiftIndex % shiftsPerDay) + 1}
                </text>
              </g>
            );
          })}

          {model.machines.map((machine, rowIndex) => {
            const y = HEADER_HEIGHT + rowIndex * (ROW_HEIGHT + ROW_GAP);
            return (
              <g key={machine}>
                <text x={LABEL_WIDTH - 8} y={y + ROW_HEIGHT / 2 + 4} textAnchor="end" className="gantt-machine">
                  M{machine}
                </text>
                <rect
                  x={LABEL_WIDTH}
                  y={y}
                  width={model.columns.length * COL_WIDTH}
                  height={ROW_HEIGHT}
                  fill="#f2f1ec"
                />
                {model.columns.map((shiftIndex) => {
                  const cell = model.byCell.get(`${machine}|${shiftIndex}`);
                  if (!cell) {
                    return null;
                  }
                  const x0 = LABEL_WIDTH + shiftIndex * COL_WIDTH;
                  let cursor = 0;
                  return cell.flatMap((row) => {
                    const segments: ReactElement[] = [];
                    const push = (hours: number, fill: string, kind: string) => {
                      if (hours <= 0) {
                        return;
                      }
                      const w = Math.max(1.5, (hours / hoursPerShift) * COL_WIDTH - 1);
                      const x = x0 + (cursor / hoursPerShift) * COL_WIDTH;
                      segments.push(
                        <rect
                          key={`${machine}-${shiftIndex}-${row.position}-${kind}`}
                          x={x}
                          y={y + 2}
                          width={w}
                          height={ROW_HEIGHT - 4}
                          rx="2"
                          fill={fill}
                          onMouseEnter={(event) =>
                            setHover({
                              x: event.clientX,
                              y: event.clientY,
                              text: [
                                `${formatDate(row.date)} · Turno ${row.shift} · M${row.machine} · pos ${row.position}`,
                                `${row.product} — ${row.color}`,
                                `${fmtN(row.kg, 0)} kg em ${fmtN(row.production_hours, 2)} h`,
                                row.form_setup_hours > 0
                                  ? `Setup de forma ${fmtN(row.form_setup_hours, 2)} h (de ${row.previous_form})`
                                  : '',
                                row.color_setup_hours > 0
                                  ? `Setup de cor ${fmtN(row.color_setup_hours, 2)} h (de ${row.previous_color})`
                                  : '',
                              ].filter((line) => line !== ''),
                            })
                          }
                          onMouseLeave={() => setHover(null)}
                        />,
                      );
                      cursor += hours;
                    };
                    push(row.form_setup_hours, 'url(#hatch-form)', 'sf');
                    push(row.color_setup_hours, 'url(#hatch-color)', 'sc');
                    push(row.production_hours, model.colorMap.get(row.product) ?? OTHER, 'p');
                    return segments;
                  });
                })}
              </g>
            );
          })}
        </svg>
      </div>

      {hover ? (
        <div className="gantt-tooltip" style={{ left: hover.x + 12, top: hover.y + 12 }}>
          {hover.text.map((line) => (
            <div key={line}>{line}</div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
