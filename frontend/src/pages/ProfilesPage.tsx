import { useCallback, useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import type { BirthProfile, BirthProfileInput } from '../auth/api';
import { createBirthProfile, deleteBirthProfile, listBirthProfiles, updateBirthProfile } from '../auth/api';
import { useAuth } from '../auth/AuthContext';
import { ArrowUpRight, CalendarDays, MapPin, Pencil, Plus, Trash2, UserRound } from 'lucide-react';

type Draft = {
  display_name: string; relationship: string; birth_date: string; birth_time: string;
  time_accuracy: string; birthplace: string; country: string; latitude: string;
  longitude: string; timezone: string;
};
const emptyDraft: Draft = { display_name: '', relationship: 'self', birth_date: '', birth_time: '', time_accuracy: 'unknown', birthplace: '', country: '', latitude: '', longitude: '', timezone: '' };
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

  const loadProfiles = useCallback(async () => {
    if (!token) return;
    setLoading(true); setError('');
    try { setProfiles(await listBirthProfiles(token)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : (ta ? 'விவரங்களை ஏற்ற முடியவில்லை.' : 'Could not load birth profiles.')); }
    finally { setLoading(false); }
  }, [token, ta]);

  useEffect(() => { void loadProfiles(); }, [loadProfiles]);

  function setValue<K extends keyof Draft>(key: K, value: Draft[K]) { setDraft(current => ({ ...current, [key]: value })); }
  function startCreate() { setEditingId(null); setDraft(emptyDraft); setFormError(''); setShowForm(true); }
  function startEdit(profile: BirthProfile) {
    setEditingId(profile.id);
    setDraft({ display_name: profile.display_name, relationship: profile.relationship, birth_date: profile.birth_date, birth_time: profile.birth_time?.slice(0, 5) ?? '', time_accuracy: profile.time_accuracy, birthplace: profile.birthplace, country: profile.country ?? '', latitude: profile.latitude?.toString() ?? '', longitude: profile.longitude?.toString() ?? '', timezone: profile.timezone ?? '' });
    setFormError(''); setShowForm(true);
  }
  function cancelForm() { setShowForm(false); setEditingId(null); setDraft(emptyDraft); setFormError(''); }

  function validateDraft(): string | null {
    if (!draft.display_name.trim() || !draft.birthplace.trim() || !draft.birth_date) return ta ? 'பெயர், பிறந்த தேதி மற்றும் பிறந்த இடம் தேவை.' : 'Name, date of birth, and birthplace are required.';
    if (new Date(`${draft.birth_date}T00:00:00`) > new Date(new Date().toDateString())) return ta ? 'பிறந்த தேதி எதிர்காலத்தில் இருக்க முடியாது.' : 'Date of birth cannot be in the future.';
    if (draft.time_accuracy === 'exact' && !draft.birth_time) return ta ? 'துல்லியமான நேரத்தை உள்ளிடவும்.' : 'Enter the exact birth time.';
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
    const payload: BirthProfileInput = { display_name: draft.display_name.trim(), relationship: draft.relationship, birth_date: draft.birth_date, birth_time: draft.time_accuracy === 'unknown' || !draft.birth_time ? null : `${draft.birth_time}:00`, time_accuracy: draft.time_accuracy, birthplace: draft.birthplace.trim(), country: draft.country.trim(), latitude: draft.latitude ? Number(draft.latitude) : null, longitude: draft.longitude ? Number(draft.longitude) : null, timezone: draft.timezone.trim() || null };
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
      <div className="form-title"><div><span className="notice-icon"><UserRound size={17}/></span><h2>{editingId ? (ta ? 'விவரங்களைத் திருத்து' : 'Edit birth profile') : (ta ? 'புதிய பிறப்பு விவரம்' : 'New birth profile')}</h2></div><span>{ta ? 'இட விவரங்களை கைமுறையாக உள்ளிடவும்' : 'Location details are entered manually'}</span></div>
      <div className="profile-fields">
        <label>{ta ? 'காண்பிக்கும் பெயர்' : 'Display name'}<input required maxLength={120} value={draft.display_name} onChange={e => setValue('display_name', e.target.value)} placeholder={ta ? 'பெயர்' : 'e.g. Anas'} /></label>
        <label>{ta ? 'உறவு' : 'Relationship'}<select value={draft.relationship} onChange={e => setValue('relationship', e.target.value)}>{Object.entries(relationshipLabels).map(([value, label]) => <option key={value} value={value}>{ta ? ({self:'நான்',father:'தந்தை',mother:'தாய்',spouse_partner:'துணைவர்',son_daughter:'மகன் / மகள்',brother_sister:'சகோதரர் / சகோதரி',family_member:'குடும்ப உறுப்பினர்',friend:'நண்பர்',other:'மற்றவர்'} as Record<string,string>)[value] : label}</option>)}</select></label>
        <label>{ta ? 'பிறந்த தேதி' : 'Date of birth'}<input type="date" required max={new Date().toISOString().slice(0, 10)} value={draft.birth_date} onChange={e => setValue('birth_date', e.target.value)} /></label>
        <label>{ta ? 'பிறந்த நேர துல்லியம்' : 'Birth time accuracy'}<select value={draft.time_accuracy} onChange={e => setValue('time_accuracy', e.target.value)}><option value="exact">{ta ? 'துல்லியம்' : 'Exact'}</option><option value="approximate">{ta ? 'தோராயம்' : 'Approximate'}</option><option value="unknown">{ta ? 'தெரியாது' : 'Unknown'}</option></select></label>
        {draft.time_accuracy !== 'unknown' && <label>{ta ? 'பிறந்த நேரம்' : 'Birth time'}<input type="time" required={draft.time_accuracy === 'exact'} value={draft.birth_time} onChange={e => setValue('birth_time', e.target.value)} /></label>}
        <label>{ta ? 'பிறந்த இடம்' : 'Birthplace'}<input required maxLength={200} value={draft.birthplace} onChange={e => setValue('birthplace', e.target.value)} placeholder={ta ? 'நகரம் அல்லது இடம்' : 'City or place name'} /></label>
        <label>{ta ? 'நாடு' : 'Country'}<input maxLength={100} value={draft.country} onChange={e => setValue('country', e.target.value)} placeholder={ta ? 'நாடு' : 'Country'} /></label>
        <label>{ta ? 'அட்சரேகை' : 'Latitude'}<input inputMode="decimal" value={draft.latitude} onChange={e => setValue('latitude', e.target.value)} placeholder="e.g. 13.0827" /></label>
        <label>{ta ? 'தீர்க்கரேகை' : 'Longitude'}<input inputMode="decimal" value={draft.longitude} onChange={e => setValue('longitude', e.target.value)} placeholder="e.g. 80.2707" /></label>
        <label className="timezone-field">{ta ? 'IANA நேர மண்டலம்' : 'IANA timezone'}<input value={draft.timezone} onChange={e => setValue('timezone', e.target.value)} placeholder="e.g. Asia/Kolkata" /><small>{ta ? 'தானியங்கி இடத் தேடல் இல்லை; சரியான விவரங்களை நீங்களே உள்ளிடவும்.' : 'No geocoding is connected. Enter the verified location, coordinates and IANA timezone yourself.'}</small></label>
      </div>
      {formError && <p className="auth-error" role="alert">{formError}</p>}
      <div className="form-actions"><button type="button" className="cancel-btn" onClick={cancelForm}>{ta ? 'ரத்து' : 'Cancel'}</button><button type="submit" className="primary-btn" disabled={saving}>{saving ? (ta ? 'சேமிக்கிறது…' : 'Saving…') : (ta ? 'சேமி' : 'Save profile')} <ArrowUpRight size={15}/></button></div>
    </form>}
    {loading ? <div className="profiles-state" role="status">{ta ? 'விவரங்கள் ஏற்றப்படுகின்றன…' : 'Loading birth profiles…'}</div> : error ? null : profiles.length === 0 ? <div className="profiles-empty"><div className="empty-icon"><UserRound size={21}/></div><h2>{ta ? 'இன்னும் பிறப்பு விவரங்கள் இல்லை' : 'No birth profiles yet'}</h2><p>{ta ? 'ஒரு விவரத்தைச் சேர்த்து தொடங்குங்கள்.' : 'Add your first profile to keep birth information organized.'}</p>{!showForm && <button className="secondary-action" onClick={startCreate}><Plus size={15}/>{ta ? 'முதல் விவரத்தைச் சேர்க்க' : 'Add your first profile'}</button>}</div> : <div className="profiles-grid">{profiles.map(profile => <article className="birth-profile-card" key={profile.id}><div className="birth-card-head"><span className="profile-avatar"><UserRound size={17}/></span><div><h2>{profile.display_name}</h2><span>{ta ? ({self:'நான்',father:'தந்தை',mother:'தாய்',spouse_partner:'துணைவர்',son_daughter:'மகன் / மகள்',brother_sister:'சகோதரர் / சகோதரி',family_member:'குடும்ப உறுப்பினர்',friend:'நண்பர்',other:'மற்றவர்'} as Record<string,string>)[profile.relationship] : (relationshipLabels[profile.relationship] ?? profile.relationship)}</span></div><div className="profile-card-actions"><button aria-label={`Edit ${profile.display_name}`} onClick={() => startEdit(profile)}><Pencil size={15}/></button><button aria-label={`Delete ${profile.display_name}`} disabled={deletingId === profile.id} onClick={() => void removeProfile(profile)}><Trash2 size={15}/></button></div></div><div className="profile-detail"><CalendarDays size={15}/><span>{new Date(`${profile.birth_date}T00:00:00`).toLocaleDateString(ta ? 'ta-IN' : 'en', { dateStyle: 'long' })}{profile.birth_time ? ` · ${profile.birth_time.slice(0, 5)}` : ''}</span></div><div className="profile-detail"><MapPin size={15}/><span>{[profile.birthplace, profile.country].filter(Boolean).join(', ')}</span></div><div className="profile-meta">{profile.latitude != null && profile.longitude != null ? `${profile.latitude}, ${profile.longitude}` : (ta ? 'இட ஆயத்தொலைவு சேர்க்கப்படவில்லை' : 'Coordinates not provided')}<span>{profile.timezone || (ta ? 'நேர மண்டலம் இல்லை' : 'Timezone not provided')}</span></div></article>)}</div>}
  </section>;
}
