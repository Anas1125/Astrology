import { useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { CalendarDays, MapPin, Sunrise, Sunset } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { ApiError, calculateDailyPanchang, listBirthProfiles, searchBirthplaces } from '../auth/api';
import type { BirthProfile, LocationSuggestion, PanchangResult } from '../auth/api';
import './panchang.css';

type Language = 'en' | 'ta';
export const panchangText = {
  en: {
    title: 'Daily Panchang', intro: 'Choose a date and search for a location. Day elements are evaluated at that location’s local sunrise.',
    saved: 'Use a saved birth profile location', manual: 'Search location', city: 'Location', date: 'Local date', latitude: 'Latitude', longitude: 'Longitude', timezone: 'IANA timezone',
    calculate: 'Calculate Panchang', calculating: 'Calculating…', missing: 'Search for a place and choose one of the verified suggestions.', searching: 'Searching places…', noPlaces: 'No matching places found. Try a nearby city or district.', searchHint: 'Type at least 3 characters, then select a suggested place.', placeSearchUnavailable: 'Place search is unavailable right now. Please try again later.', placeSelected: 'Location selected',
    error: 'Panchang could not be calculated.', tithi: 'Tithi', vara: 'Vara', nakshatra: 'Nakshatra', yoga: 'Yoga', karana: 'Karana', sunrise: 'Sunrise', sunset: 'Sunset',
    atSunrise: 'Day elements at local sunrise', source: 'Calculation convention and source', method: 'Swiss Ephemeris with Lahiri sidereal longitudes. Sunrise/sunset follow the Swiss Ephemeris Hindu rising convention: solar centre at the horizon, no refraction, geocentric position, and solar ecliptic latitude ignored. Tithi, Nakshatra, Yoga, and Karana use the documented angular divisions; Vara is the local weekday. This convention differs from the Indian IMD Rashtriya Panchang upper-limb apparent sunrise convention. Daytime intervals use weekday-indexed eighths for Rahu Kalam, Yamagandam and Gulika Kalam; Abhijit is the eighth of fifteen equal daylight divisions. These are convention-based time windows, not auspiciousness advice; regional rules can differ.',
    daytimeWindows: 'Daytime windows', rahu: 'Rahu Kalam', yama: 'Yamagandam', gulika: 'Gulika Kalam', abhijit: 'Abhijit Muhurta', transitions: 'Next element transitions', calculated: 'Calculated',
    runtime: 'Public calculations are currently disabled pending licensing review. No values are shown until the server confirms that its verified runtime is available.', idle: 'No Panchang result yet. Choose a date and location, then calculate to retrieve the values from the server.', profile: 'Saved profile location', choose: 'Choose a profile', signIn: 'Log in again to continue.',
  },
  ta: {
    title: 'தினசரி பஞ்சாங்கம்', intro: 'தேதியையும் இடத்தையும் தேர்ந்தெடுக்கவும். அன்றைய கூறுகள் அந்த இடத்தின் உள்ளூர் சூரிய உதயத்தில் கணக்கிடப்படும்.',
    saved: 'சேமித்த பிறப்பு விவர இடத்தைப் பயன்படுத்து', manual: 'இடத்தைத் தேடு', city: 'இடம்', date: 'உள்ளூர் தேதி', latitude: 'அட்சரேகை', longitude: 'தீர்க்கரேகை', timezone: 'IANA நேரமண்டலம்',
    calculate: 'பஞ்சாங்கம் கணக்கிடு', calculating: 'கணக்கிடப்படுகிறது…', missing: 'இடத்தைத் தேடி, பரிந்துரைகளில் ஒன்றைத் தேர்ந்தெடுக்கவும்.', searching: 'இடங்கள் தேடப்படுகின்றன…', noPlaces: 'பொருத்தமான இடம் கிடைக்கவில்லை. அருகிலுள்ள நகரம் அல்லது மாவட்டத்தை முயற்சிக்கவும்.', searchHint: 'குறைந்தது 3 எழுத்துகளைத் தட்டச்சு செய்து, பரிந்துரைக்கப்படும் இடத்தைத் தேர்ந்தெடுக்கவும்.', placeSearchUnavailable: 'இடத் தேடல் தற்போது கிடைக்கவில்லை. சிறிது நேரம் கழித்து முயற்சிக்கவும்.', placeSelected: 'இடம் தேர்ந்தெடுக்கப்பட்டது',
    error: 'பஞ்சாங்கத்தை கணக்கிட முடியவில்லை.', tithi: 'திதி', vara: 'வாரம்', nakshatra: 'நட்சத்திரம்', yoga: 'யோகம்', karana: 'கரணம்', sunrise: 'சூரிய உதயம்', sunset: 'சூரிய அஸ்தமனம்',
    atSunrise: 'உள்ளூர் சூரிய உதயத்திலுள்ள அன்றைய கூறுகள்', source: 'கணக்கீட்டு முறை மற்றும் மூலம்', method: 'லஹிரி நிரயன நீளங்களுடன் Swiss Ephemeris பயன்படுத்தப்படுகிறது. Swiss Ephemeris இந்து உதய முறையின்படி சூரிய மையம் விளிம்பில், வளிமண்டல விலகல் இன்றி, புவிமைய நிலையில் கணக்கிடப்படுகிறது; சூரிய கிராந்திவட்ட அகலமும் புறக்கணிக்கப்படுகிறது. திதி, நட்சத்திரம், யோகம், கரணம் ஆகியவை குறிப்பிடப்பட்ட கோணப் பிரிவுகளால் கணக்கிடப்படுகின்றன; வாரம் உள்ளூர் கிழமையைக் குறிக்கும். இந்த முறை இந்திய IMD ராஷ்ட்ரிய பஞ்சாங்கத்தின் மேல்விளிம்பு, வளிமண்டல விலகல் கொண்ட உதய முறையிலிருந்து மாறுபடும். ராகு காலம், யமகண்டம், குளிகை ஆகியவை கிழமையின்படி பகலை எட்டு சம பாகங்களாகப் பிரிக்கின்றன; அபிஜித் பகலின் பதினைந்து சம முகூர்த்தங்களில் எட்டாவது. இவை நேர இடைவெளிகள் மட்டுமே; சுப/அசுப அறிவுரை அல்ல, பிராந்திய வழக்கங்கள் மாறலாம்.',
    daytimeWindows: 'பகல் நேர இடைவெளிகள்', rahu: 'ராகு காலம்', yama: 'யமகண்டம்', gulika: 'குளிகை காலம்', abhijit: 'அபிஜித் முகூர்த்தம்', transitions: 'அடுத்த அங்க மாற்றங்கள்', calculated: 'கணக்கிடப்பட்டது',
    runtime: 'உரிம மதிப்பாய்வு நிலுவையில் இருப்பதால் பொது கணக்கீடுகள் தற்போது முடக்கப்பட்டுள்ளன. சரிபார்க்கப்பட்ட சேவையக இயந்திரம் கிடைக்கும் வரை மதிப்புகள் காட்டப்படாது.', idle: 'பஞ்சாங்க முடிவு இன்னும் இல்லை. தேதியையும் இடத்தையும் தேர்ந்தெடுத்து, பஞ்சாங்கத்தைக் கணக்கிடவும்.', profile: 'சேமித்த விவரத்தின் இடம்', choose: 'விவரத்தைத் தேர்ந்தெடுக்கவும்', signIn: 'தொடர மீண்டும் உள்நுழையவும்.',
  },
} as const;
const tamilNames: Record<string, string> = {
  Sunday:'ஞாயிறு',Monday:'திங்கள்',Tuesday:'செவ்வாய்',Wednesday:'புதன்',Thursday:'வியாழன்',Friday:'வெள்ளி',Saturday:'சனி',Shukla:'சுக்ல பக்ஷம்',Krishna:'கிருஷ்ண பக்ஷம்',
  Pratipada:'பிரதமை',Dvitiya:'துதியை',Tritiya:'திருதியை',Chaturthi:'சதுர்த்தி',Panchami:'பஞ்சமி',Shashthi:'சஷ்டி',Saptami:'சப்தமி',Ashtami:'அஷ்டமி',Navami:'நவமி',Dashami:'தசமி',Ekadashi:'ஏகாதசி',Dwadashi:'துவாதசி',Trayodashi:'திரயோதசி',Chaturdashi:'சதுர்த்தசி',Purnima:'பௌர்ணமி',Amavasya:'அமாவாசை',
  Ashwini:'அசுவினி',Bharani:'பரணி',Krittika:'கார்த்திகை',Rohini:'ரோகிணி',Mrigashirsha:'மிருகசீரிடம்',Ardra:'திருவாதிரை',Punarvasu:'புனர்பூசம்',Pushya:'பூசம்',Ashlesha:'ஆயில்யம்',Magha:'மகம்','Purva Phalguni':'பூரம்','Uttara Phalguni':'உத்திரம்',Hasta:'ஹஸ்தம்',Chitra:'சித்திரை',Swati:'சுவாதி',Vishakha:'விசாகம்',Anuradha:'அனுஷம்',Jyeshtha:'கேட்டை',Mula:'மூலம்','Purva Ashadha':'பூராடம்','Uttara Ashadha':'உத்திராடம்',Shravana:'திருவோணம்',Dhanishta:'அவிட்டம்',Shatabhisha:'சதயம்','Purva Bhadrapada':'பூரட்டாதி','Uttara Bhadrapada':'உத்திரட்டாதி',Revati:'ரேவதி',
  Vishkambha:'விஷ்கம்பம்',Priti:'ப்ரீதி',Ayushman:'ஆயுஷ்மான்',Saubhagya:'சௌபாக்யம்',Shobhana:'சோபனம்',Atiganda:'அதிகண்டம்',Sukarma:'சுகர்மா',Dhriti:'திருதி',Shula:'சூலம்',Ganda:'கண்டம்',Vriddhi:'விருத்தி',Dhruva:'துருவம்',Vyaghata:'வியாகாதம்',Harshana:'ஹர்ஷணம்',Vajra:'வஜ்ரம்',Siddhi:'சித்தி',Vyatipata:'வ்யதீபாதம்',Variyana:'வரீயான்',Parigha:'பரிகம்',Shiva:'சிவம்',Siddha:'சித்தம்',Sadhya:'சாத்யம்',Shubha:'சுபம்',Brahma:'பிரம்மம்',Indra:'இந்திரம்',Vaidhriti:'வைதிருதி',
  Kimstughna:'கிம்ஸ்துக்னம்',Bava:'பவம்',Balava:'பாலவம்',Kaulava:'கௌலவம்',Taitila:'தைதுலம்',Garaja:'கரஜை',Vanija:'வணிஜை',Vishti:'விஷ்டி',Shakuni:'சகுனி',Chatushpada:'சதுஷ்பாதம்',Naga:'நாகம்',
};
function localizedName(value: string, language: Language) { return language === 'ta' ? tamilNames[value] ?? value : value; }

function localToday() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
}

