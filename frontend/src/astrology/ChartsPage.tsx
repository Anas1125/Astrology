import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ChangeEvent } from 'react';
import { useAuth } from '../auth/AuthContext';
import { ApiError, calculateVedicChart, calculateWesternChart, getSavedChart, getVedicDignity, listBirthProfiles, listChartHistory } from '../auth/api';
import type { BirthProfile, ChartCalculationResponse, ChartHistoryItem, ChartHistoryPage, VedicDignityAnalysis, WesternHouseSystem } from '../auth/api';
import { astroLabel } from './i18n';
import type { AstroLanguage } from './i18n';
import { isAstrologyResult } from './types';
import type { AstrologyResult } from './types';
import { VedicChartView } from './VedicChartView';
import WesternChartView from './WesternChartView';
import { VedicDignitySection } from './VedicDignitySection';
import { chooseProfileId } from './chartUtils';
import { ChartEmptyState, ChartErrorState, ChartLoadingState } from './ChartFeedback';
import { ArrowUpRight, RefreshCw, Sparkles } from 'lucide-react';

type System = 'vedic' | 'western';
type Division = 'D1' | 'D9';
type HouseOption = { code: WesternHouseSystem; label: string };
const HOUSE_OPTIONS: HouseOption[] = [
  { code: 'P', label: 'Placidus' }, { code: 'W', label: 'Whole Sign' }, { code: 'E', label: 'Equal (Ascendant)' },
  { code: 'K', label: 'Koch' }, { code: 'R', label: 'Regiomontanus' }, { code: 'C', label: 'Campanus' },
  { code: 'O', label: 'Porphyry' }, { code: 'B', label: 'Alcabitius' }, { code: 'M', label: 'Morinus' },
  { code: 'A', label: 'Equal (MC)' }, { code: 'V', label: 'Vehlow Equal' }, { code: 'X', label: 'Meridian' },
  { code: 'H', label: 'Horizon' }, { code: 'T', label: 'Polich/Page' },
];

function selectedChartResponse(response: ChartCalculationResponse, system: System): AstrologyResult | null {
  if (response.calculation_system !== system || response.status !== 'complete' || !isAstrologyResult(response.result, system)) return null;
  return response.result;
}

