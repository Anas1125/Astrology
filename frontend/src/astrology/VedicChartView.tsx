import { useEffect, useMemo, useState } from 'react';
import type { AstrologyResult, PlanetPosition } from './types';
import { localizeNakshatra, localizePlanet, localizeSign } from './i18n';
import type { AstroLanguage } from './i18n';

type Layout = 'south' | 'north';
const SIGN_NAMES = ['Mesha', 'Vrishabha', 'Mithuna', 'Karka', 'Simha', 'Kanya', 'Tula', 'Vrischika', 'Dhanu', 'Makara', 'Kumbha', 'Meena'];
const SOUTH_CELLS: Array<[number, number]> = [[0,1],[0,2],[0,3],[1,3],[2,3],[3,3],[3,2],[3,1],[3,0],[2,0],[1,0],[0,0]];
const NORTH_CENTERS: Array<[number, number]> = [[200,78],[292,112],[328,166],[328,200],[328,234],[292,288],[200,322],[108,288],[72,234],[72,200],[72,166],[108,112]];

function planetSignIndex(planet: PlanetPosition) {
  if (typeof planet.division_rashi_index === 'number') return planet.division_rashi_index;
  return SIGN_NAMES.indexOf(planet.division_rashi ?? planet.nakshatra?.rashi ?? '');
}

function planetLongitude(planet: PlanetPosition, division: 'D1' | 'D9') {
  return division === 'D9' ? planet.division_longitude ?? planet.d9?.longitude ?? planet.longitude : planet.longitude;
}

function shortName(language: AstroLanguage, name: string) {
  if (language === 'ta') return localizePlanet(language, name);
  return ({ Jupiter: 'Jup', Mercury: 'Mer', Neptune: 'Nep', Sagittarius: 'Sag' } as Record<string, string>)[name] ?? name.slice(0, 3);
}

