export type Account = { id: string; email: string; role: string };
export type TokenResponse = { access_token: string; token_type: string };

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(message: string, readonly status: number) { super(message); this.name = 'ApiError'; }
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      ...(init.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`;
    if (response.status === 401 && typeof window !== 'undefined') window.dispatchEvent(new Event('astroai:unauthorized'));
    throw new ApiError(detail, response.status);
  }
  return body as T;
}

export function register(email: string, password: string) {
  return request<TokenResponse>('/auth/register', { method: 'POST', body: JSON.stringify({ email, password }) });
}

export function login(email: string, password: string, rememberMe = false) {
  const form = new URLSearchParams({ username: email, password, remember_me: String(rememberMe) });
  return request<TokenResponse>('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: form,
  });
}

export function getAccount(token: string) {
  return request<Account>('/auth/me', { method: 'GET' }, token);
}

export type BirthProfile = {
  id: string;
  display_name: string;
  relationship: string;
  birth_date: string;
  birth_time: string | null;
  time_accuracy: string;
  birthplace: string;
  country: string;
  latitude: number | null;
  longitude: number | null;
  timezone: string | null;
};

export type BirthProfileInput = Omit<BirthProfile, 'id'>;

export function listBirthProfiles(token: string) {
  return request<BirthProfile[]>('/profiles', { method: 'GET' }, token);
}

export type LocationSuggestion = {
  id: string; city: string; region: string | null; country: string; latitude: number;
  longitude: number; timezone: string | null; attribution: string;
};

export function searchBirthplaces(token: string, query: string, language: 'en' | 'ta', signal?: AbortSignal) {
  const params = new URLSearchParams({ q: query, language });
  return request<LocationSuggestion[]>(`/profiles/location-search?${params}`, { method: 'GET', signal }, token);
}

export type PanchangResult = {
  local_date: string;
  calculated_at: string;
  location_name: string;
  timezone: string;
  sunrise: string;
  sunset: string;
  elements_at: 'sunrise';
  tithi: { index: number; name: string; paksha: string };
  vara: { index: number; name: string };
  nakshatra: { index: number; name: string; longitude: number };
  yoga: { index: number; name: string };
  karana: { index: number; name: string };
  daytime_windows: Record<'rahu_kalam' | 'yamagandam' | 'gulika_kalam' | 'abhijit_muhurta', {
    part: number; parts_in_daylight: number; start: string; end: string;
  }>;
  transitions: Record<'tithi' | 'nakshatra' | 'yoga' | 'karana', { at: string; next_index: number; next_name: string; next_paksha?: string }>;
  calculation: Record<string, string>;
};

export function calculateDailyPanchang(token: string, input: {
  local_date: string; location_name: string; latitude: number; longitude: number; timezone: string;
}) {
  return request<PanchangResult>('/panchang/daily', { method: 'POST', body: JSON.stringify(input) }, token);
}

export type HoroscopeAvailability = {
  status: 'available' | 'missing_chart' | 'unavailable'; mode: 'general' | 'personalized'; system: 'vedic' | 'western';
  local_date: string; period: 'daily' | 'weekly' | 'monthly'; category: 'overview' | 'career' | 'relationships' | 'finance' | 'personal_growth';
  sign: string | null; chart_id: string | null; content: string | null;
  source_references: Array<string | Record<string, unknown>>; reason: string; message: string;
};

export function checkDailyHoroscope(token: string, input: {
  mode: 'general' | 'personalized'; system: 'vedic' | 'western'; local_date: string;
  period?: 'daily' | 'weekly' | 'monthly'; category?: 'overview' | 'career' | 'relationships' | 'finance' | 'personal_growth';
  language: 'en' | 'ta'; sign?: string; profile_id?: string; chart_id?: string;
}) {
  return request<HoroscopeAvailability>('/horoscope/daily', { method: 'POST', body: JSON.stringify(input) }, token);
}

export type CompatibilityFactor = {
  koota: string;
  score: number;
  maximum: number;
  convention?: string;
  [key: string]: unknown;
};

export type CompatibilityAvailability = {
  status: 'missing_charts' | 'unavailable' | 'available';
  system: 'vedic' | 'western';
  profiles_checked: 2;
  completed_chart_count: number;
  chart_ids: [string | null, string | null];
  score: number | null;
  maximum_score?: number;
  factors: CompatibilityFactor[];
  reason: string;
  message: string;
  report_id?: string;
  result?: {
    bhakoot_cancellation?: {
      dosha_detected?: boolean;
      evaluated?: boolean;
      status?: string;
    };
    role_mapping?: {
      profile_a?: string;
      profile_b?: string;
      note?: string;
    };
    [key: string]: unknown;
  };
};

export function checkCompatibility(token: string, input: {
  profile_a_id: string;
  profile_b_id: string;
  system: 'vedic' | 'western';
  chart_a_id?: string;
  chart_b_id?: string;
}) {
  return request<CompatibilityAvailability>(
    '/compatibility/check',
    { method: 'POST', body: JSON.stringify(input) },
    token,
  );
}

export function createBirthProfile(token: string, profile: BirthProfileInput) {
  return request<BirthProfile>('/profiles', { method: 'POST', body: JSON.stringify(profile) }, token);
}

export function updateBirthProfile(token: string, id: string, profile: BirthProfileInput) {
  return request<BirthProfile>(`/profiles/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(profile) }, token);
}

