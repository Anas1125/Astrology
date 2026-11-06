import { useCallback, useEffect, useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { BookOpen, Download, FilePlus2, Pencil, RefreshCw, Send, Trash2, Upload, XCircle } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import {
  createAdminHoroscopeDraft,
  deleteAdminHoroscopeContent,
  listAdminHoroscopeContent,
  publishAdminHoroscopeContent,
  unpublishAdminHoroscopeContent,
  updateAdminHoroscopeDraft,
  bulkImportAdminHoroscopeContent,
  bulkPublishAdminHoroscopeContent,
} from '../auth/api';
import type { HoroscopeAdminContent, HoroscopeBulkImportRow } from '../auth/api';
import './horoscope-admin.css';

type Language = 'en' | 'ta';
type System = 'vedic' | 'western';
type Period = 'daily' | 'weekly' | 'monthly';
type Category = 'overview' | 'career' | 'relationships' | 'finance' | 'personal_growth';

const copy = {
  en: {
    title: 'Horoscope content manager', intro: 'Write simple English and Tamil horoscope content, save drafts, and publish it when you are ready. General horoscopes are for reflection and entertainment, not guaranteed predictions.',
    create: 'Create horoscope', editing: 'Edit horoscope', update: 'Save changes', save: 'Save draft', cancel: 'Cancel', refresh: 'Refresh',
    system: 'Tradition', vedic: 'Vedic', western: 'Western', period: 'Period', daily: 'Daily', weekly: 'Weekly', monthly: 'Monthly',
    sign: 'Sign / Rashi', category: 'Topic', overview: 'Overview', career: 'Career', relationships: 'Relationships', finance: 'Finance', personal: 'Personal growth',
    starts: 'Starts on', ends: 'Ends on', english: 'English content', tamil: 'Tamil content',
    list: 'Horoscope library', empty: 'No horoscope entries yet. Create your first one above.', draft: 'Draft', published: 'Published',
    edit: 'Edit', publish: 'Publish', unpublish: 'Unpublish', remove: 'Delete', loading: 'Loading…', saving: 'Saving…',
    savedDraft: 'Bilingual draft saved. It is not visible on the Horoscope page yet.', updated: 'Changes saved. The entry is now a draft; publish it when ready.',
    publishedNotice: 'Horoscope published. It is now available for matching selections.', unpublishedNotice: 'Horoscope unpublished and hidden from users.', deleted: 'Horoscope entry deleted.',
    confirmDelete: 'Delete this English and Tamil horoscope entry?', confirmPublish: 'Publish this English and Tamil horoscope entry?', confirmUnpublish: 'Unpublish this entry and hide it from users?',
    disclaimer: 'Keep the English and Tamil versions aligned. Use original, general astrology-themed writing. Avoid medical, financial or other guaranteed claims. Astrology is a traditional belief system and is not scientifically established.',
    bulkTitle: 'Import many horoscope entries', bulkHelp: 'Upload a CSV with one row per sign and date. English and Tamil are imported together as drafts; nothing is published automatically.', downloadTemplate: 'Download CSV template', chooseCsv: 'Choose CSV file', importing: 'Importing…',
    publishAll: 'Publish all drafts', publishingAll: 'Publishing…',
    confirmPublishAll: 'Publish all {count} draft entries? Every complete English/Tamil pair will become available to users.',
    publishedAll: '{published} entries published; {skipped} incomplete entries skipped.',
    forbidden: 'Administrator access is required for this page.', error: 'Something went wrong. Please try again.',
  },
  ta: {
    title: 'ராசிபலன் உள்ளடக்க நிர்வாகம்', intro: 'ஆங்கிலம் மற்றும் தமிழில் எளிய ராசிபலன் உள்ளடக்கத்தை எழுதிச் சேமித்து, தயாரானதும் வெளியிடுங்கள். இது சிந்தனைக்கும் பொழுதுபோக்கிற்குமான பொதுவான உள்ளடக்கம்; உறுதியான கணிப்பு அல்ல.',
    create: 'ராசிபலன் உருவாக்கு', editing: 'ராசிபலனைத் திருத்து', update: 'மாற்றங்களைச் சேமி', save: 'வரைவாகச் சேமி', cancel: 'ரத்துசெய்', refresh: 'புதுப்பி',
    system: 'ஜோதிட மரபு', vedic: 'வேத', western: 'மேற்கத்திய', period: 'காலம்', daily: 'தினசரி', weekly: 'வாராந்திர', monthly: 'மாதாந்திர',
    sign: 'ராசி', category: 'தலைப்பு', overview: 'பொதுக் கண்ணோட்டம்', career: 'தொழில்', relationships: 'உறவுகள்', finance: 'நிதி', personal: 'தனிப்பட்ட வளர்ச்சி',
    starts: 'தொடக்க தேதி', ends: 'முடிவு தேதி', english: 'ஆங்கில உள்ளடக்கம்', tamil: 'தமிழ் உள்ளடக்கம்',
    list: 'ராசிபலன் நூலகம்', empty: 'இன்னும் உள்ளடக்கம் இல்லை. மேலே முதல் பதிவை உருவாக்குங்கள்.', draft: 'வரைவு', published: 'வெளியிடப்பட்டது',
    edit: 'திருத்து', publish: 'வெளியிடு', unpublish: 'வெளியீட்டை நிறுத்து', remove: 'நீக்கு', loading: 'ஏற்றப்படுகிறது…', saving: 'சேமிக்கப்படுகிறது…',
    savedDraft: 'இருமொழி வரைவு சேமிக்கப்பட்டது. இது இன்னும் ராசிபலன் பக்கத்தில் காட்டப்படாது.', updated: 'மாற்றங்கள் சேமிக்கப்பட்டன. இது மீண்டும் வரைவாக உள்ளது; தயாரானதும் வெளியிடுங்கள்.',
    publishedNotice: 'ராசிபலன் வெளியிடப்பட்டது. பொருந்தும் தேர்வுகளில் இப்போது காட்டப்படும்.', unpublishedNotice: 'வெளியீடு நிறுத்தப்பட்டது; பயனர்களுக்குக் காட்டப்படாது.', deleted: 'ராசிபலன் நீக்கப்பட்டது.',
    confirmDelete: 'இந்த ஆங்கிலம் மற்றும் தமிழ் ராசிபலன் பதிவை நீக்கவா?', confirmPublish: 'இந்த ஆங்கிலம் மற்றும் தமிழ் ராசிபலன் பதிவை வெளியிடவா?', confirmUnpublish: 'இந்தப் பதிவின் வெளியீட்டை நிறுத்தி பயனர்களிடமிருந்து மறைக்கவா?',
    disclaimer: 'ஆங்கிலம் மற்றும் தமிழ் உள்ளடக்கங்கள் ஒரே பொருளைக் கொண்டிருக்க வேண்டும். அசல் பொதுவான ஜோதிட உள்ளடக்கத்தை எழுதுங்கள். மருத்துவம், நிதி அல்லது உறுதியான பலன் குறித்த கூற்றுகளைத் தவிர்க்கவும். ஜோதிடம் பாரம்பரிய நம்பிக்கை முறை; இது அறிவியல் ரீதியாக நிறுவப்படவில்லை.',
    bulkTitle: 'பல ராசிபலன்களை இறக்குமதி செய்', bulkHelp: 'ஒவ்வொரு தேதி மற்றும் ராசிக்கும் ஒரு வரி கொண்ட CSV கோப்பைப் பதிவேற்றுங்கள். ஆங்கிலம் மற்றும் தமிழ் இரண்டும் வரைவாகச் சேமிக்கப்படும்; தானாக வெளியிடப்படாது.', downloadTemplate: 'CSV மாதிரியைப் பதிவிறக்கு', chooseCsv: 'CSV கோப்பைத் தேர்வு செய்', importing: 'இறக்குமதி செய்கிறது…',
    publishAll: 'அனைத்து வரைவுகளையும் வெளியிடு', publishingAll: 'வெளியிடப்படுகிறது…',
    confirmPublishAll: 'அனைத்து {count} வரைவுகளையும் வெளியிடவா? முழுமையான ஆங்கிலம்/தமிழ் இணைகள் பயனர்களுக்குக் கிடைக்கும்.',
    publishedAll: '{published} பதிவுகள் வெளியிடப்பட்டன; முழுமையற்ற {skipped} பதிவுகள் தவிர்க்கப்பட்டன.',
    forbidden: 'இந்தப் பக்கத்திற்கு நிர்வாக அணுகல் தேவை.', error: 'பிழை ஏற்பட்டது. மீண்டும் முயற்சிக்கவும்.',
  },
} as const;

const vedicSigns = ['Mesha','Vrishabha','Mithuna','Karka','Simha','Kanya','Tula','Vrischika','Dhanu','Makara','Kumbha','Meena'];
const westernSigns = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'];

function localToday() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}


