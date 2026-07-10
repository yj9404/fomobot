import { useC } from '../ThemeContext'
import type { Lang } from '../types'

export const FOOTER_LINKS = [
  { href: '/about.html', ko: '소개', en: 'About' },
  { href: '/methodology.html', ko: '방법론', en: 'Methodology' },
  { href: '/survivorship-bias.html', ko: '생존 편향', en: 'Survivorship bias' },
  { href: '/glossary.html', ko: '용어 해설', en: 'Glossary' },
  { href: '/privacy.html', ko: '개인정보처리방침', en: 'Privacy' },
  {
    href: 'mailto:yjlee.k94@gmail.com?subject=%5BFomoBot%5D%20%EB%B2%84%EA%B7%B8%2F%EA%B8%B0%EB%8A%A5%20%EB%AC%B8%EC%9D%98',
    hrefEn: 'mailto:yjlee.k94@gmail.com?subject=%5BFomoBot%5D%20Bug%2FFeature%20Request',
    ko: '버그 및 기능 문의',
    en: 'Report a Bug or Feature',
  },
]

export function Footer({ lang, style }: { lang: Lang; style?: React.CSSProperties }) {
  const C = useC()
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 10px', fontSize: 10.5, ...style }}>
      {FOOTER_LINKS.map((l) => (
        <a
          key={l.href}
          href={lang === 'en' && 'hrefEn' in l ? l.hrefEn : l.href}
          style={{ color: C.textDim, textDecoration: 'none' }}
        >
          {lang === 'ko' ? l.ko : l.en}
        </a>
      ))}
    </div>
  )
}