export function deleteBirthProfile(token: string, id: string) {
  return request<void>(`/profiles/${encodeURIComponent(id)}`, { method: 'DELETE' }, token);
}

export type ChartCalculationResponse = {
  chart_id: string;
  calculation_run_id: string;
  profile_id: string;
  calculation_system: 'vedic' | 'western';
  status: string;
  engine_version: string | null;
  ephemeris_version: string | null;
  configuration: Record<string, unknown>;
  input_snapshot: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  calculated_at: string;
};

export type WesternHouseSystem = 'P' | 'W' | 'K' | 'R' | 'C' | 'E' | 'O' | 'B' | 'M' | 'A' | 'V' | 'X' | 'H' | 'T';
export type AspectOrbs = Partial<Record<'conjunction' | 'sextile' | 'square' | 'trine' | 'opposition', number>>;

export function calculateVedicChart(token: string, profileId: string, division: 'D1' | 'D9', houseSystem: WesternHouseSystem = 'P') {
  return request<ChartCalculationResponse>('/astrology/charts/vedic', {
    method: 'POST',
    body: JSON.stringify({ profile_id: profileId, division, house_system: houseSystem, dasha_year_convention: 'savana_360_day' }),
  }, token);
}

export function calculateWesternChart(token: string, profileId: string, houseSystem: WesternHouseSystem = 'P', aspectOrbs?: AspectOrbs) {
  return request<ChartCalculationResponse>('/astrology/charts/western', {
    method: 'POST',
    body: JSON.stringify({ profile_id: profileId, house_system: houseSystem, ...(aspectOrbs ? { aspect_orbs: aspectOrbs } : {}) }),
  }, token);
}

export function getSavedChart(token: string, chartId: string) {
  return request<ChartCalculationResponse>(`/astrology/charts/${encodeURIComponent(chartId)}`, { method: 'GET' }, token);
}

export type ChartHistoryItem = {
  id: string;
  profile_id: string;
  profile_name: string;
  system: 'vedic' | 'western';
  division: string;
  status: string;
  created_at: string;
  configuration: Record<string, unknown>;
  unavailable_reason: string | null;
};

export type ChartHistoryPage = { items: ChartHistoryItem[]; total: number; limit: number; offset: number };

export type VedicDignityPlanet = {
  planet: string; sidereal_longitude: number; rashi: string; degree_in_rashi: number;
  sign_lord: string; relationship_to_sign_lord: 'self' | 'friend' | 'neutral' | 'enemy';
  dignity: 'exalted' | 'debilitated' | 'moolatrikona' | 'own_sign' | 'friend_sign' | 'neutral_sign' | 'enemy_sign';
  is_exalted_sign: boolean; is_in_exaltation_range: boolean; is_debilitated_sign: boolean; is_at_deep_exaltation_degree: boolean;
  is_at_deep_debilitation_degree: boolean; is_moolatrikona: boolean;
  exaltation_reference: { sign: string; deep_degree: number };
  debilitation_reference: { sign: string; deep_degree: number };
  moolatrikona_range: { sign: string; start_degrees: number; end_degrees_exclusive: number };
  source_rule_set: string; source_id: string; source_locator: string;
};

