export function formatDate(iso: string): string {
  const parts = iso.split(' ')[0].split('-');
  if (parts.length === 3) {
    return `${parts[2]}/${parts[1]}/${parts[0]}`;
  } else if (parts.length === 2) {
    return `${parts[1]}/${parts[0]}`;
  } else {
    return iso;
  }
}

export function fmtN(value: number | null | undefined, digits: number): string {
  return (value ?? 0).toLocaleString('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function fmtCSV(value: number | null | undefined): string {
  return (value ?? 0).toFixed(2).replace('.', ',');
}