export default function PanchangPage({ language }: { language: Language }) {
  const { token } = useAuth();
  const t = panchangText[language];
  const [profiles, setProfiles] = useState<BirthProfile[]>([]);
  const [profileChoice, setProfileChoice] = useState('');
  const [location, setLocation] = useState('');
  const [latitude, setLatitude] = useState('');
  const [longitude, setLongitude] = useState('');
  const [timezone, setTimezone] = useState('');
  // Coordinates and timezone remain internal; users choose a verified place.
  const [placeQuery, setPlaceQuery] = useState('');
  const [placeSuggestions, setPlaceSuggestions] = useState<LocationSuggestion[]>([]);
  const [placeSearchState, setPlaceSearchState] = useState<'idle' | 'loading' | 'results' | 'empty' | 'error'>('idle');
  const [placeSearchError, setPlaceSearchError] = useState('');
  const [placeSelected, setPlaceSelected] = useState(false);
  const [localDate, setLocalDate] = useState(localToday);
  const [result, setResult] = useState<PanchangResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [profilesError, setProfilesError] = useState('');

  useEffect(() => {
    if (!token) return;
    let active = true;
    void listBirthProfiles(token).then(items => { if (active) setProfiles(items); })
      .catch(err => { if (active) setProfilesError(err instanceof Error ? err.message : t.error); });
    return () => { active = false; };
  }, [token, t.error]);

  // PANCHANG_LOCATION_SEARCH_V1: reuse the authenticated birthplace lookup used by Birth Profiles.
  useEffect(() => {
    const query = location.trim();
    if (!token || placeSelected || query.length < 3) {
      setPlaceSuggestions([]);
      setPlaceSearchState('idle');
      setPlaceSearchError('');
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setPlaceSearchState('loading');
      setPlaceSearchError('');
      void searchBirthplaces(token, query, language, controller.signal).then(items => {
        if (controller.signal.aborted) return;
        setPlaceSuggestions(items);
        setPlaceSearchState(items.length ? 'results' : 'empty');
      }).catch(reason => {
        if (controller.signal.aborted) return;
        setPlaceSuggestions([]);
        setPlaceSearchState('error');
        setPlaceSearchError(reason instanceof ApiError && reason.status === 503
          ? t.placeSearchUnavailable
          : (reason instanceof Error ? reason.message : t.placeSearchUnavailable));
      });
    }, 350);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [language, location, placeSelected, t.placeSearchUnavailable, token]);

  const selectedProfile = useMemo(() => profiles.find(item => item.id === profileChoice), [profiles, profileChoice]);
  function chooseProfile(value: string) {
    setProfileChoice(value);
    setPlaceSuggestions([]);
    setPlaceSearchState('idle');
    setPlaceSearchError('');
    const profile = profiles.find(item => item.id === value);
    if (!profile) {
      setLocation(''); setLatitude(''); setLongitude(''); setTimezone(''); setPlaceSelected(false); setResult(null);
      return;
    }
    setLocation(profile.birthplace);
    setLatitude(profile.latitude == null ? '' : String(profile.latitude));
    setLongitude(profile.longitude == null ? '' : String(profile.longitude));
    setTimezone(profile.timezone ?? '');
    setPlaceSelected(profile.latitude != null && profile.longitude != null && Boolean(profile.timezone));
    setResult(null);
  }

  function selectPlace(place: LocationSuggestion) {
    setLocation(`${place.city}, ${place.country}`);
    setLatitude(String(place.latitude));
    setLongitude(String(place.longitude));
    setTimezone(place.timezone ?? '');
    setProfileChoice('');
    setPlaceSelected(Boolean(place.timezone));
    setPlaceSuggestions([]);
    setPlaceSearchState('idle');
    setPlaceSearchError('');
    setResult(null);
  }
  async function calculate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token || !location.trim() || !placeSelected || !timezone || !localDate || latitude === '' || longitude === '') return;
    setLoading(true); setError(''); setResult(null);
    try {
      const data = await calculateDailyPanchang(token, {
        local_date: localDate, location_name: location.trim(), latitude: Number(latitude),
        longitude: Number(longitude), timezone,
      });
      setResult(data);
    } catch (reason) {
      const message = reason instanceof ApiError ? reason.message : reason instanceof Error ? reason.message : t.error;
      setError(message);
    } finally { setLoading(false); }
  }
  const formatTime = (value: string) => new Intl.DateTimeFormat(language === 'ta' ? 'ta-IN' : 'en-IN', { hour: 'numeric', minute: '2-digit', timeZone: timezone }).format(new Date(value));

  return <section className="panchang-page">
    <header className="module-heading"><div className="eyebrow"><span className="live-dot"/> ASTROAI · {language === 'ta' ? 'உங்கள் பகுதி' : 'YOUR SPACE'}</div><h1>{t.title}</h1><p>{t.intro}</p></header>
    <form className="panchang-form" onSubmit={event => void calculate(event)}>
      <label><span>{t.saved}</span><select aria-label={t.profile} value={profileChoice} onChange={event => chooseProfile(event.target.value)}><option value="">{t.choose}</option>{profiles.map(item => <option key={item.id} value={item.id}>{item.display_name} · {item.birthplace}</option>)}</select></label>
      <div className="panchang-form-grid">
        <div className="panchang-place-field">
          <label htmlFor="panchang-location"><span>{t.city}</span></label>
          <input id="panchang-location" required maxLength={160} value={location} autoComplete="off" placeholder={language === 'ta' ? 'நகரம் அல்லது ஊரைத் தேடுங்கள்' : 'Search city or town'} onChange={event => { setLocation(event.target.value); setProfileChoice(''); setLatitude(''); setLongitude(''); setTimezone(''); setPlaceSelected(false); setResult(null); }} aria-autocomplete="list" aria-expanded={placeSuggestions.length > 0} aria-controls="panchang-place-suggestions" />
{placeSearchState === 'loading' && <p className="panchang-hint" role="status">{t.searching}</p>}
{placeSearchState === 'results' && <div id="panchang-place-suggestions" className="panchang-place-suggestions" role="listbox" aria-label={t.city}>
            {placeSuggestions.map((place, index) => <button type="button" role="option" aria-selected="false" key={`${place.city}-${place.country}-${index}`} onClick={() => selectPlace(place)}>
              <MapPin size={15}/><span><strong>{place.city}</strong><small>{place.country}{place.timezone ? ` · ${place.timezone}` : ''}</small></span>
            </button>)}
          </div>}
{placeSearchState === 'empty' && <p className="panchang-hint" role="status">{t.noPlaces}</p>}
{placeSearchError && <p className="panchang-error" role="alert">{placeSearchError}</p>}
{placeSelected && <p className="panchang-hint" role="status">{t.placeSelected}: {location}</p>}
{!placeSelected && placeSearchState === 'idle' && <p className="panchang-hint">{t.searchHint}</p>}
        </div>
        <label><span>{t.date}</span><input required type="date" value={localDate} onChange={event => setLocalDate(event.target.value)}/></label>
      </div>
      {profilesError && <p className="panchang-error" role="alert">{profilesError}</p>}
      <p className="panchang-hint">{selectedProfile ? `${t.profile}: ${selectedProfile.display_name}` : t.missing}</p>
      <button className="primary-btn" type="submit" disabled={loading || !token || !location.trim() || !timezone || latitude === '' || longitude === ''}>{loading ? t.calculating : <><CalendarDays size={16}/>{t.calculate}</>}</button>
    </form>
    {error && <div className="panchang-error" role="alert">{error}</div>}
    {!error && !result && <div className="panchang-empty-state" role="note"><p>{t.idle}</p></div>}
    {result && <section className="panchang-result" aria-live="polite">
      <div className="panchang-result-heading"><div><MapPin size={17}/><strong>{result.location_name}</strong><span>{result.local_date}</span></div><small>{t.atSunrise} · {t.calculated} {new Intl.DateTimeFormat(language === 'ta' ? 'ta-IN' : 'en-IN', { dateStyle: 'medium', timeStyle: 'short', timeZone: timezone }).format(new Date(result.calculated_at))}</small></div>
      <div className="panchang-time-grid"><div><Sunrise size={19}/><small>{t.sunrise}</small><strong>{formatTime(result.sunrise)}</strong></div><div><Sunset size={19}/><small>{t.sunset}</small><strong>{formatTime(result.sunset)}</strong></div></div>
      <section className="panchang-window-section" aria-label={t.daytimeWindows}><h2>{t.daytimeWindows}</h2><div className="panchang-window-grid">{([[t.rahu, result.daytime_windows.rahu_kalam], [t.yama, result.daytime_windows.yamagandam], [t.gulika, result.daytime_windows.gulika_kalam], [t.abhijit, result.daytime_windows.abhijit_muhurta]] as const).map(([label, window]) => <div key={label}><small>{label} · {window.part}/{window.parts_in_daylight}</small><strong>{formatTime(window.start)} – {formatTime(window.end)}</strong></div>)}</div></section>
      <section className="panchang-window-section" aria-label={t.transitions}><h2>{t.transitions}</h2><div className="panchang-window-grid">{([[t.tithi, result.transitions.tithi], [t.nakshatra, result.transitions.nakshatra], [t.yoga, result.transitions.yoga], [t.karana, result.transitions.karana]] as const).map(([label, transition]) => <div key={label}><small>{label} · {transition.next_index}</small><strong>{localizedName(transition.next_paksha ? `${transition.next_paksha} ${transition.next_name}` : transition.next_name, language)}</strong><small>{formatTime(transition.at)}</small></div>)}</div></section>
      <div className="panchang-element-grid">{[[t.tithi, `${localizedName(result.tithi.paksha, language)} ${localizedName(result.tithi.name, language)}`], [t.vara, localizedName(result.vara.name, language)], [t.nakshatra, localizedName(result.nakshatra.name, language)], [t.yoga, localizedName(result.yoga.name, language)], [t.karana, localizedName(result.karana.name, language)]].map(([label, value]) => <div key={label}><small>{label}</small><strong>{value}</strong></div>)}</div>
      <details className="panchang-method"><summary>{t.source}</summary><p>{t.method}</p><small>{result.calculation.engine_version} · Swiss Ephemeris {result.calculation.provider_engine_version}</small></details>
    </section>}
  </section>;
}
