export default function DataSection({ open, onToggleOpen, files, activeFile, onSelectFile }) {
    return (
        <div className="sb-section">
            <button className="sb-section-toggle" onClick={onToggleOpen}>
                Dados
                <svg className={open ? 'chevron' : 'chevron rotated'} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="18 15 12 9 6 15" />
                </svg>
            </button>
            {open && (
                <div>
                    <div className="sb-field">
                        <label>Arquivo de input</label>
                        <select
                            className="form-select form-select-sm"
                            value={activeFile || ''}
                            onChange={e => onSelectFile(e.target.value)}
                        >
                            {files.map(file => (
                                <option key={file} value={file}>{file}</option>
                            ))}
                        </select>
                    </div>
                </div>
            )}
        </div>
    )
}
