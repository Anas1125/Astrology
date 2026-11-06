import { useEffect, useRef, useState } from 'react';
import type { MouseEvent } from 'react';
import { Compass, ImagePlus, LoaderCircle, MapPin, Trash2, Upload } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { analyzeVastuFloorPlan } from '../auth/api';
import type { VastuAnalysis, VastuRoomInput } from '../auth/api';
import './vastu.css';

type Language = 'en' | 'ta';
type NorthSide = 'top' | 'right' | 'bottom' | 'left';
type RoomType = VastuRoomInput['room_type'];
type MarkedRoom = VastuRoomInput & { id: string };
type BoundaryPoint = { x: number; y: number };

const COPY = {
  en: {
    title: 'Vastu floor-plan review', intro: 'Upload a floor plan, tell AstroAI which edge is north, then mark the centre of each room.',
    uploadTitle: '1. Upload your floor plan', upload: 'Choose floor-plan image', uploadHint: 'PNG, JPG or WebP · up to 10 MB', replace: 'Change image', northTitle: '2. Confirm north', north: 'Which edge of this image points north?', top: 'Top edge', right: 'Right edge', bottom: 'Bottom edge', left: 'Left edge',
    boundaryTitle: '3. Mark the building boundary', boundaryIntro: 'Click the four outer corners of the house clockwise, starting at the top-left corner. This excludes margins, compass panels and labels.', markBoundary: 'Mark building boundary', redrawBoundary: 'Redraw boundary', resetBoundary: 'Reset boundary', boundaryDone: 'Four corners selected. Room markers will be mapped inside this outline.', boundaryProgress: 'Boundary corners', boundaryRequired: 'Mark all four outer corners of the building before marking rooms or reviewing.',
    roomTitle: '4. Mark rooms', roomType: 'Room to mark', clickHint: 'Choose a room type, then click near the centre of that room inside the building outline.',
    kitchen: 'Kitchen', master_bedroom: 'Master bedroom', bedroom: 'Bedroom', prayer_room: 'Prayer room', bathroom: 'Bathroom / toilet', living_room: 'Living room', study_room: 'Study room', dining_room: 'Dining room', other: 'Other room',
    marked: 'Marked rooms', noRooms: 'No rooms marked yet.', remove: 'Remove', analyze: 'Review floor plan', analyzing: 'Reviewing…', results: 'Vastu observations',
    preferred: 'Common traditional preference', alternative: 'Alternative mentioned in some traditions', review: 'Outside common preferred zone', varies: 'Guidance varies', not_assessed: 'Not assessed in this version',
    imageRequired: 'Upload a floor-plan image first.', roomRequired: 'Mark at least one room on the image.', error: 'Could not review this floor plan.',
    limitations: 'Assisted review only: AstroAI does not automatically recognise room names or walls. You place the markers and confirm north. Vastu is traditional guidance, not scientific certainty. This is not a building, structural, fire-safety or code inspection.',
    clear: 'Clear plan', northCompass: 'North', method: 'How this review works',
  },
  ta: {
    title: 'வாஸ்து தரைத்தள ஆய்வு', intro: 'தரைத்தளப் படத்தைப் பதிவேற்றி, வடக்கு இருக்கும் விளிம்பைத் தேர்ந்தெடுத்து, ஒவ்வொரு அறையின் மையத்தையும் குறிக்கவும்.',
    uploadTitle: '1. தரைத்தளப் படத்தைப் பதிவேற்றவும்', upload: 'தரைத்தளப் படத்தைத் தேர்ந்தெடுக்கவும்', uploadHint: 'PNG, JPG அல்லது WebP · அதிகபட்சம் 10 MB', replace: 'படத்தை மாற்றவும்', northTitle: '2. வடக்குத் திசையை உறுதிப்படுத்தவும்', north: 'இந்தப் படத்தின் எந்த விளிம்பு வடக்கைக் குறிக்கிறது?', top: 'மேல் விளிம்பு', right: 'வலது விளிம்பு', bottom: 'கீழ் விளிம்பு', left: 'இடது விளிம்பு',
    boundaryTitle: '3. கட்டிடத்தின் வெளிப்புற எல்லையைக் குறிக்கவும்', boundaryIntro: 'வீட்டின் நான்கு வெளிப்புற மூலைகளையும் படத்தில் மேல்-இடது மூலையிலிருந்து தொடங்கி கடிகாரத் திசையில் சொடுக்கவும். இதனால் படத்தின் ஓரம், திசைகாட்டி மற்றும் எழுத்துகள் கணக்கில் வராது.', markBoundary: 'கட்டிட எல்லையைக் குறிக்கவும்', redrawBoundary: 'எல்லையை மீண்டும் குறிக்கவும்', resetBoundary: 'எல்லையை மீட்டமை', boundaryDone: 'நான்கு மூலைகளும் குறிக்கப்பட்டன. அறைக் குறியீடுகள் இந்த எல்லைக்குள் கணக்கிடப்படும்.', boundaryProgress: 'எல்லை மூலைகள்', boundaryRequired: 'அறைகளைக் குறிக்கவும் ஆய்வு செய்யவும் முன் கட்டிடத்தின் நான்கு வெளிப்புற மூலைகளையும் குறிக்கவும்.',
    roomTitle: '4. அறைகளைக் குறிக்கவும்', roomType: 'குறிக்க வேண்டிய அறை', clickHint: 'அறை வகையைத் தேர்ந்தெடுத்து, கட்டிட எல்லைக்குள் அந்த அறையின் மையத்தைச் சொடுக்கவும்.',
    kitchen: 'சமையலறை', master_bedroom: 'முதன்மை படுக்கையறை', bedroom: 'படுக்கையறை', prayer_room: 'பூஜை அறை', bathroom: 'குளியலறை / கழிப்பறை', living_room: 'வரவேற்பறை', study_room: 'படிப்பு அறை', dining_room: 'உணவருந்தும் அறை', other: 'மற்ற அறை',
    marked: 'குறிக்கப்பட்ட அறைகள்', noRooms: 'இன்னும் அறைகள் குறிக்கப்படவில்லை.', remove: 'நீக்கு', analyze: 'தரைத்தளத்தை ஆய்வு செய்', analyzing: 'ஆய்வு செய்கிறது…', results: 'வாஸ்து குறிப்புகள்',
    preferred: 'பொதுவாகக் குறிப்பிடப்படும் பாரம்பரிய விருப்பம்', alternative: 'சில மரபுகளில் மாற்றாகக் குறிப்பிடப்படுகிறது', review: 'பொதுவான விருப்பத் திசைக்கு வெளியே', varies: 'வழிகாட்டுதல் மாறுபடும்', not_assessed: 'இந்தப் பதிப்பில் மதிப்பிடப்படவில்லை',
    imageRequired: 'முதலில் தரைத்தளப் படத்தைப் பதிவேற்றவும்.', roomRequired: 'படத்தில் குறைந்தது ஒரு அறையையாவது குறிக்கவும்.', error: 'இந்தத் தரைத்தளத்தை ஆய்வு செய்ய முடியவில்லை.',
    limitations: 'வழிகாட்டப்பட்ட ஆய்வு மட்டுமே: அறைப் பெயர்களையோ சுவர்களையோ AstroAI தானாக அடையாளம் காணாது. அறைக் குறியீடுகளை நீங்களே இடவும்; வடக்குத் திசையையும் உறுதிப்படுத்தவும். வாஸ்து பாரம்பரிய வழிகாட்டுதல் மட்டுமே; அறிவியல் உறுதி அல்ல. இது கட்டிடம், கட்டமைப்பு, தீ பாதுகாப்பு அல்லது விதிமுறை ஆய்வு அல்ல.',
    clear: 'படத்தை நீக்கு', northCompass: 'வடக்கு', method: 'இந்த ஆய்வு எவ்வாறு செயல்படுகிறது',
  },
} as const;

