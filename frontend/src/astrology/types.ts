export type PlanetPosition = {
  name: string;
  longitude: number;
  latitude?: number;
  distance_au?: number;
  longitude_speed_deg_per_day?: number;
  retrograde?: boolean;
  flags?: number;
  sign?: string;
  sign_index?: number;
  degrees_in_sign?: number;
  house?: number;
  nakshatra?: { index: number; name: string; lord: string; pada: number; remaining_fraction: number; degrees_remaining: number; rashi: string; degrees_in_rashi: number };
  d9?: { segment: number; rashi_index: number; rashi: string; longitude: number };
  division_longitude?: number;
  division_rashi?: string;
  division_rashi_index?: number;
  division_house?: number;
};

export type HouseCusp = { number: number; cusp_longitude: number; sign?: string; sign_index?: number; degrees_in_sign?: number };
export type ChartAngle = { longitude: number; sign?: string; sign_index?: number; rashi_index?: number; degrees_in_sign?: number; house?: number; rashi?: string; name?: string; index?: number; pada?: number; lord?: string; d9?: { segment: number; rashi_index: number; rashi: string; longitude: number }; division_longitude?: number; division_rashi?: string; division_rashi_index?: number; division_house?: number };
export type ChartAspect = { planet_a: string; planet_b: string; aspect: string; angle: number; separation: number; orb: number; allowed_orb: number; motion?: 'applying' | 'separating' | 'exact' | 'unknown'; applying?: boolean | null };
export type DashaPeriod = { lord: string; start: string; end: string; full_duration_days: number; full_duration_years?: number; balance_days_at_birth?: number | null; elapsed_days_at_birth?: number; remaining_days_at_birth?: number | null; mahadasha_lord?: string; antardasha_lord?: string };
export type AstrologyResult = {
  calculation_system: 'vedic' | 'western';
  division?: 'D1' | 'D9';
  calculated_at?: string;
  engine_version?: string;
  western_engine_version?: string;
  vedic_engine_version?: string;
  ephemeris_version?: string;
  calculation_flags?: { requested?: number; houses?: number; apparent?: boolean; geocentric?: boolean; ephemeris?: string };
  configuration?: Record<string, unknown>;
  planets: PlanetPosition[];
  houses: HouseCusp[];
  division_houses?: HouseCusp[];
  ascendant?: ChartAngle;
  midheaven?: ChartAngle;
  ascendant_longitude?: number;
  midheaven_longitude?: number;
  aspects?: ChartAspect[];
  vimshottari_dasha?: { year_convention: string; year_length_days: number; starting_nakshatra: string; starting_lord: string; birth_balance_days: number; mahadashas: DashaPeriod[]; antardashas: DashaPeriod[]; pratyantardashas?: DashaPeriod[] };
};

export function isAstrologyResult(value: Record<string, unknown> | null, system: 'vedic' | 'western'): value is Record<string, unknown> & AstrologyResult {
  return Boolean(value && value.calculation_system === system && Array.isArray(value.planets) && Array.isArray(value.houses));
}
