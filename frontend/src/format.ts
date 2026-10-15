export function termLabel(code: string): string {
  if (/^1\d{2}[159]$/.test(code)) {
    const season = { '1': 'Winter', '5': 'Spring', '9': 'Fall' }[code[3]];
    return `${season} ${2000 + Number(code.slice(1, 3))}`;
  }
  return `Term ${code}`;
}

export function dateLabel(value: string): string {
  // SQLite may serialize the existing UTC created_at column without an offset.
  const date = new Date(/(?:Z|[+-]\d{2}:\d{2})$/i.test(value) ? value : `${value}Z`);
  return Number.isNaN(date.getTime()) ? 'Time unavailable' : date.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
}
