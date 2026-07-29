export function formatDate(iso) {
    const p = iso.split(' ')[0].split('-')
    if (p.length === 3) {
        return `${p[2]}/${p[1]}/${p[0]}`
    } else if (p.length === 2) {
        return `${p[1]}/${p[0]}`
    } else {
        return iso
    }
}

export function fmtN(val, digits) {
    return (val ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

export function fmtCSV(val) {
    return (val ?? 0).toFixed(2).replace('.', ',')
}

export function downloadCSV(data, headers, mapper, filename) {
    if (!data?.length) {
        alert('Não há dados para exportar.')
    } else {
        let csv = '﻿' + headers.join(';') + '\n'
        for (const row of data) {
            csv += mapper(row).join(';') + '\n'
        }
        const a = document.createElement('a')
        a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }))
        a.download = filename
        a.click()
    }
}
