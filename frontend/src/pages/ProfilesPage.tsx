import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import type { BirthProfile, BirthProfileInput, LocationSuggestion } from '../auth/api';
import { ApiError, createBirthProfile, deleteBirthProfile, listBirthProfiles, searchBirthplaces, updateBirthProfile } from '../auth/api';
import { useAuth } from '../auth/AuthContext';
import { ArrowUpRight, CalendarDays, MapPin, Pencil, Plus, Trash2, UserRound } from 'lucide-react';
import { to12HourParts, toBackendBirthTime } from './birthTime';

type Draft = {
  display_name: string; relationship: string; birth_date: string;
  time_accuracy: string; birthplace: string; country: string; latitude: string;
  longitude: string; timezone: string;
};
type TimeDraft = { hour: string; minute: string; meridiem: 'AM' | 'PM' };
const emptyTime: TimeDraft = { hour: '', minute: '', meridiem: 'AM' };
const emptyDraft: Draft = { display_name: '', relationship: 'self', birth_date: '', time_accuracy: 'unknown', birthplace: '', country: '', latitude: '', longitude: '', timezone: '' };
const relationshipLabels: Record<string, string> = {
  self: 'Self', father: 'Father', mother: 'Mother', spouse_partner: 'Spouse / partner',
  son_daughter: 'Son / daughter', brother_sister: 'Brother / sister', family_member: 'Family member', friend: 'Friend', other: 'Other',
};

