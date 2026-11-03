export type AstroLanguage = 'en' | 'ta';

export const astrologyText = {
  en: {
    title: 'Birth chart', system: 'Astrology system', vedic: 'Vedic', western: 'Western', profile: 'Birth profile',
    manageProfiles: 'Manage birth profiles', noProfiles: 'Add a birth profile to begin', noProfilesDescription: 'A chart needs a saved birth date, exact time, IANA timezone and verified coordinates.',
    profileRequired: 'Select a birth profile.', missingBirthData: 'This profile needs a known birth time, IANA timezone, latitude and longitude before a chart can be calculated.',
    houseSystem: 'House system', calculate: 'Calculate chart', calculating: 'Calculating…', loadingProfiles: 'Loading birth profiles…', loadingChart: 'Loading saved chart…',
    unavailableTitle: 'Chart calculation unavailable', unavailableDescription: 'The server did not make chart calculations available. AstroAI will respect that server setting.',
    errorTitle: 'Could not load chart', retry: 'Try again', noChart: 'Choose a profile and calculate a chart to see its placements.',
    division: 'Chart division', d1: 'D1 · Rashi', d9: 'D9 · Navamsa', chartLayout: 'Chart layout', south: 'South Indian', north: 'North Indian',
    ascendant: 'Ascendant', midheaven: 'Midheaven', planets: 'Planet placements', planet: 'Planet', sign: 'Sign', degrees: 'Degrees', house: 'House', motion: 'Motion',
    direct: 'Direct', retrograde: 'Retrograde', nakshatra: 'Nakshatra', pada: 'Pada', lord: 'Lord', aspects: 'Major aspects', noAspects: 'No major aspects fall within the configured orbs.',
    applying: 'Applying', separating: 'Separating', exact: 'Exact', unknown: 'Unknown', mahadasha: 'Vimshottari Mahadasha', antardasha: 'Antardasha',
    savanaNote: 'Periods use the configured 360-day Savana year convention.', start: 'Start', end: 'End', balance: 'Birth balance', systemError: 'Chart system or response did not match this request.',
    plSystem: 'Placidus', wholeSign: 'Whole Sign', equal: 'Equal (Ascendant)',
    history: 'Saved chart history', openChart: 'Open chart', noHistory: 'No saved charts for this profile yet.', historyUnavailable: 'Calculation was unavailable when this chart was requested.', previous: 'Previous', next: 'Next',
    planetsTamil: { Sun: 'சூரியன்', Moon: 'சந்திரன்', Mercury: 'புதன்', Venus: 'சுக்கிரன்', Mars: 'செவ்வாய்', Jupiter: 'குரு', Saturn: 'சனி', Uranus: 'யுரேனஸ்', Neptune: 'நெப்டியூன்', Pluto: 'புளூட்டோ', Rahu: 'ராகு', Ketu: 'கேது' },
    signsTamil: { Aries: 'மேஷம்', Taurus: 'ரிஷபம்', Gemini: 'மிதுனம்', Cancer: 'கடகம்', Leo: 'சிம்மம்', Virgo: 'கன்னி', Libra: 'துலாம்', Scorpio: 'விருச்சிகம்', Sagittarius: 'தனுசு', Capricorn: 'மகரம்', Aquarius: 'கும்பம்', Pisces: 'மீனம்', Mesha: 'மேஷம்', Vrishabha: 'ரிஷபம்', Mithuna: 'மிதுனம்', Karka: 'கடகம்', Simha: 'சிம்மம்', Kanya: 'கன்னி', Tula: 'துலாம்', Vrischika: 'விருச்சிகம்', Dhanu: 'தனுசு', Makara: 'மகரம்', Kumbha: 'கும்பம்', Meena: 'மீனம்' },
    nakshatrasTamil: { Ashwini: 'அசுவினி', Bharani: 'பரணி', Krittika: 'கார்த்திகை', Rohini: 'ரோகிணி', Mrigashirsha: 'மிருகசீரிடம்', Ardra: 'திருவாதிரை', Punarvasu: 'புனர்பூசம்', Pushya: 'பூசம்', Ashlesha: 'ஆயில்யம்', Magha: 'மகம்', 'Purva Phalguni': 'பூரம்', 'Uttara Phalguni': 'உத்திரம்', Hasta: 'அஸ்தம்', Chitra: 'சித்திரை', Swati: 'சுவாதி', Vishakha: 'விசாகம்', Anuradha: 'அனுஷம்', Jyeshtha: 'கேட்டை', Mula: 'மூலம்', 'Purva Ashadha': 'பூராடம்', 'Uttara Ashadha': 'உத்திராடம்', Shravana: 'திருவோணம்', Dhanishta: 'அவிட்டம்', Shatabhisha: 'சதயம்', 'Purva Bhadrapada': 'பூரட்டாதி', 'Uttara Bhadrapada': 'உத்திரட்டாதி', Revati: 'ரேவதி' },
    aspectsTamil: { conjunction: 'சேர்க்கை', sextile: 'அறுபது பாகை', square: 'சதுரம்', trine: 'திரிகோணம்', opposition: 'எதிர் நிலை' },
  },
  ta: {
    title: 'பிறப்பு ஜாதகம்', system: 'ஜோதிட முறை', vedic: 'வேத ஜோதிடம்', western: 'மேற்கத்திய ஜோதிடம்', profile: 'பிறப்பு விவரம்',
    manageProfiles: 'பிறப்பு விவரங்களை நிர்வகிக்க', noProfiles: 'தொடங்க பிறப்பு விவரத்தைச் சேர்க்கவும்', noProfilesDescription: 'ஜாதகக் கணக்கீட்டுக்கு பிறந்த தேதி, துல்லியமான நேரம், IANA நேர மண்டலம் மற்றும் சரிபார்க்கப்பட்ட ஆயத்தொலைவுகள் தேவை.',
    profileRequired: 'பிறப்பு விவரத்தைத் தேர்ந்தெடுக்கவும்.', missingBirthData: 'ஜாதகக் கணக்கீட்டுக்கு தெரிந்த பிறந்த நேரம், IANA நேர மண்டலம், அட்சரேகை மற்றும் தீர்க்கரேகை தேவை.',
    houseSystem: 'பாவ முறை', calculate: 'ஜாதகத்தைக் கணக்கிடு', calculating: 'கணக்கிடுகிறது…', loadingProfiles: 'பிறப்பு விவரங்கள் ஏற்றப்படுகின்றன…', loadingChart: 'சேமித்த ஜாதகம் ஏற்றப்படுகிறது…',
    unavailableTitle: 'ஜாதகக் கணக்கீடு கிடைக்கவில்லை', unavailableDescription: 'சேவையகம் தற்போது கணக்கீட்டை அனுமதிக்கவில்லை. AstroAI சேவையக அமைப்பை மதிக்கும்.',
    errorTitle: 'ஜாதகத்தை ஏற்ற முடியவில்லை', retry: 'மீண்டும் முயற்சி', noChart: 'நிலைகளைக் காண விவரத்தைத் தேர்ந்தெடுத்து ஜாதகத்தைக் கணக்கிடவும்.',
    division: 'ஜாதகப் பிரிவு', d1: 'D1 · ராசி', d9: 'D9 · நவாம்சம்', chartLayout: 'ஜாதக வடிவம்', south: 'தென்னிந்திய முறை', north: 'வடஇந்திய முறை',
    ascendant: 'லக்னம்', midheaven: 'மத்திய உச்சம்', planets: 'கிரக நிலைகள்', planet: 'கிரகம்', sign: 'ராசி', degrees: 'பாகை', house: 'பாவம்', motion: 'இயக்கம்',
    direct: 'நேர்கதி', retrograde: 'வக்கிரம்', nakshatra: 'நட்சத்திரம்', pada: 'பாதம்', lord: 'அதிபதி', aspects: 'முக்கிய பார்வைகள்', noAspects: 'அமைக்கப்பட்ட பாகை வரம்பில் முக்கிய பார்வைகள் இல்லை.',
    applying: 'நெருங்கும்', separating: 'விலகும்', exact: 'துல்லியம்', unknown: 'தெரியாது', mahadasha: 'விம்சோத்தரி மகாதசை', antardasha: 'அந்தர்தசை',
    savanaNote: 'இந்தக் காலங்கள் அமைக்கப்பட்ட 360 நாள் சாவன ஆண்டு முறையைப் பயன்படுத்துகின்றன.', start: 'தொடக்கம்', end: 'முடிவு', balance: 'பிறப்பு இருப்புக் காலம்', systemError: 'கோரிய ஜோதிட முறை அல்லது பதில் பொருந்தவில்லை.',
    plSystem: 'பிளாசிடஸ்', wholeSign: 'முழு ராசி', equal: 'சம பாவம் (லக்னம்)',
    history: 'சேமித்த ஜாதக வரலாறு', openChart: 'ஜாதகத்தைத் திற', noHistory: 'இந்த விவரத்திற்குச் சேமித்த ஜாதகங்கள் இல்லை.', historyUnavailable: 'இந்த ஜாதகக் கோரிக்கையின் போது கணக்கீடு கிடைக்கவில்லை.', previous: 'முந்தைய', next: 'அடுத்து',
    planetsTamil: { Sun: 'சூரியன்', Moon: 'சந்திரன்', Mercury: 'புதன்', Venus: 'சுக்கிரன்', Mars: 'செவ்வாய்', Jupiter: 'குரு', Saturn: 'சனி', Uranus: 'யுரேனஸ்', Neptune: 'நெப்டியூன்', Pluto: 'புளூட்டோ', Rahu: 'ராகு', Ketu: 'கேது' },
    signsTamil: { Aries: 'மேஷம்', Taurus: 'ரிஷபம்', Gemini: 'மிதுனம்', Cancer: 'கடகம்', Leo: 'சிம்மம்', Virgo: 'கன்னி', Libra: 'துலாம்', Scorpio: 'விருச்சிகம்', Sagittarius: 'தனுசு', Capricorn: 'மகரம்', Aquarius: 'கும்பம்', Pisces: 'மீனம்', Mesha: 'மேஷம்', Vrishabha: 'ரிஷபம்', Mithuna: 'மிதுனம்', Karka: 'கடகம்', Simha: 'சிம்மம்', Kanya: 'கன்னி', Tula: 'துலாம்', Vrischika: 'விருச்சிகம்', Dhanu: 'தனுசு', Makara: 'மகரம்', Kumbha: 'கும்பம்', Meena: 'மீனம்' },
    nakshatrasTamil: { Ashwini: 'அசுவினி', Bharani: 'பரணி', Krittika: 'கார்த்திகை', Rohini: 'ரோகிணி', Mrigashirsha: 'மிருகசீரிடம்', Ardra: 'திருவாதிரை', Punarvasu: 'புனர்பூசம்', Pushya: 'பூசம்', Ashlesha: 'ஆயில்யம்', Magha: 'மகம்', 'Purva Phalguni': 'பூரம்', 'Uttara Phalguni': 'உத்திரம்', Hasta: 'அஸ்தம்', Chitra: 'சித்திரை', Swati: 'சுவாதி', Vishakha: 'விசாகம்', Anuradha: 'அனுஷம்', Jyeshtha: 'கேட்டை', Mula: 'மூலம்', 'Purva Ashadha': 'பூராடம்', 'Uttara Ashadha': 'உத்திராடம்', Shravana: 'திருவோணம்', Dhanishta: 'அவிட்டம்', Shatabhisha: 'சதயம்', 'Purva Bhadrapada': 'பூரட்டாதி', 'Uttara Bhadrapada': 'உத்திரட்டாதி', Revati: 'ரேவதி' },
    aspectsTamil: { conjunction: 'சேர்க்கை', sextile: 'அறுபது பாகை', square: 'சதுரம்', trine: 'திரிகோணம்', opposition: 'எதிர் நிலை' },
  },
} as const;

export function astroLabel(language: AstroLanguage, key: keyof typeof astrologyText.en): string {
  return astrologyText[language][key] as string;
}

export function localizePlanet(language: AstroLanguage, name: string): string {
  return language === 'ta' ? astrologyText.ta.planetsTamil[name as keyof typeof astrologyText.ta.planetsTamil] ?? name : name;
}

export function localizeSign(language: AstroLanguage, name: string): string {
  return language === 'ta' ? astrologyText.ta.signsTamil[name as keyof typeof astrologyText.ta.signsTamil] ?? name : name;
}

export function localizeNakshatra(language: AstroLanguage, name: string): string {
  return language === 'ta' ? astrologyText.ta.nakshatrasTamil[name as keyof typeof astrologyText.ta.nakshatrasTamil] ?? name : name;
}

export function localizeAspect(language: AstroLanguage, name: string): string {
  return language === 'ta' ? astrologyText.ta.aspectsTamil[name as keyof typeof astrologyText.ta.aspectsTamil] ?? name : name;
}