const csvHeaders = ['system', 'period', 'sign', 'category', 'starts_on', 'ends_on', 'en_content', 'ta_content'];

function parseCsvRecords(source: string): string[][] {
  const text = source.replace(/^\uFEFF/, '');
  const records: string[][] = [];
  let record: string[] = [];
  let value = '';
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (quoted) {
      if (char === '"') {
        if (text[index + 1] === '"') { value += '"'; index += 1; }
        else quoted = false;
      } else value += char;
      continue;
    }
    if (char === '"' && value.length === 0) quoted = true;
    else if (char === ',') { record.push(value); value = ''; }
    else if (char === '\n' || char === '\r') {
      if (char === '\r' && text[index + 1] === '\n') index += 1;
      record.push(value); value = '';
      if (record.some(cell => cell.trim() !== '')) records.push(record);
      record = [];
    } else value += char;
  }
  if (quoted) throw new Error('CSV contains an unclosed quoted field.');
  record.push(value);
  if (record.some(cell => cell.trim() !== '')) records.push(record);
  return records;
}

function parseHoroscopeCsv(source: string): HoroscopeBulkImportRow[] {
  const records = parseCsvRecords(source);
  if (records.length < 2) throw new Error('The CSV needs a header row and at least one horoscope row.');
  const headers = records[0].map(value => value.trim().toLowerCase());
  const missing = csvHeaders.filter(header => !headers.includes(header));
  if (missing.length) throw new Error(`Missing CSV columns: ${missing.join(', ')}`);
  const column: Record<string, number> = {};
  csvHeaders.forEach(header => { column[header] = headers.indexOf(header); });
  if (records.length - 1 > 5000) throw new Error('A single import can contain at most 5,000 rows.');

  const vedicSigns = ['Mesha','Vrishabha','Mithuna','Karka','Simha','Kanya','Tula','Vrischika','Dhanu','Makara','Kumbha','Meena'];
  const westernSigns = ['Aries','Taurus','Gemini','Cancer','Leo','Virgo','Libra','Scorpio','Sagittarius','Capricorn','Aquarius','Pisces'];
  const periods = ['daily', 'weekly', 'monthly'];
  const categories = ['overview', 'career', 'relationships', 'finance', 'personal_growth'];

  return records.slice(1).map((cells, index) => {
    const line = index + 2;
    const get = (name: string) => (cells[column[name]] ?? '').trim();
    const item = {
      system: get('system').toLowerCase(),
      period: get('period').toLowerCase(),
      sign: get('sign'),
      category: get('category').toLowerCase(),
      starts_on: get('starts_on'),
      ends_on: get('ends_on'),
      en_content: cells[column.en_content] ?? '',
      ta_content: cells[column.ta_content] ?? '',
    };
    const fail = (message: string): never => { throw new Error(`CSV row ${line}: ${message}`); };
    if (item.system !== 'vedic' && item.system !== 'western') fail('system must be vedic or western.');
    if (!periods.includes(item.period)) fail('period must be daily, weekly or monthly.');
    if (!categories.includes(item.category)) fail('category is not recognised.');
    if (!(item.system === 'vedic' ? vedicSigns : westernSigns).includes(item.sign)) fail('sign must match the selected tradition and use its exact sign key.');
    const validDate = (date: string) => {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return false;
      const [year, month, day] = date.split('-').map(Number);
      const parsed = new Date(Date.UTC(year, month - 1, day));
      return parsed.getUTCFullYear() === year && parsed.getUTCMonth() === month - 1 && parsed.getUTCDate() === day;
    };
    if (!validDate(item.starts_on) || !validDate(item.ends_on)) fail('dates must use YYYY-MM-DD.');
    if (item.ends_on < item.starts_on) fail('ends_on cannot be before starts_on.');
    if (item.en_content.trim().length < 10 || item.ta_content.trim().length < 10) fail('English and Tamil content must each contain at least 10 characters.');
    if (item.en_content.length > 12000 || item.ta_content.length > 12000) fail('each language field must be 12,000 characters or fewer.');
    return {
      ...item,
      system: item.system as HoroscopeBulkImportRow['system'],
      period: item.period as HoroscopeBulkImportRow['period'],
      category: item.category as HoroscopeBulkImportRow['category'],
    };
  });
}

