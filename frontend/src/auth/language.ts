import { useEffect, useState } from 'react';

const KEY = 'astroai_language';
const EVENT = 'astroai:language-changed';

function storedLanguage(): 'en' | 'ta' {
  return typeof window !== 'undefined' && window.localStorage.getItem(KEY) === 'ta' ? 'ta' : 'en';
}

export function setAstroLanguage(language: 'en' | 'ta') {
  if (typeof window === 'undefined') return;
  window.localStorage.setItem(KEY, language);
  window.dispatchEvent(new Event(EVENT));
}

export function useAstroLanguage(): ['en' | 'ta', (language: 'en' | 'ta') => void] {
  const [language, setLanguageState] = useState<'en' | 'ta'>(storedLanguage);
  useEffect(() => {
    const sync = () => setLanguageState(storedLanguage());
    window.addEventListener(EVENT, sync);
    return () => window.removeEventListener(EVENT, sync);
  }, []);
  const updateLanguage = (nextLanguage: 'en' | 'ta') => {
    setAstroLanguage(nextLanguage);
    // Update this component synchronously as well as notifying other mounted pages.
    setLanguageState(nextLanguage);
  };
  return [language, updateLanguage];
}