export default function ChartsPage({ system, language, onSystemChange, onManageProfiles }: {
  system: System;
  language: AstroLanguage;
  onSystemChange: (system: System) => void;
  onManageProfiles: () => void;
}) {
  const { token, account } = useAuth();
  const [profiles, setProfiles] = useState<BirthProfile[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [profilesLoading, setProfilesLoading] = useState(true);
  const [profilesError, setProfilesError] = useState('');
  const [division, setDivision] = useState<Division>('D1');
  const [houseSystem, setHouseSystem] = useState<WesternHouseSystem>('P');
  const [chart, setChart] = useState<ChartCalculationResponse | null>(null);
  const [chartLoading, setChartLoading] = useState(false);
  const [calculating, setCalculating] = useState(false);
  const [chartError, setChartError] = useState<{ message: string; status?: number } | null>(null);
  const [history, setHistory] = useState<ChartHistoryPage | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState('');
  const [historyOffset, setHistoryOffset] = useState(0);
  const [dignity, setDignity] = useState<VedicDignityAnalysis | null>(null);
  const [dignityLoading, setDignityLoading] = useState(false);
  const [dignityError, setDignityError] = useState('');
  const t = useCallback((key: Parameters<typeof astroLabel>[1]) => astroLabel(language, key), [language]);

  const loadProfiles = useCallback(async () => {
    if (!token) return;
    setProfilesLoading(true); setProfilesError('');
    try {
      const values = await listBirthProfiles(token);
      setProfiles(values);
      setSelectedId(current => {
        const remembered = account ? sessionStorage.getItem(`astroai_selected_profile:${account.id}`) : null;
        return chooseProfileId(values, current, remembered);
      });
    } catch (reason) {
      setProfilesError(reason instanceof Error ? reason.message : t('errorTitle'));
    } finally { setProfilesLoading(false); }
  }, [token, account, t]);

  useEffect(() => { void loadProfiles(); }, [loadProfiles]);

  const selectedProfile = useMemo(() => profiles.find(profile => profile.id === selectedId) ?? null, [profiles, selectedId]);
  const isLimitedProfile = Boolean(selectedProfile && (!selectedProfile.birth_time || selectedProfile.time_accuracy === 'unknown'));
  useEffect(() => { if (isLimitedProfile && division !== 'D1') setDivision('D1'); }, [isLimitedProfile, division]);
  useEffect(() => {
    if (!account || !selectedId) return;
    sessionStorage.setItem(`astroai_selected_profile:${account.id}`, selectedId);
  }, [account, selectedId]);

  useEffect(() => {
    setChart(null); setChartError(null);
    setChartLoading(false);
  }, [selectedId, system]);

  useEffect(() => {
    let cancelled = false;
    setDignity(null); setDignityError('');
    if (!token || !chart || system !== 'vedic' || division !== 'D1' || chart.status !== 'complete' || chart.result?.division !== 'D1' || chart.result?.calculation_mode === 'limited_date_only') {
      setDignityLoading(false);
      return () => { cancelled = true; };
    }
    setDignityLoading(true);
    void getVedicDignity(token, chart.chart_id)
      .then(value => { if (!cancelled) setDignity(value); })
      .catch(reason => { if (!cancelled) setDignityError(reason instanceof Error ? reason.message : t('errorTitle')); })
      .finally(() => { if (!cancelled) setDignityLoading(false); });
    return () => { cancelled = true; };
  }, [token, chart, system, division, t]);

  useEffect(() => {
    let cancelled = false;
    if (!token || !selectedId) { setHistory(null); return; }
    setHistoryLoading(true); setHistoryError('');
    void listChartHistory(token, { profileId: selectedId, system, limit: 10, offset: historyOffset })
      .then(page => { if (!cancelled) setHistory(page); })
      .catch(reason => { if (!cancelled) setHistoryError(reason instanceof Error ? reason.message : t('errorTitle')); })
      .finally(() => { if (!cancelled) setHistoryLoading(false); });
    return () => { cancelled = true; };
  }, [token, selectedId, system, historyOffset, t]);

  const refreshHistory = useCallback(async () => {
    if (!token || !selectedId) return;
    try {
      setHistory(await listChartHistory(token, { profileId: selectedId, system, limit: 10, offset: historyOffset }));
      setHistoryError('');
    } catch (reason) { setHistoryError(reason instanceof Error ? reason.message : t('errorTitle')); }
  }, [token, selectedId, system, historyOffset, t]);

  function updateSelected(event: ChangeEvent<HTMLSelectElement>) {
    setSelectedId(event.target.value); setChart(null); setChartError(null); setHistoryOffset(0);
  }

  async function openHistory(item: ChartHistoryItem) {
    setChart(null); setChartError(null);
    if (item.status !== 'complete') {
      setChartError({ message: item.unavailable_reason || t('historyUnavailable'), status: 503 });
      return;
    }
    if (item.system === 'vedic') setDivision(item.division === 'D9' ? 'D9' : 'D1');
    setChartLoading(true);
    try {
      const saved = await getSavedChart(token!, item.id);
      if (!selectedChartResponse(saved, item.system)) throw new Error(t('systemError'));
      setChart(saved);
    } catch (reason) {
      setChartError({ message: reason instanceof Error ? reason.message : t('errorTitle'), status: reason instanceof ApiError ? reason.status : undefined });
    } finally { setChartLoading(false); }
  }

  async function calculate() {
    if (!token || !selectedProfile) { setChartError({ message: t('profileRequired') }); return; }
    setCalculating(true); setChartError(null); setChart(null);
    try {
      const calculated = system === 'vedic'
        ? await calculateVedicChart(token, selectedProfile.id, division, houseSystem)
        : await calculateWesternChart(token, selectedProfile.id, houseSystem);
      if (!selectedChartResponse(calculated, system)) throw new Error(t('systemError'));
      const saved = await getSavedChart(token, calculated.chart_id);
      if (!selectedChartResponse(saved, system)) throw new Error(t('systemError'));
      setChart(saved);
      await refreshHistory();
    } catch (reason) {
      setChartError({ message: reason instanceof Error ? reason.message : t('errorTitle'), status: reason instanceof ApiError ? reason.status : undefined });
    } finally { setCalculating(false); }
  }

  const hasRequiredLocation = Boolean(selectedProfile?.timezone && selectedProfile.latitude !== null && selectedProfile.latitude !== undefined && selectedProfile.longitude !== null && selectedProfile.longitude !== undefined);
  const hasRequiredBirthData = Boolean(selectedProfile && hasRequiredLocation && (isLimitedProfile || (selectedProfile.birth_time && selectedProfile.time_accuracy !== 'unknown')));
  const isUnavailable = chartError?.status === 503;
  const canRetryChartRequest = chartError?.status === undefined || (chartError.status >= 500 && chartError.status !== 503);
  const result = chart ? selectedChartResponse(chart, system) : null;

  return <section className="charts-page">
    <div className="charts-heading"><div><div className="eyebrow"><span className="live-dot"/> ASTROAI · {language === 'ta' ? 'உங்கள் பகுதி' : 'YOUR SPACE'}</div><h1>{t('title')}</h1><p>{language === 'ta' ? 'உங்கள் பிறப்பு விவரங்களின் அடிப்படையில் கணக்கிடப்பட்ட ஜாதக நிலைகள்.' : 'Calculated chart placements from your saved birth information.'}</p></div><span className="chart-version-pill"><Sparkles size={14}/>{system === 'vedic' ? 'SIDEREAL · LAHIRI' : 'TROPICAL'}</span></div>

    <div className="chart-request-panel">
      <label className="chart-select-field"><span>{t('system')}</span><select aria-label={t('system')} value={system} onChange={event => { setHistoryOffset(0); onSystemChange(event.target.value as System); }}><option value="vedic">{t('vedic')}</option><option value="western">{t('western')}</option></select></label>
      <label className="chart-select-field profile-select"><span>{t('profile')}</span><select aria-label={t('profile')} value={selectedId} onChange={updateSelected} disabled={profilesLoading || profiles.length === 0}><option value="">{profilesLoading ? t('loadingProfiles') : t('profileRequired')}</option>{profiles.map(profile => <option value={profile.id} key={profile.id}>{profile.display_name} · {profile.birthplace}</option>)}</select></label>
      {system === 'vedic' && <label className="chart-select-field"><span>{t('division')}</span><select aria-label={t('division')} value={division} onChange={event => { setDivision(event.target.value as Division); setChart(null); setChartError(null); }}><option value="D1">{t('d1')}</option><option value="D9" disabled={isLimitedProfile}>{t('d9')}</option></select></label>}
{!isLimitedProfile && (
      <label className="chart-select-field"><span>{t('houseSystem')}</span><select aria-label={t('houseSystem')} value={houseSystem} onChange={event => { setHouseSystem(event.target.value as WesternHouseSystem); setChart(null); setChartError(null); }}>{HOUSE_OPTIONS.map(option => <option key={option.code} value={option.code}>{language === 'ta' ? option.code === 'P' ? t('plSystem') : option.code === 'W' ? t('wholeSign') : option.code === 'E' ? t('equal') : option.label : option.label}</option>)}</select></label>
      )}
      <button className="primary-btn chart-calculate-btn" onClick={() => void calculate()} disabled={profilesLoading || calculating || chartLoading || !selectedProfile || !hasRequiredBirthData}>{calculating ? t('calculating') : <>{t('calculate')} <ArrowUpRight size={15}/></>}</button>
    </div>

    {isLimitedProfile && hasRequiredLocation && <div className="chart-alert" role="status">{t('limitedChartNote')}</div>}
    {profilesError && <div className="chart-alert error" role="alert"><span>{profilesError}</span><button onClick={() => void loadProfiles()}>{t('retry')}</button></div>}
    {selectedProfile && <section className="chart-history" aria-labelledby="chart-history-title">
      <div className="chart-history-heading"><h2 id="chart-history-title">{t('history')}</h2><span>{history?.total ?? 0}</span></div>
      {historyError && <div className="chart-alert error" role="alert"><span>{historyError}</span><button onClick={() => void refreshHistory()}>{t('retry')}</button></div>}
      {historyLoading ? <div className="chart-muted" role="status">{t('loadingChart')}</div> : !historyError && (history?.items.length ?? 0) === 0 ? <p className="chart-muted">{t('noHistory')}</p> : <>
        <div className="chart-history-list">{history?.items.map(item => <button className="chart-history-item" key={item.id} onClick={() => void openHistory(item)}>
          <span><b>{item.system === 'vedic' ? t('vedic') : t('western')} · {item.division}</b><small>{item.profile_name} · {new Date(item.created_at).toLocaleString(language === 'ta' ? 'ta-IN' : 'en', { dateStyle: 'medium', timeStyle: 'short' })}</small></span>
          <span className={`chart-history-status ${item.status === 'complete' ? 'complete' : 'unavailable'}`}>{item.status === 'complete' ? (language === 'ta' ? 'முடிந்தது' : 'Complete') : (language === 'ta' ? 'கிடைக்கவில்லை' : 'Unavailable')}</span>
          <span className="chart-history-open">{t('openChart')} <ArrowUpRight size={14}/></span>
        </button>)}</div>
        {history && history.total > history.limit && <div className="chart-history-pagination"><button disabled={history.offset === 0} onClick={() => setHistoryOffset(Math.max(0, historyOffset - history.limit))}>{t('previous')}</button><span>{history.offset + 1}–{Math.min(history.offset + history.limit, history.total)} / {history.total}</span><button disabled={history.offset + history.limit >= history.total} onClick={() => setHistoryOffset(historyOffset + history.limit)}>{t('next')}</button></div>}
      </>}
    </section>}
    {!profilesLoading && !profilesError && profiles.length === 0 && <ChartEmptyState language={language} noProfiles onManageProfiles={onManageProfiles}/>}
    {selectedProfile && !hasRequiredBirthData && <div className="chart-alert" role="status">{t('missingBirthData')} <button className="text-button" onClick={onManageProfiles}>{t('manageProfiles')}</button></div>}
    {chartError && <ChartErrorState language={language} message={chartError.message} unavailable={isUnavailable} onRetry={!canRetryChartRequest || !hasRequiredBirthData || calculating ? undefined : () => void calculate()}/>}
    {chartLoading && <ChartLoadingState language={language} saved/>}
    {!chartLoading && !chartError && !chart && profiles.length > 0 && <ChartEmptyState language={language}/>}
    {result && chart && <div className="chart-result" key={`${system}-${division}-${chart.chart_id}`}>
      <div className="chart-result-meta"><span>{selectedProfile?.display_name}</span><span>{chart.calculated_at ? new Date(chart.calculated_at).toLocaleString(language === 'ta' ? 'ta-IN' : 'en', { dateStyle: 'medium', timeStyle: 'short' }) : ''}</span><button className="icon-btn" aria-label={language === 'ta' ? 'ஜாதகத்தை மீண்டும் ஏற்று' : 'Reload saved chart'} onClick={() => void openHistory({ id: chart.chart_id, profile_id: chart.profile_id, profile_name: selectedProfile?.display_name ?? '', system: chart.calculation_system, division: division, status: chart.status, created_at: chart.calculated_at, configuration: chart.configuration, unavailable_reason: null })}><RefreshCw size={15}/></button></div>
      {system === 'vedic' && result.calculation_system === 'vedic' ? <><VedicChartView data={result} division={division} language={language}/>{division === 'D1' && result.division === 'D1' && result.calculation_mode !== 'limited_date_only' && <VedicDignitySection analysis={dignity} loading={dignityLoading} error={dignityError} language={language}/>}</> : system === 'western' && result.calculation_system === 'western' ? <WesternChartView data={result} language={language}/> : <div className="chart-alert error" role="alert">{t('systemError')}</div>}
    </div>}
  </section>;
}
