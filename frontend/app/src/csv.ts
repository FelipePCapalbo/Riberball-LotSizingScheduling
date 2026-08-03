export function downloadCSV<T>(data: T[], headers: string[], mapper: (row: T) => (string | number)[], filename: string): void {
  if (!data.length) {
    window.alert('Não há dados para exportar.');
  } else {
    let csv = '﻿' + headers.join(';') + '\n';
    for (const row of data) {
      csv += mapper(row).join(';') + '\n';
    }
    const anchor = document.createElement('a');
    anchor.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }));
    anchor.download = filename;
    anchor.click();
  }
}
