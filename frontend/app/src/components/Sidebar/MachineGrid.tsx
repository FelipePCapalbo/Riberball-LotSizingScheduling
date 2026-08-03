interface MachineGridProps {
  machines: string[];
  selected: Set<string>;
  onToggle: (machine: string) => void;
  toggledClassName: 'active' | 'selected';
  containerClassName?: string;
}

export default function MachineGrid({ machines, selected, onToggle, toggledClassName, containerClassName }: MachineGridProps) {
  const gridClassName = containerClassName ? `machine-grid ${containerClassName}` : 'machine-grid';

  return (
    <div className={gridClassName}>
      {machines.map((machine) => {
        const boxClassName = selected.has(machine) ? `machine-box ${toggledClassName}` : 'machine-box';
        return (
          <div key={machine} className={boxClassName} onClick={() => onToggle(machine)}>
            <span>M{machine}</span>
          </div>
        );
      })}
    </div>
  );
}
