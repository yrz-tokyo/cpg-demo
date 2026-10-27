import { useEffect, useState } from 'react'
import { api } from './api'
import { Chip } from './components/Chip'
import { EffectScreen } from './components/EffectScreen'
import { PersonaScreen } from './components/PersonaScreen'
import { ReviewScreen } from './components/ReviewScreen'
import type { Me } from './types'

type Tab = 'persona' | 'review' | 'effect'

const TABS: { id: Tab; n: string; label: string; who: string }[] = [
  { id: 'persona', n: '01', label: '現場の問い',   who: '顧客デモ' },
  { id: 'review',  n: '02', label: '衝突を裁く',   who: 'データスチュワード' },
  { id: 'effect',  n: '03', label: '統治の効果',   who: 'FE Bar' },
]

export default function App() {
  const [tab, setTab] = useState<Tab>('persona')
  const [me, setMe] = useState<Me | null>(null)

  useEffect(() => { api.me().then(setMe).catch(() => setMe(null)) }, [])

  return (
    <div className="shell">
      <header className="top">
        <div className="identity">
          <h1>Brickshouse Food and Beverage — データ統治コックピット</h1>
          <span className="sub">
            同じ言葉が部門で違う意味を持つ状態を、見つけて・決めて・効果を測る
          </span>
        </div>
        <nav className="screens">
          {TABS.map((t) => (
            <button key={t.id} className="screen-tab" aria-current={t.id === tab}
                    onClick={() => setTab(t.id)}>
              <span className="n">{t.n}</span>
              <span className="label">{t.label}</span>
              <span className="who">{t.who}</span>
            </button>
          ))}
        </nav>
      </header>

      <div className="chips">
        <Chip mono>{me?.catalog ?? '—'}</Chip>
        {me && Object.keys(me.spaces).length > 0
          ? <Chip kind="on">Genie Agent {Object.keys(me.spaces).length} 本</Chip>
          : <Chip kind="warn">Genie Agent 未設定</Chip>}
        <Chip>{me?.email ?? '—'}</Chip>
        {me && !me.can_review && <Chip kind="warn">衝突レビュー権限なし</Chip>}
      </div>

      {tab === 'persona' && <PersonaScreen />}
      {tab === 'review' && <ReviewScreen canReview={me?.can_review ?? true} />}
      {tab === 'effect' && <EffectScreen />}
    </div>
  )
}
