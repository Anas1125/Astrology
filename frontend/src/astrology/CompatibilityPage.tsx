import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { ShieldAlert, UsersRound } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { ApiError, checkCompatibility, listBirthProfiles, listChartHistory } from '../auth/api';
import type {
  BirthProfile,
  ChartHistoryItem,
  CompatibilityAvailability,
  CompatibilityFactor,
} from '../auth/api';

type Language = 'en' | 'ta';
type System = 'vedic' | 'western';

const factorNames: Record<Language, Record<string, string>> = {
  en: {
    Varna: 'Varna',
    Vashya: 'Vashya',
    Tara: 'Tara',
    Yoni: 'Yoni',
    'Graha Maitri': 'Graha Maitri',
    Gana: 'Gana',
    Bhakoot: 'Bhakoot',
    Nadi: 'Nadi',
  },
  ta: {
    Varna: 'வர்ணம்',
    Vashya: 'வசியம்',
    Tara: 'தாரா',
    Yoni: 'யோனி',
    'Graha Maitri': 'கிரக மைத்திரி',
    Gana: 'கணம்',
    Bhakoot: 'பூகூடம்',
    Nadi: 'நாடி',
  },
};

export const compatibilityText = {
  en: {
    title: 'Compatibility',
    intro: 'Compare two saved Vedic D1 charts using the traditional eight-factor Ashtakoota method. The result is an astrology calculation, not a prediction or guarantee about a relationship.',
    system: 'Astrology system',
    vedic: 'Vedic',
    western: 'Western',
    first: 'First profile',
    second: 'Second profile',
    choose: 'Choose a profile',
    chartA: 'First saved D1 chart',
    chartB: 'Second saved D1 chart',
    chooseChart: 'Use latest completed D1 chart',
    noProfiles: 'Create two separate birth profiles to begin.',
    noCharts: 'Each selected profile needs a completed saved Vedic D1 chart.',
    check: 'Calculate Ashtakoota',
    checkWestern: 'Check availability',
    loading: 'Calculating…',
    loadingProfiles: 'Loading profiles…',
    loadingCharts: 'Loading saved charts…',
    missingTitle: 'Completed charts required',
    unavailableTitle: 'Compatibility unavailable',
    availableTitle: 'Ashtakoota result',
    score: 'No score generated',
    method: 'Traditional Ashtakoota scoring is used for this astrology calculation. No score is generated when the required verified chart data is unavailable.',
    missing: 'Two completed saved Vedic D1 charts, one for each selected profile, are required.',
    privacy: 'Both profiles and charts must belong to your account. Profile A is treated as the bride and Profile B as the groom for directional scoring. This is a traditional astrology calculation, not relationship advice.',
    methods: 'Other methods',
    otherMethods: 'Manglik analysis and Western synastry are not included in this report.',
    status: 'Status',
    total: 'Total Guna score',
    breakdown: 'Eight-factor breakdown',
    outOf: 'out of',
    factor: 'Koota',
    points: 'Points',
    noScore: 'No score was generated.',
    bhakootNote: 'Bhakoot cancellation rules have not been evaluated. The displayed Bhakoot points are the base score only.',
    roleNote: 'Directional scoring uses Profile A as bride and Profile B as groom. Reverse profile order to calculate the reverse traditional roles.',
    selectTwo: 'Select two different profiles.',
    partialChart: 'Choose a chart for both profiles, or clear both chart selections to use the latest completed D1 charts.',
    useLatest: 'Leave both chart selections blank to use the latest completed D1 chart for each profile.',
    westernUnavailable: 'Western synastry is not implemented yet. No Western score was generated.',
    completedCount: 'completed charts',
  },
  ta: {
    title: 'பொருத்தம்',
    intro: 'சேமித்த வேத D1 ஜாதகங்களை பாரம்பரிய அஷ்டகூட முறையில் ஒப்பிடுங்கள். இது ஜோதிடக் கணக்கீடு மட்டுமே; உறவின் எதிர்காலத்தை உறுதி செய்யும் கணிப்பு அல்ல.',
    system: 'ஜோதிட முறை',
    vedic: 'வேத',
    western: 'மேற்கத்திய',
    first: 'முதல் விவரம்',
    second: 'இரண்டாம் விவரம்',
    choose: 'விவரத்தைத் தேர்ந்தெடுக்கவும்',
    chartA: 'முதல் சேமித்த D1 ஜாதகம்',
    chartB: 'இரண்டாம் சேமித்த D1 ஜாதகம்',
    chooseChart: 'சமீபத்திய முடிக்கப்பட்ட D1 ஜாதகத்தைப் பயன்படுத்து',
    noProfiles: 'தொடங்க இரண்டு தனித்த பிறப்பு விவரங்களை உருவாக்கவும்.',
    noCharts: 'ஒவ்வொரு விவரத்திற்கும் முடிக்கப்பட்ட சேமித்த வேத D1 ஜாதகம் தேவை.',
    check: 'அஷ்டகூடத்தைக் கணக்கிடு',
    checkWestern: 'கிடைப்பைச் சரிபார்',
    loading: 'கணக்கிடப்படுகிறது…',
    loadingProfiles: 'விவரங்கள் ஏற்றப்படுகின்றன…',
    loadingCharts: 'சேமித்த ஜாதகங்கள் ஏற்றப்படுகின்றன…',
    missingTitle: 'முடிக்கப்பட்ட ஜாதகங்கள் தேவை',
    unavailableTitle: 'பொருத்தம் கிடைக்கவில்லை',
    availableTitle: 'அஷ்டகூட முடிவு',
    score: 'மதிப்பெண் உருவாக்கப்படவில்லை',
    method: 'இந்த ஜோதிடக் கணக்கீட்டிற்கு பாரம்பரிய அஷ்டகூட மதிப்பீடு பயன்படுத்தப்படுகிறது. தேவையான சரிபார்க்கப்பட்ட ஜாதகத் தகவல்கள் இல்லையெனில் மதிப்பெண் உருவாக்கப்படாது.',
    missing: 'தேர்ந்தெடுத்த ஒவ்வொரு விவரத்திற்கும் முடிக்கப்பட்ட சேமித்த வேத D1 ஜாதகம் தேவை.',
    privacy: 'இரண்டு விவரங்களும் ஜாதகங்களும் உங்கள் கணக்கிற்குச் சொந்தமானவை ஆக வேண்டும். திசை சார்ந்த மதிப்பீட்டில் முதல் விவரம் மணமகளாகவும் இரண்டாவது விவரம் மணமகனாகவும் கருதப்படுகிறது. இது பாரம்பரிய ஜோதிடக் கணக்கீடு; உறவு ஆலோசனை அல்ல.',
    methods: 'பிற முறைகள்',
    otherMethods: 'மாங்கல்யப் பகுப்பாய்வும் மேற்கத்திய சினாஸ்ட்ரியும் இந்த அறிக்கையில் சேர்க்கப்படவில்லை.',
    status: 'நிலை',
    total: 'மொத்த குண மதிப்பெண்',
    breakdown: 'எட்டு கூடங்களின் விவரம்',
    outOf: 'மொத்தம்',
    factor: 'கூடம்',
    points: 'மதிப்பெண்',
    noScore: 'மதிப்பெண் உருவாக்கப்படவில்லை.',
    bhakootNote: 'பூகூட தோஷ நிவர்த்தி விதிகள் இன்னும் மதிப்பிடப்படவில்லை. காட்டப்படும் பூகூட மதிப்பெண் அடிப்படை மதிப்பெண் மட்டுமே.',
    roleNote: 'திசை சார்ந்த மதிப்பீட்டில் முதல் விவரம் மணமகளாகவும் இரண்டாவது விவரம் மணமகனாகவும் கருதப்படுகிறது. எதிர் மரபுப் பங்குகளைப் பார்க்க விவரங்களின் வரிசையை மாற்றவும்.',
    selectTwo: 'இரண்டு வேறு விவரங்களைத் தேர்ந்தெடுக்கவும்.',
    partialChart: 'இரண்டு விவரங்களுக்கும் ஜாதகத்தைத் தேர்ந்தெடுக்கவும் அல்லது இரண்டின் தேர்வையும் நீக்கி சமீபத்திய D1 ஜாதகங்களைப் பயன்படுத்தவும்.',
    useLatest: 'இரு ஜாதகத் தேர்வுகளையும் காலியாக விட்டால் ஒவ்வொரு விவரத்திற்கும் சமீபத்திய முடிக்கப்பட்ட D1 ஜாதகம் பயன்படுத்தப்படும்.',
    westernUnavailable: 'மேற்கத்திய சினாஸ்ட்ரி இன்னும் செயல்படுத்தப்படவில்லை. மதிப்பெண் உருவாக்கப்படவில்லை.',
    completedCount: 'முடிக்கப்பட்ட ஜாதகங்கள்',
  },
} as const;