function downloadHoroscopeCsvTemplate() {
  const sample = [
    csvHeaders.join(','),
    'vedic,daily,Mesha,overview,2025-01-12,2025-01-12,"Write the English horoscope for this sign and date.","இந்த ராசிக்கான தமிழ் ராசிபலனை இங்கே எழுதுங்கள்."',
  ].join('\r\n');
  const url = URL.createObjectURL(new Blob([sample], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'astroai-horoscope-import-template.csv';
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export default function HoroscopeAdminPage({ language }: { language: Language }) {
  const { token, account } = useAuth();
  const t = copy[language];
  const isAdmin = account?.role?.toUpperCase() === 'ADMIN';
  const [items, setItems] = useState<HoroscopeAdminContent[]>([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [importing, setImporting] = useState(false);
  const [publishingAll, setPublishingAll] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [editing, setEditing] = useState<string | null>(null);
  const [system, setSystem] = useState<System>('vedic');
  const [period, setPeriod] = useState<Period>('daily');
  const [sign, setSign] = useState(vedicSigns[0]);
  const [category, setCategory] = useState<Category>('overview');
  const [startsOn, setStartsOn] = useState(localToday);
  const [endsOn, setEndsOn] = useState(localToday);
  const [enContent, setEnContent] = useState('');
  const [taContent, setTaContent] = useState('');

  const refresh = useCallback(async () => {
    if (!token || !isAdmin) return;
    setLoading(true);
    try {
      const response = await listAdminHoroscopeContent(token);
      setItems(response.items);
      setError('');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t.error);
    } finally {
      setLoading(false);
    }
  }, [token, isAdmin, t.error]);

  useEffect(() => { void refresh(); }, [refresh]);

  const draftCount = items.filter(item => !item.published).length;

  function clearForm() {
    setEditing(null);
    setSystem('vedic'); setPeriod('daily'); setSign(vedicSigns[0]); setCategory('overview');
    setStartsOn(localToday()); setEndsOn(localToday()); setEnContent(''); setTaContent('');
  }

  function editItem(item: HoroscopeAdminContent) {
    setEditing(item.scope_key); setSystem(item.system); setPeriod(item.period); setSign(item.sign); setCategory(item.category);
    setStartsOn(item.starts_on); setEndsOn(item.ends_on); setEnContent(item.en_content); setTaContent(item.ta_content);
    setError(''); setNotice(''); window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  async function saveDraft(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setSaving(true); setError(''); setNotice('');
    try {
      const payload = { starts_on: startsOn, ends_on: endsOn, en_content: enContent, ta_content: taContent };
      if (editing) {
        await updateAdminHoroscopeDraft(token, editing, payload);
        setNotice(t.updated);
      } else {
        await createAdminHoroscopeDraft(token, { ...payload, system, period, sign, category });
        setNotice(t.savedDraft);
      }
      clearForm(); await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t.error);
    } finally { setSaving(false); }
  }



  async function importCsv(event: ChangeEvent<HTMLInputElement>) {
    const input = event.currentTarget;
    const file = input.files?.[0];
    if (!file || !token) return;
    setImporting(true); setError(''); setNotice('');
    try {
      const rows = parseHoroscopeCsv(await file.text());
      const result = await bulkImportAdminHoroscopeContent(token, rows);
      setNotice(language === 'ta'
        ? `${result.created} இருமொழி வரைவுகள் இறக்குமதி செய்யப்பட்டன; ${result.skipped} ஏற்கனவே உள்ள பதிவுகள் தவிர்க்கப்பட்டன. வெளியிடுவதற்கு முன் மதிப்பாய்வு செய்யுங்கள்.`
        : `${result.created} bilingual drafts imported; ${result.skipped} existing or repeated rows skipped. Review them before publishing.`);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t.error);
    } finally {
      setImporting(false);
      input.value = '';
    }
  }


  async function changePublication(item: HoroscopeAdminContent) {
    if (!token) return;
    const confirmMessage = item.published ? t.confirmUnpublish : t.confirmPublish;
    if (!window.confirm(confirmMessage)) return;
    setSaving(true); setError(''); setNotice('');
    try {
      if (item.published) {
        await unpublishAdminHoroscopeContent(token, item.scope_key);
        setNotice(t.unpublishedNotice);
      } else {
        await publishAdminHoroscopeContent(token, item.scope_key);
        setNotice(t.publishedNotice);
      }
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t.error);
    } finally { setSaving(false); }
  }

  async function publishAllDrafts() {
    if (!token || draftCount === 0) return;
    const message = t.confirmPublishAll.replace('{count}', String(draftCount));
    if (!window.confirm(message)) return;
    setPublishingAll(true); setError(''); setNotice('');
    try {
      const result = await bulkPublishAdminHoroscopeContent(token);
      setNotice(t.publishedAll
        .replace('{published}', String(result.published))
        .replace('{skipped}', String(result.skipped)));
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t.error);
    } finally {
      setPublishingAll(false);
    }
  }

  async function deleteItem(item: HoroscopeAdminContent) {
    if (!token || !window.confirm(t.confirmDelete)) return;
    setSaving(true); setError(''); setNotice('');
    try {
      await deleteAdminHoroscopeContent(token, item.scope_key);
      if (editing === item.scope_key) clearForm();
      setNotice(t.deleted); await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t.error);
    } finally { setSaving(false); }
  }

  if (!isAdmin) return <section className="horoscope-admin-page"><div className="horoscope-admin-alert error">{t.forbidden}</div></section>;

  return <section className="horoscope-admin-page">
    <header className="module-heading">
      <div className="eyebrow"><span className="live-dot"/> ASTROAI · ADMIN</div>
      <h1>{t.title}</h1><p>{t.intro}</p>
    </header>
    {error && <div className="horoscope-admin-alert error" role="alert">{error}</div>}
    {notice && <div className="horoscope-admin-alert success" role="status">{notice}</div>}

    <section className="horoscope-admin-import">
      <div>
        <h2>{t.bulkTitle}</h2>
        <p>{t.bulkHelp}</p>
      </div>
      <div className="horoscope-admin-import-actions">
        <button className="secondary-btn" type="button" onClick={downloadHoroscopeCsvTemplate} disabled={saving || importing}>
          <Download size={15}/>{t.downloadTemplate}
        </button>
        <label className="horoscope-admin-file-input">
          <Upload size={15}/>{importing ? t.importing : t.chooseCsv}
          <input type="file" accept=".csv,text/csv" onChange={event => void importCsv(event)} disabled={saving || importing} />
        </label>
      </div>
    </section>

    <form className="horoscope-admin-form" onSubmit={event => void saveDraft(event)}>
      <div className="horoscope-admin-section-title"><FilePlus2 size={18}/><h2>{editing ? t.editing : t.create}</h2></div>
      <div className="horoscope-admin-fields">
        <label>{t.system}<select value={system} onChange={event => { const next = event.target.value as System; setSystem(next); setSign((next === 'vedic' ? vedicSigns : westernSigns)[0]); }} disabled={Boolean(editing)}><option value="vedic">{t.vedic}</option><option value="western">{t.western}</option></select></label>
        <label>{t.period}<select value={period} onChange={event => setPeriod(event.target.value as Period)} disabled={Boolean(editing)}><option value="daily">{t.daily}</option><option value="weekly">{t.weekly}</option><option value="monthly">{t.monthly}</option></select></label>
        <label>{t.sign}<select value={sign} onChange={event => setSign(event.target.value)} disabled={Boolean(editing)}>{(system === 'vedic' ? vedicSigns : westernSigns).map(value => <option key={value} value={value}>{value}</option>)}</select></label>
        <label>{t.category}<select value={category} onChange={event => setCategory(event.target.value as Category)} disabled={Boolean(editing)}><option value="overview">{t.overview}</option><option value="career">{t.career}</option><option value="relationships">{t.relationships}</option><option value="finance">{t.finance}</option><option value="personal_growth">{t.personal}</option></select></label>
        <label>{t.starts}<input type="date" required value={startsOn} onChange={event => setStartsOn(event.target.value)}/></label>
        <label>{t.ends}<input type="date" required min={startsOn} value={endsOn} onChange={event => setEndsOn(event.target.value)}/></label>
      </div>
      <div className="horoscope-admin-language-grid">
        <label>{t.english}<textarea required minLength={10} maxLength={12000} rows={5} value={enContent} onChange={event => setEnContent(event.target.value)}/></label>
        <label>{t.tamil}<textarea required minLength={10} maxLength={12000} rows={5} value={taContent} onChange={event => setTaContent(event.target.value)}/></label>
      </div>
      <p className="horoscope-admin-help">{t.disclaimer}</p>
      <div className="horoscope-admin-actions"><button className="primary-btn" type="submit" disabled={saving}>{saving ? t.saving : editing ? t.update : t.save}</button>{editing && <button type="button" className="secondary-btn" onClick={clearForm} disabled={saving}><XCircle size={15}/>{t.cancel}</button>}</div>
    </form>

    <div className="horoscope-admin-list-heading"><div><h2>{t.list}</h2></div><div className="horoscope-admin-list-actions"><button className="primary-btn" type="button" onClick={() => void publishAllDrafts()} disabled={loading || saving || importing || publishingAll || draftCount === 0}><Send size={15}/>{publishingAll ? t.publishingAll : `${t.publishAll} (${draftCount})`}</button><button className="secondary-btn" type="button" onClick={() => void refresh()} disabled={loading || saving || publishingAll}><RefreshCw size={15}/>{t.refresh}</button></div></div>
    {loading && <p className="horoscope-admin-help">{t.loading}</p>}
    {!loading && items.length === 0 && <div className="horoscope-admin-empty"><BookOpen size={22}/><p>{t.empty}</p></div>}
    <div className="horoscope-admin-list">
      {items.map(item => <article className="horoscope-admin-card" key={item.scope_key}>
        <div className="horoscope-admin-card-head"><div><span className="horoscope-admin-kicker">{item.system} · {item.period} · {item.category}</span><h3>{item.sign}</h3><small>{item.starts_on} — {item.ends_on}</small></div><span className={item.published ? 'horoscope-status approved' : 'horoscope-status'}>{item.published ? t.published : t.draft}</span></div>
        <div className="horoscope-admin-preview"><div><b>EN</b><p>{item.en_content}</p></div><div><b>தமிழ்</b><p>{item.ta_content}</p></div></div>
        <div className="horoscope-admin-actions">
          <button className="secondary-btn" type="button" disabled={saving} onClick={() => editItem(item)}><Pencil size={15}/>{t.edit}</button>
          <button className="secondary-btn" type="button" disabled={saving} onClick={() => void changePublication(item)}><Send size={15}/>{item.published ? t.unpublish : t.publish}</button>
          <button className="secondary-btn danger-btn" type="button" disabled={saving} onClick={() => void deleteItem(item)}><Trash2 size={15}/>{t.remove}</button>
        </div>
      </article>)}
    </div>
  </section>;
}