export type VedicDignityAnalysis = {
  status: 'provisional'; chart_id: string; profile_id: string; astrology_system: 'vedic'; division: 'D1';
  zodiac: 'sidereal'; ayanamsa: string; ruleset_id: string; ruleset_version: string;
  source_id: string; source_ids: string[]; source_references: Array<{ source_id: string; edition_id: string; title: string; edition: string; url: string | null; verification_status: string; commercial_reuse_status: string }>;
  source_status: string; source_locator: string; methodology_note: string;
  shadbala: { status: 'unavailable'; reason: string }; planets: VedicDignityPlanet[]; excluded_planets: string[];
};

export function getVedicDignity(token: string, chartId: string) {
  return request<VedicDignityAnalysis>(`/astrology/charts/${encodeURIComponent(chartId)}/vedic-dignity`, { method: 'GET' }, token);
}

export function listChartHistory(token: string, filters: { profileId?: string; system?: 'vedic' | 'western'; limit?: number; offset?: number } = {}) {
  const query = new URLSearchParams();
  if (filters.profileId) query.set('profile_id', filters.profileId);
  if (filters.system) query.set('system', filters.system);
  query.set('limit', String(filters.limit ?? 20));
  query.set('offset', String(filters.offset ?? 0));
  return request<ChartHistoryPage>(`/astrology/charts?${query.toString()}`, { method: 'GET' }, token);
}

export type IntelligenceResponseSection = {
  section_type: 'general_education' | 'calculated_fact' | 'traditional_interpretation' | 'limitation';
  text: string;
  fact_ids: string[];
  rule_ids: string[];
  fact_references: IntelligenceFactReference[];
  rule_references: IntelligenceRuleReference[];
};
export type IntelligenceFactReference = {
  fact_id: string;
  subject: string;
  predicate: string;
  value: string | number | boolean;
  source_chart_id: string;
  profile_id: string;
  system: 'vedic' | 'western';
  division: string | null;
  provenance: string;
};
export type IntelligenceRuleReference = {
  rule_id: string;
  rule_version: string;
  knowledge_base_version: string;
  chart_id: string;
  profile_id: string;
  system: 'vedic' | 'western';
  division: string | null;
  source_name: string;
  attribution: string;
  reference: string;
  editorial_status: 'approved';
  classification: 'traditional_interpretation';
  source_id?: string | null;
  source_registry_version?: string | null;
  edition_id?: string | null;
  edition?: string | null;
  chapter?: string | null;
  verse?: string | null;
  page?: string | null;
  section?: string | null;
};
export type IntelligenceResponse = {
  status: 'answered' | 'missing_chart' | 'unsupported' | 'needs_clarification';
  answer: string;
  answer_fact_ids: string[];
  answer_rule_ids: string[];
  sections: IntelligenceResponseSection[];
  metadata: {
    engine_version: string;
    knowledge_base_version: string;
    system: 'vedic' | 'western' | null;
    division: string | null;
    language: 'en' | 'ta';
    matched_rule_ids: string[];
    content_classification?: 'general_education' | 'personal_chart_response' | null;
    source_verification_status?: 'not_applicable' | 'not_independently_verified';
    education_topic?: string | null;
  };
};

export type AIMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  structured_response: IntelligenceResponse | null;
  provider: string | null;
  model: string | null;
  prompt_version: string | null;
  input_tokens: number;
  output_tokens: number;
  created_at: string;
};
export type AIConversation = {
  id: string;
  profile_id: string | null;
  profile_name: string | null;
  chart_id: string | null;
  astrology_system: 'vedic' | 'western';
  language: 'en' | 'ta';
  title: string;
  created_at: string;
  updated_at: string;
};
export type AIConversationHistory = AIConversation & { messages: AIMessage[] };
export type AIConversationList = { items: AIConversation[]; total: number };
export type AIChatResponse = { message: AIMessage };

