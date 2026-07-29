export default function DataTable({ columns, rows, emptyMessage, onRowClick }) {
    return (
        <table className="table table-sm table-hover data-table">
            <thead>
                <tr>
                    {columns.map(column => (
                        <th key={column.header} className={column.headerClassName}>{column.header}</th>
                    ))}
                </tr>
            </thead>
            <tbody>
                {rows.length === 0 && (
                    <tr className="table-empty">
                        <td colSpan={columns.length}>{emptyMessage}</td>
                    </tr>
                )}
                {rows.map((row, index) => (
                    <tr key={index} className={onRowClick ? 'comparison-row' : undefined} onClick={onRowClick ? () => onRowClick(row) : undefined}>
                        {columns.map(column => (
                            <td key={column.header} className={column.className}>{column.render(row)}</td>
                        ))}
                    </tr>
                ))}
            </tbody>
        </table>
    )
}
