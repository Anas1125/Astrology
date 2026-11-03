import type { BirthProfile } from '../auth/api';

export type ChartSystem = 'vedic' | 'western';

export function chooseProfileId(profiles: BirthProfile[], current: string, remembered: string | null): string {
  if (current && profiles.some(profile => profile.id === current)) return current;
  if (remembered && profiles.some(profile => profile.id === remembered)) return remembered;
  return profiles[0]?.id ?? '';
}
