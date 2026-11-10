import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { useAstroLanguage } from '../auth/language';
import ProfilesPage from './ProfilesPage';
import ChartsPage from '../astrology/ChartsPage';
import AIChatPage from '../astrology/AIChatPage';
import PanchangPage from '../astrology/PanchangPage';
import HoroscopePage from '../astrology/HoroscopePage';
import CompatibilityPage from '../astrology/CompatibilityPage';
import VastuPage from '../astrology/VastuPage';
import SourceLicenseNotice from '../components/SourceLicenseNotice';
import HoroscopeAdminPage from '../astrology/HoroscopeAdminPage';
import { ArrowUpRight, BookOpen, CalendarDays, ChevronDown, Check, Compass, Globe2, LayoutDashboard, MoonStar, Orbit, Sparkles, Stars, ShieldCheck, UserRound, UsersRound } from 'lucide-react';

type Page = 'overview' | 'profiles' | 'vedic' | 'western' | 'astrologer' | 'panchang' | 'horoscope' | 'compatibility' | 'admin-horoscope' | 'vastu';

export default function App() {
  const { account, logout } = useAuth();
  const navigate = useNavigate();
  const [language, setLanguage] = useAstroLanguage();
  const [page, setPage] = useState<Page>('overview');
  const [languageMenuOpen, setLanguageMenuOpen] = useState(false);
  const languageMenuRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!languageMenuOpen) return;
    const handlePointerDown = (event: PointerEvent) => {
      if (event.target instanceof Node && !languageMenuRef.current?.contains(event.target)) {
        setLanguageMenuOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setLanguageMenuOpen(false);
    };
    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [languageMenuOpen]);
  const tamil = language === 'ta';
  const now = new Date();
  const today = new Intl.DateTimeFormat(tamil ? 'ta-IN' : 'en-US', { month: 'long', day: 'numeric', year: 'numeric' }).format(now);
  const localDate = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
  const labels = tamil ? {
    overview: 'உங்கள் வானம், தெளிவாக ஆராயப்படுகிறது', welcome: 'AstroAI-க்கு வரவேற்கிறோம்', subtitle: 'வேத மற்றும் மேற்கத்திய ஜோதிடத்தை தெளிவுடனும் கவனத்துடனும் ஆராயுங்கள்.', chart: 'ஜாதகக் கட்டம்', chartDesc: 'சேவையகக் கணக்கீடு மற்றும் உரிம அனுமதி கிடைக்கும் போது உங்கள் ஜாதக நிலைகள் இங்கே தோன்றும்.', profiles: 'பிறப்பு விவரங்கள்', horoscope: 'ராசிபலன்', panchang: 'பஞ்சாங்கம்', astrologer: 'ஜோதிட உரையாடல்', explore: 'உங்கள் ஜாதகத்தைப் பாருங்கள்', unavailable: 'சேவையக அமைப்பில் தற்போது கிடைக்கவில்லை', horoscopeUnavailable: 'ஆதாரச் சரிபார்ப்பும் ஆசிரியர் மதிப்பாய்வும் முடிந்த நாளுக்குரிய பலன் உள்ளடக்கம் இன்னும் இல்லை. கணிப்பு உருவாக்கப்படாது.', panchangUnavailable: 'சரிபார்க்கப்பட்ட மற்றும் உரிமம் பெற்ற வானியல் கணக்கீடு தேவை. பொது கணக்கீடுகள் தற்போது முடக்கப்பட்டுள்ளன.', compatibilityUnavailable: 'பொருத்தக் கணக்கீட்டு முறை மற்றும் முடிவுகள் இன்னும் உற்பத்திக்காக அங்கீகரிக்கப்படவில்லை. மதிப்பெண் உருவாக்கப்படாது.', adminHoroscope: 'ராசிபலன் நிர்வாகம்', yourSpace: 'உங்கள் பகுதி', mainNavigation: 'முதன்மை வழிசெலுத்தல்', astrology: 'உங்கள் ஜோதிடம்', systemsDescription: 'ஆராயத் தொடங்க ஒரு மரபைத் தேர்ந்தெடுக்கவும்.', vedic: 'வேத ஜோதிடம்', vedicDesc: 'கணக்கீடு கிடைக்கும் போது உங்கள் கிரக நிலைகள் மற்றும் தசைகளை ஆராயுங்கள்.', western: 'மேற்கத்திய ஜோதிடம்', westernDesc: 'கணக்கீடு கிடைக்கும் போது உங்கள் பிறப்பு ஜாதகம் மற்றும் கோணங்களைப் பாருங்கள்.', chartName: 'ஜாதகக் கட்டம்', janma: 'ஜன்ம குண்டலி', natal: 'பிறப்பு ஜாதகம்', disclaimer: 'AstroAI சேமித்த ஜாதகத் தகவலை வழங்கும்; ஆதாரமுள்ள பாரம்பரிய விளக்கங்கள் இன்னும் மதிப்பாய்வில் உள்ளன. ஜோதிடம் அறிவியல் உறுதி அல்லது தொழில்முறை ஆலோசனை அல்ல.'
  } : {
    overview: 'Your sky, thoughtfully explored', welcome: 'Welcome to AstroAI', subtitle: 'Explore Vedic and Western astrology with clarity, context, and care.', chart: 'Birth chart', chartDesc: 'Chart results appear when server-side calculation and licensing gates permit them.', profiles: 'Birth profiles', horoscope: 'Horoscope', panchang: 'Panchang', astrologer: 'Astrologer chat', explore: 'Explore your chart', unavailable: 'Unavailable under current server settings', horoscopeUnavailable: 'No date-specific horoscope content has passed source and editorial review. No prediction is generated.', panchangUnavailable: 'This needs a verified, licensed astronomy runtime. Public calculations remain disabled.', compatibilityUnavailable: 'Compatibility methods and calculation outputs are not approved for release. No score is generated.', adminHoroscope: 'Horoscope admin', yourSpace: 'YOUR SPACE', mainNavigation: 'Main navigation', astrology: 'Your astrology', systemsDescription: 'Choose a tradition to begin exploring.', vedic: 'Vedic astrology', vedicDesc: 'Explore placements and dashas when verified calculations are enabled.', western: 'Western astrology', westernDesc: 'Explore natal placements and aspects when verified calculations are enabled.', chartName: 'Birth chart', janma: 'Janma Kundli', natal: 'Natal chart', disclaimer: 'AstroAI shares saved chart facts; sourced traditional interpretations are still under review. Astrology is not scientific certainty or professional advice.'
  };
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark"><Stars size={21}/></span><span>astro<span className="gold">ai</span></span></div>
      <div className="workspace-label">{labels.yourSpace}</div>
      <nav aria-label="Main navigation">
        <a href="#overview" className={page === 'overview' ? 'active' : ''} onClick={() => setPage('overview')}><LayoutDashboard size={17}/>{labels.overview}</a><a href="#profiles" className={page === 'profiles' ? 'active' : ''} onClick={() => setPage('profiles')}><UserRound size={17}/>{labels.profiles}</a><a href="#vedic" className={page === 'vedic' || page === 'western' ? 'active' : ''} onClick={() => setPage('vedic')}><Orbit size={17}/>{labels.chart}</a><a href="#astrologer" className={page === 'astrologer' ? 'active' : ''} onClick={() => setPage('astrologer')}><MoonStar size={17}/>{labels.astrologer}</a><a href="#panchang" className={page === 'panchang' ? 'active' : ''} onClick={() => setPage('panchang')}><CalendarDays size={17}/>{labels.panchang}</a><a href="#horoscope" className={page === 'horoscope' ? 'active' : ''} onClick={() => setPage('horoscope')}><BookOpen size={17}/>{labels.horoscope}</a><a href="#compatibility" className={page === 'compatibility' ? 'active' : ''} onClick={() => setPage('compatibility')}><UsersRound size={17}/>{tamil ? 'பொருத்தம்' : 'Compatibility'}</a><a href="#vastu" className={page === 'vastu' ? 'active' : ''} onClick={() => setPage('vastu')}><Compass size={17}/>{tamil ? 'வாஸ்து' : 'Vastu'}</a>
        {account?.role?.toUpperCase() === 'ADMIN' && <a href="#admin-horoscope" className={page === 'admin-horoscope' ? 'active' : ''} onClick={() => setPage('admin-horoscope')}><ShieldCheck size={17}/>{labels.adminHoroscope}</a>}
      </nav>
      <div className="sidebar-bottom"><div className="account"><div className="avatar">{account?.email.charAt(0).toUpperCase()}</div><div><b>{account?.email}</b><small>{account?.role}</small></div><button className="logout-button" onClick={() => { logout(); navigate('/login', { replace: true }); }} aria-label="Log out">Log out</button></div></div>
    </aside>
    <main className="main-content">
      <header className="topbar"><div className="crumb">{labels.yourSpace} <span>/</span> <b>{page === 'astrologer' ? labels.astrologer : page === 'profiles' ? labels.profiles : page === 'vedic' || page === 'western' ? labels.chart : page === 'panchang' ? labels.panchang : page === 'horoscope' ? labels.horoscope : page === 'compatibility' ? (tamil ? 'பொருத்தம்' : 'Compatibility') : page === 'vastu' ? (tamil ? 'வாஸ்து' : 'Vastu') : page === 'admin-horoscope' ? labels.adminHoroscope : labels.overview}</b></div><div className="top-actions"><div className="language-picker" ref={languageMenuRef}>
        <button type="button" className="lang-btn" onClick={() => setLanguageMenuOpen((open) => !open)} aria-haspopup="menu" aria-expanded={languageMenuOpen} aria-label={tamil ? 'மொழியைத் தேர்ந்தெடுக்கவும்' : 'Choose language'}><Globe2 size={16}/>{tamil ? 'தமிழ்' : 'EN'}<ChevronDown size={13}/></button>
        {languageMenuOpen && <div className="language-dropdown" role="menu" aria-label={tamil ? 'மொழி' : 'Language'}>
          <button type="button" role="menuitemradio" aria-checked={!tamil} className={`language-option${!tamil ? ' is-active' : ''}`} onClick={() => { setLanguage('en'); setLanguageMenuOpen(false); }}><span className="language-option-code">EN</span><span className="language-option-label">English</span>{!tamil && <Check size={16} aria-hidden="true"/>}</button>
          <button type="button" role="menuitemradio" aria-checked={tamil} className={`language-option${tamil ? ' is-active' : ''}`} onClick={() => { setLanguage('ta'); setLanguageMenuOpen(false); }}><span className="language-option-code">TA</span><span className="language-option-label">தமிழ்</span>{tamil && <Check size={16} aria-hidden="true"/>}</button>
          <div className="language-coming-soon" aria-disabled="true"><span className="language-option-code">+</span><span>{tamil ? 'மேலும் மொழிகள் விரைவில்' : 'More languages coming soon'}</span></div>
        </div>}
      </div></div></header>
      {page === 'astrologer' ? <AIChatPage language={language}/> : page === 'profiles' ? <ProfilesPage language={language}/> : page === 'vedic' || page === 'western' ? <ChartsPage system={page} language={language} onSystemChange={setPage} onManageProfiles={() => setPage('profiles')}/> : page === 'panchang' ? <PanchangPage language={language}/> : page === 'horoscope' ? <HoroscopePage language={language}/> : page === 'compatibility' ? <CompatibilityPage language={language}/>  : page === 'vastu' ? <VastuPage language={language}/>: page === 'admin-horoscope' ? <HoroscopeAdminPage language={language}/> : <>
      <section className="welcome-row"><div><div className="eyebrow"><span className="live-dot"/> {tamil ? 'உங்கள் தனிப்பட்ட பிரபஞ்சம்' : 'YOUR PERSONAL COSMOS'}</div><h1>{labels.welcome}</h1><p>{labels.subtitle}</p></div><div className="date-chip"><CalendarDays size={15}/><time dateTime={localDate}>{today}</time></div></section>
      <section className="hero-card"><div className="hero-copy"><div className="eyebrow gold-text"><Sparkles size={14}/> {tamil ? 'தனிப்பட்ட பார்வை' : 'A MORE PERSONAL PERSPECTIVE'}</div><h2>{labels.overview}</h2><p>{tamil ? 'உங்கள் பிறப்பு விவரங்கள், ஜாதகக் குறிப்புகள் மற்றும் வழிகாட்டுதலை ஒரே தனிப்பட்ட இடத்தில் காணுங்கள்.' : 'Bring together your birth details, chart insights and thoughtful guidance in one calm, private space.'}</p><button className="primary-btn" onClick={() => setPage('vedic')}>{labels.explore} <ArrowUpRight size={16}/></button></div><div className="orbital-art" aria-hidden="true"><div className="orbit orbit-one"/><div className="orbit orbit-two"/><div className="planet"><Stars size={30}/></div><span className="star s1">✦</span><span className="star s2">✧</span><span className="star s3">·</span></div><div className="hero-glow"/></section>
      <section className="section-heading"><div><h2>{labels.astrology}</h2><p>{labels.systemsDescription}</p></div><span className="muted">2 systems</span></section>
      <section className="system-grid"><button className="system-card system-card-button vedic" onClick={() => setPage('vedic')}><div className="card-icon"><Compass size={20}/></div><div className="card-tag">SIDEREAL · LAHIRI</div><h3>{labels.vedic}</h3><p>{labels.vedicDesc}</p><div className="card-foot"><span>{labels.janma}</span><span className="round-arrow"><ArrowUpRight size={16}/></span></div></button><button className="system-card system-card-button western" onClick={() => setPage('western')}><div className="card-icon"><Orbit size={20}/></div><div className="card-tag">TROPICAL · PLACIDUS</div><h3>{labels.western}</h3><p>{labels.westernDesc}</p><div className="card-foot"><span>{labels.natal}</span><span className="round-arrow"><ArrowUpRight size={16}/></span></div></button><article className="notice-card"><div className="notice-head"><span className="notice-icon"><Sparkles size={17}/></span><span className="notice-label">{tamil ? 'கிடைக்கும் போது' : 'SERVER CONTROLLED'}</span></div><h3>{labels.chartName}</h3><p>{labels.chartDesc}</p><div className="notice-foot"><span className="status-dot"/>{labels.unavailable}</div></article></section>
      <footer>{labels.disclaimer}</footer>
      </>}
      <SourceLicenseNotice />
    </main>
  </div>;
}