function getStatusTitle(result: CompatibilityAvailability, language: Language) {
  const t = compatibilityText[language];
  if (result.status === 'available') return t.availableTitle;
  if (result.status === 'missing_charts') return t.missingTitle;
  return t.unavailableTitle;
}

function FactorRows({
  factors,
  language,
}: {
  factors: CompatibilityFactor[];
  language: Language;
}) {
  const t = compatibilityText[language];
  return (
    <div className="compatibility-factor-list">
      <div className="compatibility-factor-row compatibility-factor-heading">
        <span>{t.factor}</span>
        <span>{t.points}</span>
      </div>
      {factors.map((factor) => (
        <div className="compatibility-factor-row" key={factor.koota}>
          <span>{factorNames[language][factor.koota] ?? factor.koota}</span>
          <strong>{factor.score} / {factor.maximum}</strong>
        </div>
      ))}
    </div>
  );
}

export default function CompatibilityPage({ language }: { language: Language }) {
  const { token } = useAuth();
  const t = compatibilityText[language];
  const [profiles, setProfiles] = useState<BirthProfile[]>([]);
  const [system, setSystem] = useState<System>('vedic');
  const [first, setFirst] = useState('');
  const [second, setSecond] = useState('');
  const [chartsA, setChartsA] = useState<ChartHistoryItem[]>([]);
  const [chartsB, setChartsB] = useState<ChartHistoryItem[]>([]);
  const [chartA, setChartA] = useState('');
  const [chartB, setChartB] = useState('');
  const [profilesLoading, setProfilesLoading] = useState(true);
  const [chartsLoading, setChartsLoading] = useState(false);
  const [result, setResult] = useState<CompatibilityAvailability | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) return;
    let active = true;
    setProfilesLoading(true);
    void listBirthProfiles(token)
      .then((items) => {
        if (active) {
          setProfiles(items);
          setFirst(items[0]?.id ?? '');
          setSecond(items[1]?.id ?? '');
        }
      })
      .catch((e) => {
        if (active) setError(e instanceof Error ? e.message : 'Request failed');
      })
      .finally(() => {
        if (active) setProfilesLoading(false);
      });
    return () => {
      active = false;
    };
  }, [token]);

  useEffect(() => {
    setResult(null);
    setChartA('');
    setChartB('');
    if (!token || !first || !second || first === second) {
      setChartsA([]);
      setChartsB([]);
      return;
    }

    let active = true;
    setChartsLoading(true);
    void Promise.all([
      listChartHistory(token, { profileId: first, system, limit: 100 }),
      listChartHistory(token, { profileId: second, system, limit: 100 }),
    ])
      .then(([a, b]) => {
        if (active) {
          const isEligible = (item: ChartHistoryItem) =>
            item.status === 'complete' && (system !== 'vedic' || item.division === 'D1');
          setChartsA(a.items.filter(isEligible));
          setChartsB(b.items.filter(isEligible));
        }
      })
      .catch((e) => {
        if (active) setError(e instanceof Error ? e.message : 'Request failed');
      })
      .finally(() => {
        if (active) setChartsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [token, first, second, system]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    if (!first || !second || first === second) {
      setError(t.selectTwo);
      return;
    }
    if (Boolean(chartA) !== Boolean(chartB)) {
      setError(t.partialChart);
      return;
    }

    setLoading(true);
    setError('');
    setResult(null);
    try {
      const response = await checkCompatibility(token, {
        profile_a_id: first,
        profile_b_id: second,
        system,
        ...(chartA && chartB ? { chart_a_id: chartA, chart_b_id: chartB } : {}),
      });
      setResult(response);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : e instanceof Error ? e.message : 'Request failed');
    } finally {
      setLoading(false);
    }
  }

  const canSubmit = Boolean(
    token && first && second && first !== second
    && !chartsLoading && Boolean(chartA) === Boolean(chartB),
  );

  const bhakootCancellation = result?.result?.bhakoot_cancellation;

  return (
    <section className="content-module-page">
      <header className="module-heading">
        <div className="eyebrow">
          <span className="live-dot" /> ASTROAI · {language === 'ta' ? 'உங்கள் பகுதி' : 'YOUR SPACE'}
        </div>
        <h1>{t.title}</h1>
        <p>{t.intro}</p>
      </header>

      <form className="content-module-form" onSubmit={(event) => void submit(event)}>
        <label>
          {t.system}
          <select value={system} onChange={(event) => {
            setSystem(event.target.value as System);
            setResult(null);
            setChartA('');
            setChartB('');
          }}>
            <option value="vedic">{t.vedic}</option>
            <option value="western">{t.western}</option>
          </select>
        </label>

        <label>
          {t.first}
          <select required value={first} onChange={(event) => {
            setFirst(event.target.value);
            setResult(null);
          }}>
            <option value="">{t.choose}</option>
            {profiles.map((profile) => (
              <option key={profile.id} value={profile.id} disabled={profile.id === second}>
                {profile.display_name}
              </option>
            ))}
          </select>
        </label>

        <label>
          {t.second}
          <select required value={second} onChange={(event) => {
            setSecond(event.target.value);
            setResult(null);
          }}>
            <option value="">{t.choose}</option>
            {profiles.map((profile) => (
              <option key={profile.id} value={profile.id} disabled={profile.id === first}>
                {profile.display_name}
              </option>
            ))}
          </select>
        </label>

        <label>
          {t.chartA}
          <select
            value={chartA}
            onChange={(event) => {
              setChartA(event.target.value);
              setResult(null);
            }}
            disabled={chartsLoading || !chartsA.length}
          >
            <option value="">{t.chooseChart}</option>
            {chartsA.map((chart) => (
              <option key={chart.id} value={chart.id}>
                {chart.division} · {new Date(chart.created_at).toLocaleDateString(language === 'ta' ? 'ta-IN' : 'en-IN')}
              </option>
            ))}
          </select>
        </label>

        <label>
          {t.chartB}
          <select
            value={chartB}
            onChange={(event) => {
              setChartB(event.target.value);
              setResult(null);
            }}
            disabled={chartsLoading || !chartsB.length}
          >
            <option value="">{t.chooseChart}</option>
            {chartsB.map((chart) => (
              <option key={chart.id} value={chart.id}>
                {chart.division} · {new Date(chart.created_at).toLocaleDateString(language === 'ta' ? 'ta-IN' : 'en-IN')}
              </option>
            ))}
          </select>
        </label>

        <button className="primary-btn" type="submit" disabled={profilesLoading || loading || !canSubmit}>
          {loading ? t.loading : system === 'vedic' ? t.check : t.checkWestern}
        </button>
      </form>

      {system === 'vedic' && (
        <p className="module-privacy-note">{t.useLatest}</p>
      )}

      {!profilesLoading && profiles.length < 2 && (
        <div className="content-module-notice" role="note">
          <UsersRound size={18} />
          <p>{t.noProfiles}</p>
        </div>
      )}

      {!chartsLoading && first && second && (!chartsA.length || !chartsB.length) && (
        <div className="content-module-notice" role="note">
          <UsersRound size={18} />
          <p>{t.noCharts}</p>
        </div>
      )}

      <p className="module-privacy-note"><ShieldAlert size={16} />{t.privacy}</p>

      {error && <div className="content-module-notice error" role="alert">{error}</div>}

      {/* ASTROAI_COMPATIBILITY_REPORT_LAYOUT_V2 */}
      {result && (
        <section className="content-module-notice compatibility-report" aria-live="polite">
          <div className="compatibility-report__summary">
            <div className="compatibility-report__title-group">
              <span className="compatibility-report__eyebrow">ASTROAI · {language === 'ta' ? 'பொருத்த அறிக்கை' : 'COMPATIBILITY REPORT'}</span>
              <h2>{getStatusTitle(result, language)}</h2>
            </div>
            <p className="compatibility-report__message">{result.message}</p>
            <small className="compatibility-report__meta">
              {result.reason} · {result.completed_chart_count}/2 {t.completedCount}
            </small>
          </div>

          {result.status === 'available' && result.score !== null && (
            <>
              <div className="compatibility-total-score">
                <div className="compatibility-total-score__topline">
                  <span>{t.total}</span>
                  <strong>{result.score}<span> / {result.maximum_score ?? 36}</span></strong>
                </div>
                <div
                  className="compatibility-total-score__track"
                  role="progressbar"
                  aria-label={t.total}
                  aria-valuemin={0}
                  aria-valuemax={result.maximum_score ?? 36}
                  aria-valuenow={result.score}
                >
                  <span
                    style={{
                      width: `${Math.max(0, Math.min(100, (result.score / (result.maximum_score ?? 36)) * 100))}%`,
                    }}
                  />
                </div>
              </div>

              <div className="compatibility-report__factors">
                <div className="compatibility-report__section-heading">
                  <h3>{t.breakdown}</h3>
                  <span>{result.factors.length} / 8</span>
                </div>
                <FactorRows factors={result.factors} language={language} />
              </div>

              <p className="module-privacy-note compatibility-report__footnote">{t.roleNote}</p>
              {bhakootCancellation?.evaluated === false && (
                <p className="module-privacy-note compatibility-report__caution">{t.bhakootNote}</p>
              )}
            </>
          )}

          {result.status !== 'available' && (
            <div className="compatibility-report__unavailable">
              <p>{result.status === 'missing_charts' ? t.missing : system === 'western' ? t.westernUnavailable : t.noScore}</p>
            </div>
          )}
        </section>
      )}

      {system === 'vedic' && (
        <section className="content-module-notice" aria-label={t.methods}>
          <UsersRound size={18} />
          <div>
            <strong>{t.methods}</strong>
            <p>{t.otherMethods}</p>
          </div>
        </section>
      )}
    </section>
  );
}