export function requestPasswordReset(email: string) {
  return request<{ message: string }>('/auth/forgot-password', {
    method: 'POST', body: JSON.stringify({ email }),
  });
}

export function resetPassword(token: string, newPassword: string) {
  return request<{ message: string }>('/auth/reset-password', {
    method: 'POST', body: JSON.stringify({ token, new_password: newPassword }),
  });
}

export function createAIConversation(token: string, payload: { profile_id: string; chart_id?: string | null; astrology_system: 'vedic' | 'western'; language: 'en' | 'ta'; title?: string }) {
  return request<AIConversation>('/ai/conversations', { method: 'POST', body: JSON.stringify(payload) }, token);
}

export function listAIConversations(token: string, limit = 50, offset = 0) {
  return request<AIConversationList>(`/ai/conversations?limit=${limit}&offset=${offset}`, { method: 'GET' }, token);
}

export function getAIConversation(token: string, id: string) {
  return request<AIConversationHistory>(`/ai/conversations/${encodeURIComponent(id)}`, { method: 'GET' }, token);
}

export function deleteAIConversation(token: string, id: string) {
  return request<void>(`/ai/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' }, token);
}

export async function streamAIMessage(token: string, conversationId: string, content: string, onDelta: (content: string) => void, requestKey: string = crypto.randomUUID()): Promise<AIChatResponse> {
  const response = await fetch(`${API_BASE}/ai/conversations/${encodeURIComponent(conversationId)}/messages/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}`, Accept: 'text/event-stream', 'Idempotency-Key': requestKey },
    body: JSON.stringify({ content }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`;
    if (response.status === 401 && typeof window !== 'undefined') window.dispatchEvent(new Event('astroai:unauthorized'));
    throw new ApiError(detail, response.status);
  }
  if (!response.body) throw new ApiError('AI stream is unavailable in this browser.', 502);
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let completed: AIChatResponse | null = null;
  const consume = (block: string) => {
    let event = 'message';
    const data: string[] = [];
    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith('event:')) event = line.slice(6).trim();
      else if (line.startsWith('data:')) data.push(line.slice(5).trimStart());
    }
    if (!data.length) return;
    const payload = JSON.parse(data.join('\n')) as { content?: string; detail?: string; status?: string } | AIChatResponse;
    if (event === 'delta' && 'content' in payload && typeof payload.content === 'string') onDelta(payload.content);
    else if (event === 'done') completed = payload as AIChatResponse;
    else if (event === 'error') throw new ApiError(('detail' in payload && payload.detail) || 'AI response failed.', 502);
  };
  try {
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      let boundary: number;
      while ((boundary = buffer.search(/\r?\n\r?\n/)) !== -1) {
        const block = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary).replace(/^\r?\n\r?\n/, '');
        consume(block);
      }
      if (done) break;
    }
    if (buffer.trim()) consume(buffer);
  } finally { reader.releaseLock(); }
  if (!completed) throw new ApiError('The AI stream ended before the response was saved.', 502);
  return completed;
}
// Simple bilingual horoscope content management (admin-only endpoints).
export type HoroscopeAdminContent = {
  scope_key: string;
  system: 'vedic' | 'western';
  period: 'daily' | 'weekly' | 'monthly';
  sign: string;
  category: 'overview' | 'career' | 'relationships' | 'finance' | 'personal_growth';
  starts_on: string;
  ends_on: string;
  en_content: string;
  ta_content: string;
  languages_present: string[];
  published: boolean;
};
export type HoroscopeAdminDraftInput = {
  system: 'vedic' | 'western';
  period: 'daily' | 'weekly' | 'monthly';
  sign: string;
  category: 'overview' | 'career' | 'relationships' | 'finance' | 'personal_growth';
  starts_on: string;
  ends_on: string;
  en_content: string;
  ta_content: string;
};
export type HoroscopeAdminDraftUpdate = Pick<HoroscopeAdminDraftInput, 'starts_on' | 'ends_on' | 'en_content' | 'ta_content'>;