export function VedicChartView({ data, division, language, initialLayout = 'south' }: { data: AstrologyResult; division: 'D1' | 'D9'; language: AstroLanguage; initialLayout?: Layout }) {
  const [layout, setLayout] = useState<Layout>(initialLayout);
  const limitedChart = data.calculation_mode === 'limited_date_only';
  useEffect(() => { if (limitedChart && layout !== 'south') setLayout('south'); }, [limitedChart, layout]);
  const t = (en: string, ta: string) => language === 'ta' ? ta : en;
  const signPlanets = useMemo(() => {
    const grouped = new Map<number, PlanetPosition[]>();
    data.planets.forEach(planet => {
      const index = planetSignIndex(planet);
      if (index < 0) return;
      grouped.set(index, [...(grouped.get(index) ?? []), planet]);
    });
    return grouped;
  }, [data.planets, division]);
  const ascendantSign = division === 'D9'
    ? data.ascendant?.division_rashi ?? data.ascendant?.d9?.rashi
    : data.ascendant?.rashi;
  const ascendantLongitude = division === 'D9'
    ? data.ascendant?.division_longitude ?? data.ascendant?.d9?.longitude
    : data.ascendant?.longitude;
  const ascendantHouse = division === 'D9' ? data.ascendant?.division_house : data.ascendant?.house;

  return <div className="vedic-chart-content">
    <div className="chart-control-row">
      {!limitedChart && <div className="segmented-control" role="group" aria-label={t('Chart layout', 'ஜாதக வடிவம்')}>
        <button aria-pressed={layout === 'south'} onClick={() => setLayout('south')}>{t('South Indian', 'தென்னிந்திய முறை')}</button>
        <button aria-pressed={layout === 'north'} onClick={() => setLayout('north')}>{t('North Indian', 'வடஇந்திய முறை')}</button>
      </div>}
      <span className="chart-convention">{division} · {t('Sidereal · Lahiri', 'நிராயண · லாஹிரி')}</span>
    </div>

    <div className="vedic-chart-summary">
      {!limitedChart && <div><small>{t('Ascendant', 'லக்னம்')}</small><b>{ascendantSign ? localizeSign(language, ascendantSign) : '—'}</b><span>{typeof ascendantLongitude === 'number' ? `${(ascendantLongitude % 30).toFixed(2)}°` : ''}{ascendantHouse ? ` · ${t('House', 'பாவம்')} ${ascendantHouse}` : ''}</span></div>}
      <div><small>{limitedChart ? t('Moon Nakshatra · noon estimate', 'சந்திர நட்சத்திரம் · நண்பகல் மதிப்பீடு') : t('Moon Nakshatra', 'சந்திர நட்சத்திரம்')}</small><b>{data.planets.find(planet => planet.name === 'Moon')?.nakshatra ? localizeNakshatra(language, data.planets.find(planet => planet.name === 'Moon')!.nakshatra!.name) : '—'}</b><span>{data.planets.find(planet => planet.name === 'Moon')?.nakshatra ? `${t('Pada', 'பாதம்')} ${data.planets.find(planet => planet.name === 'Moon')!.nakshatra!.pada}` : ''}</span></div>
    </div>

    {layout === 'south' ? <div className="south-chart" role="img" aria-label={t('South Indian sign chart', 'தென்னிந்திய ராசிக் கட்டம்')}>
      {SIGN_NAMES.map((sign, index) => {
        const [row, column] = SOUTH_CELLS[index];
        return <div className={`south-chart-cell${!limitedChart && index === 0 && division === 'D1' ? ' ascendant-cell' : ''}`} style={{ gridRow: row + 1, gridColumn: column + 1 }} key={sign}>
          <small>{index + 1}. {localizeSign(language, sign)}</small>
          {!limitedChart && index === (typeof data.ascendant?.rashi_index === 'number' && division === 'D1' ? data.ascendant.rashi_index : division === 'D9' ? data.ascendant?.d9?.rashi_index ?? -1 : -1) && <i>{t('Asc', 'லக்')}</i>}
          <div>{(signPlanets.get(index) ?? []).map(planet => <span className="chart-planet-chip" key={planet.name} title={localizePlanet(language, planet.name)}>{shortName(language, planet.name)}</span>)}</div>
        </div>;
      })}
      <div className="south-chart-center"><span>ASTROAI · {division}</span><strong>{limitedChart ? t('Date-only chart', 'தேதி-மட்டும் ஜாதகம்') : t('Ascendant', 'லக்னம்')}</strong><b>{limitedChart ? t('Birth time unknown', 'பிறந்த நேரம் தெரியாது') : ascendantSign ? localizeSign(language, ascendantSign) : '—'}</b><small>{limitedChart ? t('No houses or angles', 'பாவங்கள் அல்லது கோணங்கள் இல்லை') : ascendantHouse ? `${t('House', 'பாவம்')} ${ascendantHouse}` : ''}</small></div>
    </div> : <svg className="north-chart" viewBox="0 0 400 400" role="img" aria-label={t('North Indian house chart', 'வடஇந்திய பாவக் கட்டம்')}>
      <rect x="10" y="10" width="380" height="380" fill="#101727" stroke="#b99a5b" strokeWidth="1.5"/>
      <path d="M10 10 L390 390 M390 10 L10 390 M200 10 L390 200 L200 390 L10 200 Z" fill="none" stroke="#726341" strokeWidth="1"/>
      {Array.from({ length: 12 }, (_, index) => {
        const house = index + 1;
        const [x, y] = NORTH_CENTERS[index];
        const cusp = data.division_houses?.find(item => item.number === house);
        const housePlanets = data.planets.filter(planet => (division === 'D9' ? planet.division_house : planet.house) === house);
        return <g key={house} className="north-chart-house"><text x={x} y={y - 13} textAnchor="middle" className="north-house-number">{house}</text><text x={x} y={y + 3} textAnchor="middle" className="north-house-sign">{cusp?.sign ? localizeSign(language, cusp.sign) : ''}</text><text x={x} y={y + 20} textAnchor="middle" className="north-house-planets">{housePlanets.map(planet => shortName(language, planet.name)).join(' · ')}</text></g>;
      })}
    </svg>}

    <section className="chart-data-section"><h3>{t('Planet placements', 'கிரக நிலைகள்')}</h3><div className="chart-table-wrap"><table className="chart-table"><thead><tr><th>{t('Planet', 'கிரகம்')}</th><th>{t('Sign', 'ராசி')}</th><th>{t('Degrees', 'பாகை')}</th>{!limitedChart && <th>{t('House', 'பாவம்')}</th>}<th>{t('Nakshatra', 'நட்சத்திரம்')} · {t('Pada', 'பாதம்')}</th><th>{t('Motion', 'இயக்கம்')}</th></tr></thead><tbody>{data.planets.map(planet => {
      const sign = division === 'D9' ? planet.division_rashi : planet.nakshatra?.rashi;
      const house = division === 'D9' ? planet.division_house : planet.house;
      return <tr key={planet.name}><td>{localizePlanet(language, planet.name)}</td><td>{sign ? localizeSign(language, sign) : '—'}</td><td>{(planetLongitude(planet, division) % 30).toFixed(2)}°</td>{!limitedChart && <td>{house ?? '—'}</td>}<td>{planet.nakshatra ? `${localizeNakshatra(language, planet.nakshatra.name)} · ${planet.nakshatra.pada}` : '—'}</td><td>{planet.retrograde ? t('Retrograde', 'வக்கிரம்') : t('Direct', 'நேர்கதி')}</td></tr>;
    })}</tbody></table></div></section>

    {data.vimshottari_dasha && <section className="dasha-grid"><DashaPanel title={t('Vimshottari Mahadasha', 'விம்சோத்தரி மகாதசை')} items={data.vimshottari_dasha.mahadashas} language={language}/><DashaPanel title={t('Antardasha', 'அந்தர்தசை')} items={data.vimshottari_dasha.antardashas.map(item => ({ ...item, lord: `${item.mahadasha_lord ?? ''} · ${item.lord}` }))} language={language}/>{data.vimshottari_dasha.pratyantardashas?.length ? <DashaPanel title={t('Pratyantardasha', 'பிரத்யந்தர தசை')} items={data.vimshottari_dasha.pratyantardashas.map(item => ({ ...item, lord: `${item.mahadasha_lord ?? ''} · ${item.antardasha_lord ?? ''} · ${item.lord}` }))} language={language}/> : null}<p className="savana-note">{t('Periods use the configured 360-day Savana year convention.', 'இந்தக் காலங்கள் அமைக்கப்பட்ட 360 நாள் சாவன ஆண்டு முறையைப் பயன்படுத்துகின்றன.')}</p></section>}
  </div>;
}

function DashaPanel({ title, items, language }: { title: string; items: Array<{ lord: string; start: string; end: string; balance_days_at_birth?: number | null }>; language: AstroLanguage }) {
  const t = (en: string, ta: string) => language === 'ta' ? ta : en;
  return <section className="dasha-panel"><h3>{title}</h3><ol>{items.slice(0, 12).map((item, index) => <li key={`${item.lord}-${item.start}-${index}`}><b>{item.lord}</b><span>{new Date(item.start).toLocaleDateString(language === 'ta' ? 'ta-IN' : 'en', { dateStyle: 'medium', timeZone: 'UTC' })} – {new Date(item.end).toLocaleDateString(language === 'ta' ? 'ta-IN' : 'en', { dateStyle: 'medium', timeZone: 'UTC' })}</span>{index === 0 && typeof item.balance_days_at_birth === 'number' && <small>{t('Birth balance', 'பிறப்பு இருப்புக் காலம்')}: {Math.round(item.balance_days_at_birth)} {t('days', 'நாட்கள்')}</small>}</li>)}</ol></section>;
}
