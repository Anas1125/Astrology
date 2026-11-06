export type BirthTimeParts = { hour: string; minute: string; meridiem: 'AM' | 'PM' };

export function to12HourParts(value: string | null | undefined): BirthTimeParts {
  const match = value?.match(/^(\d{2}):(\d{2})/);
  if (!match) return { hour: '', minute: '', meridiem: 'AM' };
  const h24 = Number(match[1]);
  if (h24 > 23 || Number(match[2]) > 59) return { hour: '', minute: '', meridiem: 'AM' };
  return { hour: String(h24 % 12 || 12).padStart(2, '0'), minute: match[2], meridiem: h24 >= 12 ? 'PM' : 'AM' };
}

export function toBackendBirthTime(parts: BirthTimeParts): string | null {
  if (!parts.hour || !parts.minute) return null;
  const hour = Number(parts.hour);
  const minute = Number(parts.minute);
  if (!Number.isInteger(hour) || hour < 1 || hour > 12 || !Number.isInteger(minute) || minute < 0 || minute > 59) return null;
  const h24 = (hour % 12) + (parts.meridiem === 'PM' ? 12 : 0);
  return `${String(h24).padStart(2, '0')}:${String(minute).padStart(2, '0')}:00`;
}
