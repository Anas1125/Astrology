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

export function login(email: string, password: string) {
  const form = new URLSearchParams({ username: email, password });
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

export function listChartHistory(token: string, filters: { profileId?: string; system?: 'vedic' | 'western'; limit?: number; offset?: number } = {}) {
  const query = new URLSearchParams();
  if (filters.profileId) query.set('profile_id', filters.profileId);
  if (filters.system) query.set('system', filters.system);
  query.set('limit', String(filters.limit ?? 20));
  query.set('offset', String(filters.offset ?? 0));
  return request<ChartHistoryPage>(`/astrology/charts?${query.toString()}`, { method: 'GET' }, token);
}

export type IntelligenceResponseSection = {
  section_type: 'calculated_fact' | 'traditional_interpretation' | 'limitation';
  text: string;
  fact_ids: string[];
  rule_ids: string[];
  fact_references: Array<Record<string, unknown>>;
  rule_references: IntelligenceRuleReference[];
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
export type AIUsage = { daily_limit: number; requests_used: number; remaining: number };
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
export type AIChatResponse = { message: AIMessage; usage: AIUsage };

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
