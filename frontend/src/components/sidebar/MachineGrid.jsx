export default function MachineGrid({ machines, selected, onToggle, variant }) {
    const containerClass = variant === 'high-setup' ? 'machine-grid high-setup-grid' : 'machine-grid'
    const toggledClass = variant === 'high-setup' ? 'selected' : 'active'

    return (
        <div className={containerClass}>
            {machines.map(machine => (
                <div
                    key={machine}
                    className={selected.includes(machine) ? `machine-box ${toggledClass}` : 'machine-box'}
                    onClick={() => onToggle(machine)}
                >
                    <span>M{machine}</span>
                </div>
            ))}
        </div>
    )
}