export function listAdminHoroscopeContent(token: string) {
  return request<{ items: HoroscopeAdminContent[] }>('/admin/horoscope/content', { method: 'GET' }, token);
}
export function createAdminHoroscopeDraft(token: string, payload: HoroscopeAdminDraftInput) {
  return request<{ scope_key: string; status: string }>('/admin/horoscope/content', { method: 'POST', body: JSON.stringify(payload) }, token);
}
export function updateAdminHoroscopeDraft(token: string, scopeKey: string, payload: HoroscopeAdminDraftUpdate) {
  return request<{ scope_key: string; previous_scope_key: string; status: string }>(`/admin/horoscope/content/${encodeURIComponent(scopeKey)}`, { method: 'PUT', body: JSON.stringify(payload) }, token);
}
export function publishAdminHoroscopeContent(token: string, scopeKey: string) {
  return request<HoroscopeAdminContent>(`/admin/horoscope/content/${encodeURIComponent(scopeKey)}/publish`, { method: 'POST' }, token);
}
export function unpublishAdminHoroscopeContent(token: string, scopeKey: string) {
  return request<HoroscopeAdminContent>(`/admin/horoscope/content/${encodeURIComponent(scopeKey)}/unpublish`, { method: 'POST' }, token);
}
export function deleteAdminHoroscopeContent(token: string, scopeKey: string) {
  return request<{ scope_key: string; status: string }>(`/admin/horoscope/content/${encodeURIComponent(scopeKey)}`, { method: 'DELETE' }, token);
}


export type HoroscopeBulkImportRow = {
  system: 'vedic' | 'western';
  period: 'daily' | 'weekly' | 'monthly';
  sign: string;
  category: 'overview' | 'career' | 'relationships' | 'finance' | 'personal_growth';
  starts_on: string;
  ends_on: string;
  en_content: string;
  ta_content: string;
};

export function bulkImportAdminHoroscopeContent(token: string, items: HoroscopeBulkImportRow[]) {
  return request<{ created: number; skipped: number; status: string }>(
    '/admin/horoscope/content/bulk-import',
    { method: 'POST', body: JSON.stringify({ items }) },
    token,
  );
}


export function bulkPublishAdminHoroscopeContent(token: string) {
  return request<{ published: number; skipped: number; status: string }>(
    '/admin/horoscope/content/publish-all',
    { method: 'POST' },
    token,
  );
}

export type VastuRoomInput = {
  room_type: 'kitchen' | 'master_bedroom' | 'bedroom' | 'prayer_room' | 'bathroom' | 'living_room' | 'study_room' | 'dining_room' | 'other';
  x: number;
  y: number;
};

export type VastuRoomObservation = {
  room_number: number;
  room_type: VastuRoomInput['room_type'];
  room_en: string;
  room_ta: string;
  direction: string;
  direction_ta: string;
  status: 'preferred' | 'alternative' | 'review' | 'varies' | 'not_assessed';
  title_en: string;
  title_ta: string;
  detail_en: string;
  detail_ta: string;
};

export type VastuAnalysis = {
  room_count: number;
  north_side: 'top' | 'right' | 'bottom' | 'left';
  rooms: VastuRoomObservation[];
  method_en: string;
  method_ta: string;
  caution_en: string;
  caution_ta: string;
};

export type VastuBoundaryPoint = { x: number; y: number };

export async function analyzeVastuFloorPlan(
  token: string,
  file: File,
  northSide: 'top' | 'right' | 'bottom' | 'left',
  rooms: VastuRoomInput[],
  boundary: VastuBoundaryPoint[],
): Promise<VastuAnalysis> {
  const form = new FormData();
  form.append('file', file, file.name);
  form.append('north_side', northSide);
  form.append('rooms', JSON.stringify(rooms));
  form.append('boundary', JSON.stringify(boundary));
  const response = await fetch(`${API_BASE}/vastu/analyze`, {
    method: 'POST', headers: { Authorization: `Bearer ${token}` }, body: form,
  });
  let payload: unknown;
  try { payload = await response.json(); } catch { payload = null; }
  if (!response.ok) {
    const detail = payload && typeof payload === 'object' && 'detail' in payload
      ? String((payload as { detail: unknown }).detail)
      : 'Unable to review this floor plan.';
    throw new ApiError(detail, response.status);
  }
  return payload as VastuAnalysis;
}
