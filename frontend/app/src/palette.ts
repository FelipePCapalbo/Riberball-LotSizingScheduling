export const CATEGORICAL = [
  '#2a78d6',
  '#eb6834',
  '#1baf7a',
  '#eda100',
  '#e87ba4',
  '#008300',
  '#4a3aa7',
  '#e34948',
];

export const OTHER = '#8a8985';

export const NATURE_COLORS = {
  order: '#2a78d6',
  forecast: '#eb6834',
  stock: '#1baf7a',
};

export const SETUP_FORM = '#52514e';
export const SETUP_COLOR = '#a3a29c';

export function buildColorMap(keys: string[]): Map<string, string> {
  const map = new Map<string, string>();
  keys.forEach((key, index) => {
    map.set(key, index < CATEGORICAL.length ? CATEGORICAL[index] : OTHER);
  });
  return map;
}

export function rankByVolume<T>(rows: T[], keyOf: (row: T) => string, valueOf: (row: T) => number): string[] {
  const totals = new Map<string, number>();
  for (const row of rows) {
    const key = keyOf(row);
    totals.set(key, (totals.get(key) ?? 0) + valueOf(row));
  }
  return Array.from(totals.entries())
    .sort((a, b) => b[1] - a[1])
    .map((entry) => entry[0]);
}
