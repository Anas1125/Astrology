import { useCallback, useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { MessageCircle, Plus, Send, Trash2 } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import {
  ApiError, createAIConversation, deleteAIConversation, getAIConversation, listAIConversations,
  listBirthProfiles, listChartHistory, streamAIMessage,
} from '../auth/api';
import type { AIConversation, AIConversationHistory, AIMessage, AIUsage, BirthProfile, ChartHistoryItem, IntelligenceResponse } from '../auth/api';

type Language = 'en' | 'ta';
type System = 'vedic' | 'western';
export const aiChatText = {
  en: {
    title: 'AI astrologer', intro: 'Ask reflective questions grounded in your saved chart data.', profile: 'Birth profile', system: 'Astrology system', chart: 'Saved calculated chart', noChart: 'No completed chart (general questions only)',
    noProfiles: 'Add a birth profile before starting a conversation.', create: 'New conversation', history: 'Conversations', send: 'Send', placeholder: 'Ask about your chart…', loading: 'Loading…', empty: 'Choose a conversation or start a new one.',
    noContext: 'No completed saved chart is selected. Personal chart questions will be told when chart information is unavailable; placements are never inferred.', disclaimer: 'Astrology is a traditional belief system, not scientific certainty. Do not rely on it for medical, legal, or financial decisions.',
    unavailable: 'The response engine is temporarily unavailable. Your message may be retried.', failed: 'Could not load conversations.', delete: 'Delete conversation', remaining: 'messages remaining today', providerError: 'The response could not be prepared. Your message may be retried.',
    facts: 'Calculated chart facts', interpretation: 'Traditional interpretation', limitation: 'Limitation', sources: 'Source and edition', factSources: 'Saved chart facts used', chartFact: 'Calculated from this saved chart',
  },
  ta: {
    title: 'AI ஜோதிடர்', intro: 'சேமித்த ஜாதகத் தரவை அடிப்படையாகக் கொண்டு சிந்தனைக்கான கேள்விகளைக் கேளுங்கள்.', profile: 'பிறப்பு விவரம்', system: 'ஜோதிட முறை', chart: 'சேமித்த கணக்கிடப்பட்ட ஜாதகம்', noChart: 'முடிக்கப்பட்ட ஜாதகம் இல்லை (பொதுக் கேள்விகள் மட்டும்)',
    noProfiles: 'உரையாடலைத் தொடங்க முதலில் பிறப்பு விவரத்தைச் சேர்க்கவும்.', create: 'புதிய உரையாடல்', history: 'உரையாடல்கள்', send: 'அனுப்பு', placeholder: 'உங்கள் ஜாதகத்தைப் பற்றி கேளுங்கள்…', loading: 'ஏற்றப்படுகிறது…', empty: 'உரையாடலைத் தேர்ந்தெடுக்கவும் அல்லது புதியதைத் தொடங்கவும்.',
    noContext: 'முடிக்கப்பட்ட சேமித்த ஜாதகம் தேர்ந்தெடுக்கப்படவில்லை. தனிப்பட்ட ஜாதகக் கேள்விகளுக்கு தகவல் இல்லையெனில் தெளிவாகச் சொல்லப்படும்; கிரக நிலைகள் ஊகிக்கப்படாது.', disclaimer: 'ஜோதிடம் ஒரு பாரம்பரிய நம்பிக்கை முறை; அறிவியல் உறுதி அல்ல. மருத்துவ, சட்ட அல்லது நிதி முடிவுகளுக்கு இதை மட்டும் நம்ப வேண்டாம்.',
    unavailable: 'பதில் இயந்திரம் தற்காலிகமாக கிடைக்கவில்லை. செய்தியை மீண்டும் முயற்சிக்கலாம்.', failed: 'உரையாடல்களை ஏற்ற முடியவில்லை.', delete: 'உரையாடலை நீக்கு', remaining: 'இன்றைய மீதமுள்ள செய்திகள்', providerError: 'பதிலைத் தயாரிக்க முடியவில்லை. செய்தியை மீண்டும் முயற்சிக்கலாம்.',
    facts: 'கணக்கிடப்பட்ட ஜாதகத் தகவல்கள்', interpretation: 'பாரம்பரிய விளக்கம்', limitation: 'வரம்பு', sources: 'ஆதாரம் மற்றும் பதிப்பு', factSources: 'பயன்படுத்திய சேமித்த ஜாதகத் தகவல்கள்', chartFact: 'இந்தச் சேமித்த ஜாதகத்திலிருந்து கணக்கிடப்பட்டது',
  },
} as const;

export function StructuredMessage({ response, language }: { response: IntelligenceResponse; language: Language }) {
  const t = aiChatText[language];
  const headings = {
    calculated_fact: t.facts,
    traditional_interpretation: t.interpretation,
    limitation: t.limitation,
  };
  const locator = (source: IntelligenceResponse['sections'][number]['rule_references'][number]) => {
    const labels = language === 'ta'
      ? { chapter: 'அத்தியாயம்', verse: 'சுலோகம்', page: 'பக்கம்' }
      : { chapter: 'Chapter', verse: 'verse', page: 'p.' };
    return [
      source.chapter && `${labels.chapter} ${source.chapter}`,
      source.verse && `${labels.verse} ${source.verse}`,
      source.page && `${labels.page} ${source.page}`,
      source.section,
    ].filter(Boolean).join(' · ') || source.reference;
  };
  return <div className="ai-structured-response">
    <p>{response.answer}</p>
    {response.sections.filter(section => section.text !== response.answer).map((section, index) => <section className={`ai-response-section ${section.section_type}`} key={`${section.section_type}-${index}`}>
      <small>{headings[section.section_type]}</small>
      <p>{section.text}</p>
      {section.section_type === 'calculated_fact' && section.fact_references.length > 0 && <details className="ai-response-sources"><summary>{t.factSources} · {section.fact_references.length}</summary><p>{t.chartFact}</p>{section.fact_references.map((fact, factIndex) => <p key={`${fact.fact_id}-${factIndex}`}><b>{fact.subject}</b> · {fact.predicate}: {String(fact.value)} <small>({fact.system}{fact.division ? ` · ${fact.division}` : ''})</small></p>)}</details>}
      {section.rule_references.length > 0 && <div className="ai-response-sources"><small>{t.sources}</small>{section.rule_references.map((source, sourceIndex) => <p key={`${source.rule_id}-${sourceIndex}`}><b>{source.source_name}</b>{source.edition ? ` · ${source.edition}` : ''}{source.attribution ? ` · ${source.attribution}` : ''}<br/>{locator(source)}</p>)}</div>}
    </section>)}
  </div>;
}

export default function AIChatPage({ language }: { language: Language }) {
  const { token } = useAuth();
  const t = aiChatText[language];
  const [profiles, setProfiles] = useState<BirthProfile[]>([]);
  const [profileId, setProfileId] = useState('');
  const [system, setSystem] = useState<System>('vedic');
  const [charts, setCharts] = useState<ChartHistoryItem[]>([]);
  const [chartId, setChartId] = useState('');
  const [conversations, setConversations] = useState<AIConversation[]>([]);
  const [conversationId, setConversationId] = useState('');
  const [conversation, setConversation] = useState<AIConversationHistory | null>(null);
  const [usage, setUsage] = useState<AIUsage | null>(null);
  const [draft, setDraft] = useState('');
  const [liveResponse, setLiveResponse] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const pendingRequestRef = useRef<{ key: string; content: string } | null>(null);

  const loadConversations = useCallback(async () => {
    if (!token) return;
    const response = await listAIConversations(token);
    setConversations(response.items);
  }, [token]);

  useEffect(() => {
    let active = true;
    if (!token) return;
    setLoading(true); setError('');
    Promise.all([listBirthProfiles(token), listAIConversations(token)])
      .then(([profileRows, conversationRows]) => {
        if (!active) return;
        setProfiles(profileRows);
        setProfileId(current => current && profileRows.some(item => item.id === current) ? current : profileRows[0]?.id ?? '');
        setConversations(conversationRows.items);
      })
      .catch(reason => { if (active) setError(reason instanceof Error ? reason.message : t.failed); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [token, t.failed]);

  useEffect(() => {
    let active = true;
    setCharts([]);
    if (!token || !profileId) return;
    listChartHistory(token, { profileId, system, limit: 100 })
      .then(page => { if (active) setCharts(page.items.filter(item => item.status === 'complete')); })
      .catch(reason => { if (active) setError(reason instanceof Error ? reason.message : t.failed); });
    return () => { active = false; };
  }, [token, profileId, system, t.failed]);

  useEffect(() => {
    let active = true;
    if (!token || !conversationId) { setConversation(null); return; }
    setLoadingMessages(true); setError('');
    getAIConversation(token, conversationId)
      .then(value => { if (active) { setConversation(value); setProfileId(value.profile_id ?? ''); setSystem(value.astrology_system); setChartId(value.chart_id ?? ''); } })
      .catch(reason => { if (active) setError(reason instanceof Error ? reason.message : t.failed); })
      .finally(() => { if (active) setLoadingMessages(false); });
    return () => { active = false; };
  }, [token, conversationId, t.failed]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [conversation?.messages, liveResponse]);

  async function startConversation() {
    if (!token || !profileId) return;
    setError('');
    try {
      const created = await createAIConversation(token, { profile_id: profileId, chart_id: chartId || null, astrology_system: system, language });
      await loadConversations();
      setConversationId(created.id);
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.failed); }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = draft.trim();
    if (!token || !profileId || !content || sending) return;
    setSending(true); setError(''); setLiveResponse('');
    const request = pendingRequestRef.current?.content === content
      ? pendingRequestRef.current
      : { key: crypto.randomUUID(), content };
    pendingRequestRef.current = request;
    let activeConversationId = conversationId;
    try {
      if (!activeConversationId || !conversation || conversation.profile_id !== profileId || conversation.astrology_system !== system || conversation.chart_id !== (chartId || null)) {
        const created = await createAIConversation(token, { profile_id: profileId, chart_id: chartId || null, astrology_system: system, language });
        activeConversationId = created.id;
        setConversationId(created.id);
        await loadConversations();
      }
      setDraft('');
      const result = await streamAIMessage(token, activeConversationId, content, delta => setLiveResponse(current => current + delta), request.key);
      setUsage(result.usage);
      setLiveResponse('');
      pendingRequestRef.current = null;
      setConversation(await getAIConversation(token, activeConversationId));
      await loadConversations();
    } catch (reason) {
      setLiveResponse('');
      setDraft(content);
      setError(reason instanceof ApiError && reason.status === 503 ? t.unavailable : reason instanceof Error ? reason.message : t.providerError);
    } finally { setSending(false); }
  }

  async function removeConversation(item: AIConversation) {
    if (!token) return;
    try {
      await deleteAIConversation(token, item.id);
      setConversations(current => current.filter(value => value.id !== item.id));
      if (conversationId === item.id) { setConversationId(''); setConversation(null); }
    } catch (reason) { setError(reason instanceof Error ? reason.message : t.failed); }
  }

  return <section className="ai-chat-page">
    <header className="ai-chat-heading"><div><div className="eyebrow"><span className="live-dot"/> ASTROAI · {language === 'ta' ? 'சிந்தனைக்கான வழிகாட்டுதல்' : 'REFLECTIVE GUIDANCE'}</div><h1>{t.title}</h1><p>{t.intro}</p></div><span className="ai-status-pill"><MessageCircle size={14}/>{language === 'ta' ? 'தனிப்பட்ட உரையாடல்' : 'PRIVATE CHAT'}</span></header>
    {error && <div className="chart-alert error" role="alert">{error}</div>}
    {loading ? <div className="chart-loading" role="status">{t.loading}</div> : profiles.length === 0 ? <div className="chart-empty"><h2>{t.noProfiles}</h2></div> : <div className="ai-chat-layout">
      <aside className="ai-conversation-sidebar"><div className="ai-side-heading"><h2>{t.history}</h2><button onClick={() => { setConversationId(''); setConversation(null); }} aria-label={t.create}><Plus size={16}/></button></div>
        <div className="ai-conversation-list">{conversations.map(item => <div className={`ai-conversation-row${conversationId === item.id ? ' active' : ''}`} key={item.id}><button className="ai-conversation-select" onClick={() => setConversationId(item.id)}><b>{item.title}</b><small>{item.profile_name ?? ''} · {item.astrology_system === 'vedic' ? (language === 'ta' ? 'வேதம்' : 'Vedic') : (language === 'ta' ? 'மேற்கத்திய' : 'Western')}</small></button><button className="ai-delete-button" aria-label={`${t.delete}: ${item.title}`} onClick={() => void removeConversation(item)}><Trash2 size={14}/></button></div>)}</div>
      </aside>
      <div className="ai-conversation-main">
        <div className="ai-chat-controls">
          <label>{t.profile}<select value={profileId} onChange={event => { setProfileId(event.target.value); setConversationId(''); setConversation(null); }}><option value="">{t.profile}</option>{profiles.map(profile => <option value={profile.id} key={profile.id}>{profile.display_name}</option>)}</select></label>
          <label>{t.system}<select value={system} onChange={event => { setSystem(event.target.value as System); setConversationId(''); setConversation(null); }}><option value="vedic">{language === 'ta' ? 'வேதம்' : 'Vedic'}</option><option value="western">{language === 'ta' ? 'மேற்கத்திய' : 'Western'}</option></select></label>
          <label className="ai-chart-control">{t.chart}<select value={chartId} onChange={event => { setChartId(event.target.value); setConversationId(''); setConversation(null); }}><option value="">{t.noChart}</option>{charts.map(chart => <option key={chart.id} value={chart.id}>{chart.division} · {new Date(chart.created_at).toLocaleDateString(language === 'ta' ? 'ta-IN' : 'en')}</option>)}</select></label>
          {!conversationId && <button className="secondary-action" onClick={() => void startConversation()} disabled={!profileId}><Plus size={15}/>{t.create}</button>}
        </div>
        {!chartId && <p className="ai-context-notice" role="note">{t.noContext}</p>}
        <div className="ai-message-list" aria-live="polite">
          {loadingMessages ? <div className="chart-muted">{t.loading}</div> : conversation?.messages.map(message => <article className={`ai-message ${message.role}`} key={message.id}><small>{message.role === 'user' ? (language === 'ta' ? 'நீங்கள்' : 'You') : 'AstroAI'}</small>{message.role === 'assistant' && message.structured_response ? <StructuredMessage response={message.structured_response} language={language}/> : <p>{message.content}</p>}</article>)}
          {liveResponse && <article className="ai-message assistant"><small>AstroAI</small><p>{liveResponse}</p></article>}
          {!loadingMessages && !conversation?.messages.length && !liveResponse && <p className="ai-chat-empty">{t.empty}</p>}
          <div ref={bottomRef}/>
        </div>
        <form className="ai-chat-compose" onSubmit={event => void submit(event)}><textarea value={draft} onChange={event => setDraft(event.target.value)} maxLength={4000} placeholder={t.placeholder} aria-label={t.placeholder} required disabled={sending || !profileId}/><button className="primary-btn" type="submit" disabled={sending || !draft.trim() || !profileId}>{sending ? (language === 'ta' ? 'உருவாக்குகிறது…' : 'Thinking…') : <>{t.send} <Send size={15}/></>}</button></form>
        {usage && <small className="ai-usage-note">{usage.remaining} {t.remaining}</small>}
        <p className="ai-disclaimer">{t.disclaimer}</p>
      </div>
    </div>}
  </section>;
}
