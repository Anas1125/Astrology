import type { AstrologyResult } from './types';
import { localizeAspect, localizePlanet, localizeSign } from './i18n';
import type { AstroLanguage } from './i18n';

const PLANET_GLYPHS: Record<string, string> = { Sun: '☉', Moon: '☽', Mercury: '☿', Venus: '♀', Mars: '♂', Jupiter: '♃', Saturn: '♄', Uranus: '♅', Neptune: '♆', Pluto: '♇' };
const ASPECT_COLORS: Record<string, string> = { conjunction: '#d2b875', sextile: '#6aa9bd', square: '#d87979', trine: '#75aa8b', opposition: '#c584a1' };

function point(longitude: number, radius: number, center = 220): [number, number] {
  const radians = (longitude - 90) * Math.PI / 180;
  return [center + Math.cos(radians) * radius, center + Math.sin(radians) * radius];
}

function midLongitude(start: number, end: number): number {
  return (start + ((end - start + 360) % 360) / 2) % 360;
}

function formatPosition(longitude: number) {
  const normalized = longitude % 360;
  return `${Math.floor(normalized / 30)}° ${((normalized % 30)).toFixed(2)}′`;
}

export default function WesternChartView({ data, language }: { data: AstrologyResult; language: AstroLanguage }) {
  const ta = language === 'ta';
  const t = (en: string, tamil: string) => ta ? tamil : en;
  const houses = data.houses;
  const aspects = data.aspects ?? [];
  const positions = new Map(data.planets.map((planet, index) => [planet.name, { ...point(planet.longitude, 147 + (index % 3) * 5), planet }]));
  return <div className="western-chart-content">
    <div className="western-angle-cards"><div><small>{t('Ascendant', 'லக்னம்')}</small><b>{data.ascendant?.sign ? localizeSign(language, data.ascendant.sign) : '—'}</b><span>{data.ascendant ? formatPosition(data.ascendant.longitude) : ''}</span></div><div><small>{t('Midheaven', 'மத்திய உச்சம்')}</small><b>{data.midheaven?.sign ? localizeSign(language, data.midheaven.sign) : '—'}</b><span>{data.midheaven ? formatPosition(data.midheaven.longitude) : ''}</span></div></div>
    <div className="western-wheel-wrap"><svg className="western-wheel" viewBox="0 0 440 440" role="img" aria-label={t('Western tropical natal chart wheel', 'மேற்கத்திய நிராயண பிறப்பு ஜாதக வட்டம்')}>
      <circle cx="220" cy="220" r="204" className="wheel-outer"/><circle cx="220" cy="220" r="180" className="wheel-zodiac-ring"/><circle cx="220" cy="220" r="116" className="wheel-inner"/>
      {houses.map((house, index) => {
        const next = houses[(index + 1) % houses.length];
        const [x1,y1] = point(house.cusp_longitude, 116);
        const [x2,y2] = point(house.cusp_longitude, 180);
        const [tx,ty] = point(midLongitude(house.cusp_longitude, next.cusp_longitude), 195);
        return <g key={house.number}><line x1={x1} y1={y1} x2={x2} y2={y2} className="wheel-house-line"/><text x={tx} y={ty} className="wheel-house-label" textAnchor="middle" dominantBaseline="middle">{house.number}</text></g>;
      })}
      {aspects.map((aspect, index) => {
        const a = positions.get(aspect.planet_a); const b = positions.get(aspect.planet_b);
        if (!a || !b) return null;
        return <line key={`${aspect.planet_a}-${aspect.planet_b}-${aspect.aspect}-${index}`} x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} stroke={ASPECT_COLORS[aspect.aspect] ?? '#81899b'} className="wheel-aspect-line"/>;
      })}
      {data.planets.map((planet, index) => {
        const [x,y] = point(planet.longitude, 147 + (index % 3) * 5);
        return <g key={planet.name} className="wheel-planet"><circle cx={x} cy={y} r="11"/><text x={x} y={y + 1} textAnchor="middle" dominantBaseline="middle">{PLANET_GLYPHS[planet.name] ?? planet.name.slice(0, 2)}</text><title>{`${localizePlanet(language, planet.name)} · ${planet.sign ? localizeSign(language, planet.sign) : ''} ${formatPosition(planet.longitude)}`}</title></g>;
      })}
      {data.ascendant && <g className="wheel-angle asc-angle"><line x1="220" y1="220" x2={point(data.ascendant.longitude, 181)[0]} y2={point(data.ascendant.longitude, 181)[1]}/><text x={point(data.ascendant.longitude, 168)[0]} y={point(data.ascendant.longitude, 168)[1]} textAnchor="middle">ASC</text></g>}
      {data.midheaven && <g className="wheel-angle mc-angle"><line x1="220" y1="220" x2={point(data.midheaven.longitude, 181)[0]} y2={point(data.midheaven.longitude, 181)[1]}/><text x={point(data.midheaven.longitude, 168)[0]} y={point(data.midheaven.longitude, 168)[1]} textAnchor="middle">MC</text></g>}
    </svg></div>

    <section className="chart-data-section"><h3>{t('Planet placements', 'கிரக நிலைகள்')}</h3><div className="chart-table-wrap"><table className="chart-table"><thead><tr><th>{t('Planet', 'கிரகம்')}</th><th>{t('Sign', 'ராசி')}</th><th>{t('Degrees', 'பாகை')}</th><th>{t('House', 'பாவம்')}</th><th>{t('Motion', 'இயக்கம்')}</th></tr></thead><tbody>{data.planets.map(planet => <tr key={planet.name}><td>{localizePlanet(language, planet.name)}</td><td>{planet.sign ? localizeSign(language, planet.sign) : '—'}</td><td>{formatPosition(planet.longitude)}</td><td>{planet.house ?? '—'}</td><td>{planet.retrograde ? t('Retrograde', 'வக்கிரம்') : t('Direct', 'நேர்கதி')}</td></tr>)}</tbody></table></div></section>

    <section className="chart-data-section"><h3>{t('Major aspects', 'முக்கிய பார்வைகள்')}</h3>{aspects.length === 0 ? <p className="chart-muted">{t('No major aspects fall within the configured orbs.', 'அமைக்கப்பட்ட பாகை வரம்பில் முக்கிய பார்வைகள் இல்லை.')}</p> : <div className="chart-table-wrap"><table className="chart-table"><thead><tr><th>{t('Planets', 'கிரகங்கள்')}</th><th>{t('Aspect', 'பார்வை')}</th><th>{t('Orb', 'பாகை வேறுபாடு')}</th><th>{t('Motion', 'நிலை')}</th></tr></thead><tbody>{aspects.map((aspect,index) => <tr key={`${aspect.planet_a}-${aspect.planet_b}-${aspect.aspect}-${index}`}><td>{localizePlanet(language, aspect.planet_a)} · {localizePlanet(language, aspect.planet_b)}</td><td>{localizeAspect(language, aspect.aspect)}</td><td>{aspect.orb.toFixed(2)}°</td><td>{aspect.motion === 'applying' ? t('Applying', 'நெருங்கும்') : aspect.motion === 'separating' ? t('Separating', 'விலகும்') : aspect.motion === 'exact' ? t('Exact', 'துல்லியம்') : t('Unknown', 'தெரியாது')}</td></tr>)}</tbody></table></div>}</section>
  </div>;
}