export default function ProfilesPage({ language }: { language: 'en' | 'ta' }) {
  const { token } = useAuth();
  const ta = language === 'ta';
  const [profiles, setProfiles] = useState<BirthProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>(emptyDraft);
  const [saving, setSaving] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [formError, setFormError] = useState('');
  const [timeDraft, setTimeDraft] = useState<TimeDraft>(emptyTime);
  const [placeQuery, setPlaceQuery] = useState('');
  const [placeSuggestions, setPlaceSuggestions] = useState<LocationSuggestion[]>([]);
  const [placeSearchState, setPlaceSearchState] = useState<'idle' | 'loading' | 'results' | 'empty' | 'error'>('idle');
  const [placeSearchError, setPlaceSearchError] = useState('');

  const loadProfiles = useCallback(async () => {
    if (!token) return;
    setLoading(true); setError('');
    try { setProfiles(await listBirthProfiles(token)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : (ta ? 'விவரங்களை ஏற்ற முடியவில்லை.' : 'Could not load birth profiles.')); }
    finally { setLoading(false); }
  }, [token, ta]);

  useEffect(() => { void loadProfiles(); }, [loadProfiles]);

  function setValue<K extends keyof Draft>(key: K, value: Draft[K]) { setDraft(current => ({ ...current, [key]: value })); }
  function startCreate() { setEditingId(null); setDraft(emptyDraft); setTimeDraft(emptyTime); setPlaceQuery(''); setFormError(''); setShowForm(true); }
  function startEdit(profile: BirthProfile) {
    setEditingId(profile.id);
    setDraft({ display_name: profile.display_name, relationship: profile.relationship, birth_date: profile.birth_date, time_accuracy: profile.time_accuracy, birthplace: profile.birthplace, country: profile.country ?? '', latitude: profile.latitude?.toString() ?? '', longitude: profile.longitude?.toString() ?? '', timezone: profile.timezone ?? '' });
    setTimeDraft(to12HourParts(profile.birth_time)); setPlaceQuery('');
    setFormError(''); setShowForm(true);
  }
  function cancelForm() { setShowForm(false); setEditingId(null); setDraft(emptyDraft); setTimeDraft(emptyTime); setPlaceQuery(''); setPlaceSuggestions([]); setFormError(''); }

  useEffect(() => {
    const query = placeQuery.trim();
    if (!showForm || query.length < 3 || !token) { setPlaceSuggestions([]); setPlaceSearchState('idle'); setPlaceSearchError(''); return; }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setPlaceSearchState('loading'); setPlaceSearchError('');
      void searchBirthplaces(token, query, language, controller.signal).then(items => {
        setPlaceSuggestions(items); setPlaceSearchState(items.length ? 'results' : 'empty');
      }).catch(reason => {
        if (controller.signal.aborted) return;
        setPlaceSuggestions([]); setPlaceSearchState('error');
        setPlaceSearchError(reason instanceof ApiError && reason.status === 503
          ? (ta ? 'இடத் தேடல் சேவையகம் அமைக்கப்படவில்லை. விவரங்களை கைமுறையாக உள்ளிடலாம்.' : 'Place search is not configured on this server. You can enter the location manually.')
          : (ta ? 'இடங்களைத் தேட முடியவில்லை. இணைப்பைச் சரிபார்க்கவும் அல்லது கைமுறையாக உள்ளிடவும்.' : 'Could not search places. Check your connection or enter the location manually.'));
      });
    }, 350);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [language, placeQuery, showForm, ta, token]);

  function selectPlace(place: LocationSuggestion) {
    setDraft(current => ({ ...current, birthplace: place.city, country: place.country, latitude: String(place.latitude), longitude: String(place.longitude), timezone: place.timezone ?? '' }));
    setPlaceQuery(''); setPlaceSuggestions([]); setPlaceSearchState('idle'); setPlaceSearchError('');
  }

  function validateDraft(): string | null {
    if (!draft.display_name.trim() || !draft.birthplace.trim() || !draft.birth_date) return ta ? 'பெயர், பிறந்த தேதி மற்றும் பிறந்த இடம் தேவை.' : 'Name, date of birth, and birthplace are required.';
    if (!draft.country.trim() || !draft.latitude.trim() || !draft.longitude.trim()) return ta ? 'தேடல் பட்டியலில் இருந்து பிறந்த இடத்தைத் தேர்ந்தெடுக்கவும்.' : 'Please select your birthplace from the location suggestions.';
    if (new Date(`${draft.birth_date}T00:00:00`) > new Date(new Date().toDateString())) return ta ? 'பிறந்த தேதி எதிர்காலத்தில் இருக்க முடியாது.' : 'Date of birth cannot be in the future.';
    if (draft.time_accuracy === 'exact' && !toBackendBirthTime(timeDraft)) return ta ? 'சரியான மணி, நிமிடம் மற்றும் AM/PM தேர்ந்தெடுக்கவும்.' : 'Choose a valid hour, minute and AM/PM for the exact birth time.';
    const hasLat = draft.latitude.trim() !== '', hasLon = draft.longitude.trim() !== '';
    if (hasLat !== hasLon) return ta ? 'அட்சரேகை மற்றும் தீர்க்கரேகை இரண்டையும் உள்ளிடவும்.' : 'Enter both latitude and longitude.';
    if (hasLat && (!Number.isFinite(Number(draft.latitude)) || Number(draft.latitude) < -90 || Number(draft.latitude) > 90)) return ta ? 'அட்சரேகை -90 முதல் 90 வரை இருக்க வேண்டும்.' : 'Latitude must be between -90 and 90.';
    if (hasLon && (!Number.isFinite(Number(draft.longitude)) || Number(draft.longitude) < -180 || Number(draft.longitude) > 180)) return ta ? 'தீர்க்கரேகை -180 முதல் 180 வரை இருக்க வேண்டும்.' : 'Longitude must be between -180 and 180.';
    if (draft.timezone.trim()) {
      try { new Intl.DateTimeFormat('en', { timeZone: draft.timezone.trim() }).format(); }
      catch { return ta ? 'சரியான IANA நேர மண்டலத்தை உள்ளிடவும்.' : 'Enter a valid IANA timezone, for example Asia/Kolkata.'; }
    }
    return null;
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setNotice('');
    const validation = validateDraft();
    if (validation) { setFormError(validation); return; }
    if (!token) { setFormError(ta ? 'அமர்வு காலாவதியானது. மீண்டும் உள்நுழையவும்.' : 'Your session expired. Please log in again.'); return; }
    setSaving(true); setFormError('');
    const payload: BirthProfileInput = { display_name: draft.display_name.trim(), relationship: draft.relationship, birth_date: draft.birth_date, birth_time: draft.time_accuracy === 'unknown' ? null : toBackendBirthTime(timeDraft), time_accuracy: draft.time_accuracy, birthplace: draft.birthplace.trim(), country: draft.country.trim(), latitude: draft.latitude ? Number(draft.latitude) : null, longitude: draft.longitude ? Number(draft.longitude) : null, timezone: draft.timezone.trim() || null };
    try {
      if (editingId) await updateBirthProfile(token, editingId, payload); else await createBirthProfile(token, payload);
      await loadProfiles(); setNotice(editingId ? (ta ? 'விவரங்கள் புதுப்பிக்கப்பட்டன.' : 'Birth profile updated.') : (ta ? 'பிறப்பு விவரம் சேர்க்கப்பட்டது.' : 'Birth profile created.')); cancelForm();
    } catch (reason) { setFormError(reason instanceof Error ? reason.message : (ta ? 'சேமிக்க முடியவில்லை.' : 'Could not save the birth profile.')); }
    finally { setSaving(false); }
  }

  async function removeProfile(profile: BirthProfile) {
    const confirmed = window.confirm(ta ? `${profile.display_name} விவரத்தை நீக்கவா?` : `Delete the birth profile for ${profile.display_name}?`);
    if (!confirmed || !token) return;
    setDeletingId(profile.id); setError(''); setNotice('');
    try { await deleteBirthProfile(token, profile.id); setProfiles(current => current.filter(item => item.id !== profile.id)); setNotice(ta ? 'பிறப்பு விவரம் நீக்கப்பட்டது.' : 'Birth profile deleted.'); }
    catch (reason) { setError(reason instanceof Error ? reason.message : (ta ? 'நீக்க முடியவில்லை.' : 'Could not delete the birth profile.')); }
    finally { setDeletingId(null); }
  }

  return <section className="profiles-page">
    <div className="profiles-heading"><div><div className="eyebrow"><span className="live-dot"/> {ta ? 'உங்கள் பகுதி' : 'YOUR SPACE'}</div><h1>{ta ? 'பிறப்பு விவரங்கள்' : 'Birth profiles'}</h1><p>{ta ? 'உங்களுக்கும் குடும்பத்தினருக்கும் தனித்தனி விவரங்களை பாதுகாப்பாக வைத்திருங்கள்.' : 'Keep birth details for you and your family together in one private place.'}</p></div><button className="primary-btn" onClick={startCreate}><Plus size={16}/>{ta ? 'சுயவிவரம் சேர்க்க' : 'Add profile'}</button></div>
    {notice && <div className="profile-notice" role="status">{notice}</div>}
    {error && <div className="profile-error" role="alert"><span>{error}</span><button onClick={() => void loadProfiles()}>{ta ? 'மீண்டும் முயற்சி' : 'Retry'}</button></div>}
    {showForm && <form className="birth-profile-form" onSubmit={submit}>
      <div className="form-title"><div><span className="notice-icon"><UserRound size={17}/></span><h2>{editingId ? (ta ? 'விவரங்களைத் திருத்து' : 'Edit birth profile') : (ta ? 'புதிய பிறப்பு விவரம்' : 'New birth profile')}</h2></div><span>{ta ? 'இடத்தைத் தேடித் தேர்வு செய்யவும். மற்ற விவரங்கள் தானாக நிரப்பப்படும்.' : 'Search and select a place. Location details are filled in automatically.'}</span></div>
      <div className="profile-fields">
        <label>{ta ? 'காண்பிக்கும் பெயர்' : 'Display name'}<input required maxLength={120} value={draft.display_name} onChange={e => setValue('display_name', e.target.value)} placeholder={ta ? 'பெயர்' : 'e.g. John'} /></label>
        <label>{ta ? 'உறவு' : 'Relationship'}<select value={draft.relationship} onChange={e => setValue('relationship', e.target.value)}>{Object.entries(relationshipLabels).map(([value, label]) => <option key={value} value={value}>{ta ? ({self:'நான்',father:'தந்தை',mother:'தாய்',spouse_partner:'துணைவர்',son_daughter:'மகன் / மகள்',brother_sister:'சகோதரர் / சகோதரி',family_member:'குடும்ப உறுப்பினர்',friend:'நண்பர்',other:'மற்றவர்'} as Record<string,string>)[value] : label}</option>)}</select></label>
        <label>{ta ? 'பிறந்த தேதி' : 'Date of birth'}<input type="date" required max={new Date().toISOString().slice(0, 10)} value={draft.birth_date} onChange={e => setValue('birth_date', e.target.value)} /></label>
        <label>{ta ? 'பிறந்த நேர துல்லியம்' : 'Birth time accuracy'}<select value={draft.time_accuracy} onChange={e => setValue('time_accuracy', e.target.value)}><option value="exact">{ta ? 'துல்லியம்' : 'Exact'}</option><option value="approximate">{ta ? 'தோராயம்' : 'Approximate'}</option><option value="unknown">{ta ? 'தெரியாது' : 'Unknown'}</option></select></label>
        {draft.time_accuracy !== 'unknown' && <fieldset className="birth-time-field"><legend>{ta ? 'பிறந்த நேரம்' : 'Birth time'}{draft.time_accuracy === 'exact' ? ' *' : ''}</legend><div className="birth-time-selects"><label><span className="sr-only">{ta ? 'மணி' : 'Hour'}</span><select aria-label={ta ? 'மணி' : 'Hour'} required={draft.time_accuracy === 'exact'} value={timeDraft.hour} onChange={e => setTimeDraft(current => ({ ...current, hour: e.target.value }))}><option value="">HH</option>{Array.from({ length: 12 }, (_, i) => String(i + 1).padStart(2, '0')).map(hour => <option key={hour} value={hour}>{hour}</option>)}</select></label><span>:</span><label><span className="sr-only">{ta ? 'நிமிடம்' : 'Minute'}</span><select aria-label={ta ? 'நிமிடம்' : 'Minute'} required={draft.time_accuracy === 'exact'} value={timeDraft.minute} onChange={e => setTimeDraft(current => ({ ...current, minute: e.target.value }))}><option value="">MM</option>{Array.from({ length: 60 }, (_, i) => String(i).padStart(2, '0')).map(minute => <option key={minute} value={minute}>{minute}</option>)}</select></label><label><span className="sr-only">AM/PM</span><select aria-label="AM/PM" value={timeDraft.meridiem} onChange={e => setTimeDraft(current => ({ ...current, meridiem: e.target.value as TimeDraft['meridiem'] }))}><option value="AM">AM</option><option value="PM">PM</option></select></label></div></fieldset>}
        <label className="birthplace-field">{ta ? 'பிறந்த இடம்' : 'Birthplace'}<input required maxLength={200} autoComplete="off" role="combobox" aria-expanded={placeSearchState === 'results'} aria-controls="birthplace-suggestions" value={draft.birthplace} onChange={e => { const value = e.target.value; if (value !== draft.birthplace) setDraft(current => ({ ...current, birthplace: value, country: '', latitude: '', longitude: '', timezone: '' })); setPlaceQuery(value); setPlaceSuggestions([]); setPlaceSearchState('idle'); setPlaceSearchError(''); }} placeholder={ta ? 'நகரம் அல்லது இடத்தைத் தேடவும்' : 'Search for a city or place'} />{placeSearchState === 'loading' && <small role="status">{ta ? 'இடங்கள் தேடப்படுகின்றன…' : 'Searching places…'}</small>}{placeSearchState === 'empty' && <small role="status">{ta ? 'பொருந்தும் இடங்கள் இல்லை. தேடலை மாற்றவும் அல்லது கைமுறையாக உள்ளிடவும்.' : 'No matching places. Refine the search or enter the location manually.'}</small>}{placeSearchState === 'error' && <small role="alert">{placeSearchError}</small>}{placeSearchState === 'results' && <div id="birthplace-suggestions" className="birthplace-suggestions" role="listbox" aria-label={ta ? 'இடத் தேர்வுகள்' : 'Place suggestions'}>{placeSuggestions.map(place => <button type="button" role="option" aria-selected="false" key={place.id} onClick={() => selectPlace(place)}><strong>{place.city}</strong><span>{[place.region, place.country].filter(Boolean).join(', ')}</span></button>)}</div>}</label>
      </div>
      {formError && <p className="auth-error" role="alert">{formError}</p>}
      <div className="form-actions"><button type="button" className="cancel-btn" onClick={cancelForm}>{ta ? 'ரத்து' : 'Cancel'}</button><button type="submit" className="primary-btn" disabled={saving}>{saving ? (ta ? 'சேமிக்கிறது…' : 'Saving…') : (ta ? 'சேமி' : 'Save profile')} <ArrowUpRight size={15}/></button></div>
    </form>}
    {loading ? <div className="profiles-state" role="status">{ta ? 'விவரங்கள் ஏற்றப்படுகின்றன…' : 'Loading birth profiles…'}</div> : error ? null : profiles.length === 0 ? <div className="profiles-empty"><div className="empty-icon"><UserRound size={21}/></div><h2>{ta ? 'இன்னும் பிறப்பு விவரங்கள் இல்லை' : 'No birth profiles yet'}</h2><p>{ta ? 'ஒரு விவரத்தைச் சேர்த்து தொடங்குங்கள்.' : 'Add your first profile to keep birth information organized.'}</p>{!showForm && <button className="secondary-action" onClick={startCreate}><Plus size={15}/>{ta ? 'முதல் விவரத்தைச் சேர்க்க' : 'Add your first profile'}</button>}</div> : <div className="profiles-grid">{profiles.map(profile => <article className="birth-profile-card" key={profile.id}><div className="birth-card-head"><span className="profile-avatar"><UserRound size={17}/></span><div><h2>{profile.display_name}</h2><span>{ta ? ({self:'நான்',father:'தந்தை',mother:'தாய்',spouse_partner:'துணைவர்',son_daughter:'மகன் / மகள்',brother_sister:'சகோதரர் / சகோதரி',family_member:'குடும்ப உறுப்பினர்',friend:'நண்பர்',other:'மற்றவர்'} as Record<string,string>)[profile.relationship] : (relationshipLabels[profile.relationship] ?? profile.relationship)}</span></div><div className="profile-card-actions"><button aria-label={`Edit ${profile.display_name}`} onClick={() => startEdit(profile)}><Pencil size={15}/></button><button aria-label={`Delete ${profile.display_name}`} disabled={deletingId === profile.id} onClick={() => void removeProfile(profile)}><Trash2 size={15}/></button></div></div><div className="profile-detail"><CalendarDays size={15}/><span>{new Date(`${profile.birth_date}T00:00:00`).toLocaleDateString(ta ? 'ta-IN' : 'en', { dateStyle: 'long' })}{profile.birth_time ? ` · ${profile.birth_time.slice(0, 5)}` : ''}</span></div><div className="profile-detail"><MapPin size={15}/><span>{profile.birthplace}</span></div>
    <div className="profile-meta">
      {profile.latitude != null && profile.longitude != null
        ? (ta ? 'இட விவரங்கள் சேமிக்கப்பட்டுள்ளன' : 'Location details saved')
        : (ta ? 'இட ஆயத்தொலைவு சேர்க்கப்படவில்லை' : 'Coordinates not provided')}
    </div>
    </article>)}</div>}
    <p className="geocoder-attribution">{ta ? 'இடத் தேடல் ஆதாரம்: ' : 'Place search attribution: '}<a href="https://www.geoapify.com/" target="_blank" rel="noreferrer">Geoapify</a> · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors</a></p>
  </section>;
}
