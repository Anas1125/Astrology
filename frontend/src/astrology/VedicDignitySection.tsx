import type { VedicDignityAnalysis, VedicDignityPlanet } from '../auth/api';
import type { AstroLanguage } from './i18n';
import { localizePlanet, localizeSign } from './i18n';

const DIGNITY_LABELS = {
  en: { exalted: 'Exalted sign', debilitated: 'Debilitated sign', moolatrikona: 'Moolatrikona', own_sign: 'Own sign', friend_sign: 'Friendly sign', neutral_sign: 'Neutral sign', enemy_sign: 'Enemy sign', self: 'Self', friend: 'Friend', neutral: 'Neutral', enemy: 'Enemy' },
  ta: { exalted: 'உச்ச ராசி', debilitated: 'நீச ராசி', moolatrikona: 'மூலத்திரிகோணம்', own_sign: 'சொந்த ராசி', friend_sign: 'நட்பு ராசி', neutral_sign: 'சம ராசி', enemy_sign: 'பகை ராசி', self: 'தன் கிரகம்', friend: 'நட்பு', neutral: 'சமம்', enemy: 'பகை' },
} as const;
const DIGNITY_EXPLANATIONS = {
  en: { exalted: 'Within the exaltation range defined by this provisional ruleset.', debilitated: 'In the opposite sign designated as debilitation by this ruleset.', moolatrikona: 'Within the listed Moolatrikona sign and degree interval.', own_sign: 'In a sign assigned to this planet as its own.', friend_sign: 'The sign lord is classified as a natural friend in this ruleset.', neutral_sign: 'The sign lord is classified as neutral in this ruleset.', enemy_sign: 'The sign lord is classified as a natural enemy in this ruleset.' },
  ta: { exalted: 'இந்தத் தற்காலிக விதிமுறையில் வரையறுக்கப்பட்ட உச்ச வரம்புக்குள் உள்ளது.', debilitated: 'இந்த விதிமுறையில் நீசமாகக் குறிப்பிடப்பட்ட எதிர் ராசியில் உள்ளது.', moolatrikona: 'பட்டியலிடப்பட்ட மூலத்திரிகோண ராசி மற்றும் பாகை வரம்புக்குள் உள்ளது.', own_sign: 'இந்தக் கிரகத்தின் சொந்த ராசியாகக் குறிப்பிடப்பட்ட ராசியில் உள்ளது.', friend_sign: 'இந்த விதிமுறையில் ராசி அதிபர் இயற்கை நண்பராக வகைப்படுத்தப்படுகிறார்.', neutral_sign: 'இந்த விதிமுறையில் ராசி அதிபர் சமமாக வகைப்படுத்தப்படுகிறார்.', enemy_sign: 'இந்த விதிமுறையில் ராசி அதிபர் இயற்கைப் பகையாக வகைப்படுத்தப்படுகிறார்.' },
} as const;

export function VedicDignitySection({ analysis, loading, error, language }: {
  analysis: VedicDignityAnalysis | null; loading: boolean; error: string; language: AstroLanguage;
}) {
  const ta = language === 'ta';
  const text = (en: string, tamil: string) => ta ? tamil : en;
  return <section className="chart-data-section vedic-dignity-section" aria-labelledby="vedic-dignity-heading">
    <h3 id="vedic-dignity-heading">{text('Planetary dignity', 'கிரக கண்ணியம்')}</h3>
    {loading ? <p role="status">{text('Loading saved-chart analysis…', 'சேமித்த ஜாதகப் பகுப்பாய்வு ஏற்றப்படுகிறது…')}</p> : error ? <p className="chart-muted" role="status">{error}</p> : analysis ? <>
      <p className="dignity-method-note">{text('Traditional Parashari sign classifications. This ruleset is provisional because the exact print edition has not been verified; these are not scientifically established measures of personality, strength, or future outcomes.', 'பாரம்பரிய பராசர ராசி வகைப்பாடுகள். அச்சுப் பதிப்பு சரிபார்க்கப்படாததால் இந்த விதிமுறை தற்காலிகமானது; இவை ஆளுமை, வலிமை அல்லது எதிர்காலத்தை அளக்கும் அறிவியல் முறைகள் அல்ல.')}</p>
      <div className="chart-table-wrap"><table className="chart-table"><thead><tr>
        <th>{text('Planet', 'கிரகம்')}</th><th>{text('Sign', 'ராசி')}</th><th>{text('Degree', 'பாகை')}</th><th>{text('Classification', 'வகைப்பாடு')}</th><th>{text('Sign lord relationship', 'ராசி அதிபருடனான உறவு')}</th>
      </tr></thead><tbody>{analysis.planets.map((planet: VedicDignityPlanet) => <tr key={planet.planet}>
        <td>{localizePlanet(language, planet.planet)}</td><td>{localizeSign(language, planet.rashi)}</td><td>{planet.degree_in_rashi.toFixed(2)}°</td>
        <td><b>{DIGNITY_LABELS[language][planet.dignity]}</b><small className="dignity-row-explanation">{DIGNITY_EXPLANATIONS[language][planet.dignity]}</small></td><td>{localizePlanet(language, planet.sign_lord)} · {DIGNITY_LABELS[language][planet.relationship_to_sign_lord]}</td>
      </tr>)}</tbody></table></div>
      <small className="dignity-provenance">{text('Provisional source locator:', 'தற்காலிக ஆதார இடம்:')} {analysis.source_locator} · {analysis.ruleset_id}</small>
      <div className="dignity-source-list" aria-label={text('Source references', 'ஆதாரக் குறிப்புகள்')}>{analysis.source_references.map(source => <a key={source.source_id} href={source.url ?? undefined} target="_blank" rel="noreferrer">{source.source_id} · {text('edition unverified', 'பதிப்பு சரிபார்க்கப்படவில்லை')}</a>)}</div>
      <p className="dignity-method-note">{text('Rahu and Ketu are not classified in this seven-planet method. Shadbala is unavailable; no score is produced.', 'இந்த ஏழு கிரக முறையில் ராகு, கேதுவுக்கு வகைப்பாடு வழங்கப்படவில்லை. ஷட்பலம் கிடைக்கவில்லை; மதிப்பெண் உருவாக்கப்படாது.')}</p>
    </> : <p className="chart-muted">{text('No completed Vedic D1 chart is available for this analysis.', 'இந்தப் பகுப்பாய்வுக்கான முடிக்கப்பட்ட வேத D1 ஜாதகம் இல்லை.')}</p>}
  </section>;
}
