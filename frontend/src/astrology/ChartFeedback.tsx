import { CalendarDays, Sparkles } from 'lucide-react';
import { astroLabel } from './i18n';
import type { AstroLanguage } from './i18n';

export function ChartLoadingState({ language, saved = false }: { language: AstroLanguage; saved?: boolean }) {
  return <div className="chart-loading" role="status"><span className="loading-spinner"/>{astroLabel(language, saved ? 'loadingChart' : 'calculating')}</div>;
}

export function ChartEmptyState({ language, onManageProfiles, noProfiles = false }: { language: AstroLanguage; onManageProfiles?: () => void; noProfiles?: boolean }) {
  if (noProfiles) return <div className="chart-empty"><CalendarDays size={25}/><h2>{astroLabel(language, 'noProfiles')}</h2><p>{astroLabel(language, 'noProfilesDescription')}</p>{onManageProfiles && <button className="secondary-action" onClick={onManageProfiles}>{astroLabel(language, 'manageProfiles')}</button>}</div>;
  return <div className="chart-empty chart-empty-compact"><Sparkles size={23}/><p>{astroLabel(language, 'noChart')}</p></div>;
}

export function ChartErrorState({ language, message, unavailable = false, onRetry }: { language: AstroLanguage; message: string; unavailable?: boolean; onRetry?: () => void }) {
  return <div className={`chart-alert ${unavailable ? 'unavailable' : 'error'}`} role="alert"><div><b>{astroLabel(language, unavailable ? 'unavailableTitle' : 'errorTitle')}</b><p>{unavailable ? astroLabel(language, 'unavailableDescription') : message}</p>{unavailable && !/disabled intentionally|licensing approval/i.test(message) && <small>{message}</small>}</div>{onRetry && !unavailable && <button onClick={onRetry}>{astroLabel(language, 'retry')}</button>}</div>;
}