const ROOM_TYPES: RoomType[] = ['kitchen', 'master_bedroom', 'bedroom', 'prayer_room', 'bathroom', 'living_room', 'study_room', 'dining_room', 'other'];
const NORTH_SIDES: NorthSide[] = ['top', 'right', 'bottom', 'left'];
const PREVIEW_URLS = new Set<string>();

export default function VastuPage({ language }: { language: Language }) {
  const { token } = useAuth();
  const t = COPY[language];
  const fileInput = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState('');
  const [imageRatio, setImageRatio] = useState('4 / 3');
  const [northSide, setNorthSide] = useState<NorthSide>('top');
  const [boundary, setBoundary] = useState<BoundaryPoint[]>([]);
  const [boundaryMode, setBoundaryMode] = useState(false);
  const [roomType, setRoomType] = useState<RoomType>('kitchen');
  const [rooms, setRooms] = useState<MarkedRoom[]>([]);
  const [result, setResult] = useState<VastuAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => () => {
    PREVIEW_URLS.forEach(url => URL.revokeObjectURL(url));
    PREVIEW_URLS.clear();
  }, []);

  function clearPlan() {
    if (preview) {
      URL.revokeObjectURL(preview);
      PREVIEW_URLS.delete(preview);
    }
    setFile(null); setPreview(''); setBoundary([]); setBoundaryMode(false); setRooms([]); setResult(null); setError('');
    setImageRatio('4 / 3');
    if (fileInput.current) fileInput.current.value = '';
  }

  function chooseImage(next: File | undefined) {
    setError(''); setResult(null);
    if (!next) return;
    const allowed = new Set(['image/png', 'image/jpeg', 'image/webp']);
    if (!allowed.has(next.type)) { setError(language === 'ta' ? 'PNG, JPG அல்லது WebP படத்தைத் தேர்ந்தெடுக்கவும்.' : 'Choose a PNG, JPG or WebP image.'); return; }
    if (next.size > 10 * 1024 * 1024) { setError(language === 'ta' ? 'படம் 10 MB அல்லது அதற்குக் குறைவாக இருக்க வேண்டும்.' : 'Choose an image that is 10 MB or smaller.'); return; }
    if (preview) { URL.revokeObjectURL(preview); PREVIEW_URLS.delete(preview); }
    const url = URL.createObjectURL(next); PREVIEW_URLS.add(url);
    setFile(next); setPreview(url); setBoundary([]); setBoundaryMode(false); setRooms([]); setResult(null);
  }

  function markRoom(event: MouseEvent<HTMLDivElement>) {
    if (!file || loading) return;
    const rect = event.currentTarget.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const x = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
    const y = Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height));
    if (boundaryMode) {
      if (boundary.length >= 4) { setBoundaryMode(false); return; }
      setBoundary(current => [...current, { x, y }]); setResult(null); setError('');
      if (boundary.length === 3) setBoundaryMode(false);
      return;
    }
    if (boundary.length !== 4) { setError(t.boundaryRequired); return; }
    if (rooms.length >= 20) { setError(language === 'ta' ? 'அதிகபட்சம் 20 அறைகளை மட்டுமே குறிக்கலாம்.' : 'You can mark up to 20 rooms.'); return; }
    setRooms(current => [...current, { id: crypto.randomUUID(), room_type: roomType, x, y }]); setResult(null); setError('');
  }

  function beginBoundarySelection() { setBoundary([]); setBoundaryMode(true); setRooms([]); setResult(null); setError(''); }
  function resetBoundary() { setBoundary([]); setBoundaryMode(false); setRooms([]); setResult(null); setError(''); }

  function removeRoom(id: string) {
    setRooms(current => current.filter(room => room.id !== id));
    setResult(null);
  }

  async function reviewPlan() {
    setError(''); setResult(null);
    if (!file) { setError(t.imageRequired); return; }
    if (boundary.length !== 4) { setError(t.boundaryRequired); return; }
    if (!rooms.length) { setError(t.roomRequired); return; }
    if (!token) { setError(language === 'ta' ? 'மீண்டும் உள்நுழையவும்.' : 'Please sign in again.'); return; }
    setLoading(true);
    try {
      const response = await analyzeVastuFloorPlan(token, file, northSide, rooms.map(({ room_type, x, y }) => ({ room_type, x, y })), boundary);
      setResult(response);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t.error);
    } finally {
      setLoading(false);
    }
  }

  const statusLabel = (status: string) => (t as unknown as Record<string, string>)[status] ?? status;
  return <section className="vastu-page">
    <div className="vastu-heading"><div><div className="eyebrow"><span className="live-dot"/> {language === 'ta' ? 'உங்கள் வீடு' : 'YOUR HOME'}</div><h1>{t.title}</h1><p>{t.intro}</p></div></div>
    <div className="vastu-grid">
      <div className="vastu-card">
        <div className="vastu-section-title"><ImagePlus size={18}/><h2>{t.uploadTitle}</h2></div>
        <input ref={fileInput} className="vastu-file-input" type="file" accept="image/png,image/jpeg,image/webp" onChange={event => chooseImage(event.target.files?.[0])}/>
        {!preview ? <button className="vastu-upload-box" type="button" onClick={() => fileInput.current?.click()}><Upload size={24}/><strong>{t.upload}</strong><span>{t.uploadHint}</span></button> : <>
          <div className="vastu-plan-wrap" style={{ aspectRatio: imageRatio }} onClick={markRoom} role="button" tabIndex={0} aria-label={t.clickHint} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { const target = event.currentTarget.getBoundingClientRect(); markRoom({ currentTarget: event.currentTarget, clientX: target.left + target.width / 2, clientY: target.top + target.height / 2 } as MouseEvent<HTMLDivElement>); } }}>
            <img src={preview} alt={language === 'ta' ? 'பதிவேற்றிய தரைத்தளப் படம்' : 'Uploaded floor plan'} onLoad={event => setImageRatio(`${event.currentTarget.naturalWidth} / ${event.currentTarget.naturalHeight}`)}/>
            {boundary.length > 0 && <svg className="vastu-boundary-overlay" viewBox="0 0 100 100" preserveAspectRatio="none"><polygon points={boundary.map(point => `${point.x * 100},${point.y * 100}`).join(' ')} /></svg>}
            {boundary.map((point, index) => <span key={`boundary-${index}`} className="vastu-boundary-pin" style={{ left: `${point.x * 100}%`, top: `${point.y * 100}%` }}><b>{index + 1}</b></span>)}
            {rooms.map((room, index) => <span key={room.id} className="vastu-room-pin" style={{ left: `${room.x * 100}%`, top: `${room.y * 100}%` }} aria-label={`${index + 1}. ${t[room.room_type]}`}><b>{index + 1}</b></span>)}
            <span className="vastu-north-indicator">N</span>
          </div>
          <div className="vastu-image-actions"><span>{file?.name}</span><button type="button" className="text-action" onClick={clearPlan}><Trash2 size={14}/>{t.clear}</button></div>
          <button type="button" className="secondary-btn" onClick={() => fileInput.current?.click()}>{t.replace}</button>
        </>}
      </div>
      <div className="vastu-card">
        <div className="vastu-section-title"><Compass size={18}/><h2>{t.northTitle}</h2></div>
        <label className="vastu-field"><span>{t.north}</span><select value={northSide} onChange={event => { setNorthSide(event.target.value as NorthSide); setResult(null); }}>
          {NORTH_SIDES.map(side => <option key={side} value={side}>{t[side]}</option>)}
        </select></label>
        <div className="vastu-section-title"><MapPin size={18}/><h2>{t.boundaryTitle}</h2></div>
        <p className="vastu-hint">{boundaryMode ? t.boundaryIntro : boundary.length === 4 ? t.boundaryDone : t.boundaryIntro}</p>
        <div className="vastu-boundary-actions"><button type="button" className="secondary-btn" onClick={beginBoundarySelection} disabled={!file || loading}>{boundary.length === 4 ? t.redrawBoundary : t.markBoundary}</button>{boundary.length > 0 && <button type="button" className="text-action" onClick={resetBoundary} disabled={loading}>{t.resetBoundary}</button>}</div>
        <div className="vastu-marked-heading"><strong>{t.boundaryProgress}</strong><span>{boundary.length}/4</span></div>
        <div className="vastu-boundary-progress">{[0,1,2,3].map(index => <span key={index} className={index < boundary.length ? 'complete' : ''}>{index + 1}</span>)}</div>
        <div className="vastu-section-title"><MapPin size={18}/><h2>{t.roomTitle}</h2></div>
        <label className="vastu-field"><span>{t.roomType}</span><select value={roomType} onChange={event => setRoomType(event.target.value as RoomType)} disabled={boundary.length !== 4 || loading}>
          {ROOM_TYPES.map(type => <option key={type} value={type}>{t[type]}</option>)}
        </select></label>
        <p className="vastu-hint">{boundary.length === 4 ? t.clickHint : t.boundaryRequired}</p>
        <div className="vastu-marked-heading"><strong>{t.marked}</strong><span>{rooms.length}/20</span></div>
        {rooms.length === 0 ? <p className="vastu-empty">{t.noRooms}</p> : <ul className="vastu-room-list">{rooms.map((room, index) => <li key={room.id}><span className="vastu-room-index">{index + 1}</span><span>{t[room.room_type]}</span><button type="button" onClick={() => removeRoom(room.id)} aria-label={`${t.remove} ${t[room.room_type]}`}><Trash2 size={14}/></button></li>)}</ul>}
        {error && <div className="vastu-alert error" role="alert">{error}</div>}
        <button type="button" className="primary-btn vastu-submit" onClick={() => void reviewPlan()} disabled={loading || !file || boundary.length !== 4 || !rooms.length}>{loading ? <><LoaderCircle size={16} className="vastu-spin"/>{t.analyzing}</> : <>{t.analyze} <Compass size={16}/></>}</button>
      </div>
    </div>
    {result && <section className="vastu-results" aria-live="polite"><div className="vastu-section-title"><Compass size={18}/><h2>{t.results}</h2></div><p className="vastu-method">{language === 'ta' ? result.method_ta : result.method_en}</p>
      <div className="vastu-result-list">{result.rooms.map(room => <article className="vastu-result-card" key={room.room_number}><div className="vastu-result-head"><div><strong>{language === 'ta' ? room.room_ta : room.room_en}</strong><span>{language === 'ta' ? room.direction_ta : room.direction}</span></div><small className={`vastu-status ${room.status}`}>{statusLabel(room.status)}</small></div><h3>{language === 'ta' ? room.title_ta : room.title_en}</h3><p>{language === 'ta' ? room.detail_ta : room.detail_en}</p></article>)}</div>
      <p className="vastu-caution">{language === 'ta' ? result.caution_ta : result.caution_en}</p>
    </section>}
    <p className="vastu-limitation">{t.limitations}</p>
  </section>;
}
