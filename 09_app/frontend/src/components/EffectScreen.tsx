import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import type { EvalCompare, EvalItem, EvalSummary, Rate } from '../types'
import { Chip } from './Chip'
import { Verdict } from './Verdict'

const pct = (r: Rate | undefined) =>
  r && r.pct !== null ? `${r.pct.toFixed(0)}%` : '—'
const frac = (r: Rate | undefined) => (r ? `${r.k}/${r.n}` : '—')

/** KPI は3つまで。単位・期間・基準・出所を必ず添える。 */
function Kpi({ k, before, after, basis }: {
  k: string
  before: Rate | undefined
  after: Rate | undefined
  basis: string
}) {
  return (
    <div className="kpi">
      <span className="k">{k}</span>
      <div className="kpi-pair">
        <div className="kpi-fig">
          <span className="n">{pct(before)}</span>
          <span className="c">統治前 {frac(before)}</span>
        </div>
        <span className="kpi-arrow">→</span>
        <div className={`kpi-fig kpi-fig-after${after ? '' : ' kpi-pending'}`}>
          <span className="n">{after ? pct(after) : '未測定'}</span>
          <span className="c">{after ? `統治後 ${frac(after)}` : '統治ONの測定が未実施'}</span>
        </div>
      </div>
      <div className="kpi-basis">{basis}</div>
    </div>
  )
}

function Side({ title, side, truth }: {
  title: string
  side: EvalItem['before']
  truth: number[]
}) {
  return (
    <div className={`ba-side ba-${title === '統治前' ? 'before' : 'after'}`}>
      <h3>{title} <Verdict v={side.verdict} /></h3>
      {side.text
        ? <div className="answer-text">{side.text}</div>
        : <p className="empty" style={{ padding: '6px 0' }}>回答なし</p>}
      {side.refs.length > 0 && (
        <div className="chips">
          {side.refs.map((r) => <Chip key={r} mono>{r}</Chip>)}
        </div>
      )}
      {side.numbers.length > 0 && (
        <div className="truth">
          Genie の数値: {side.numbers.slice(0, 4).join(' / ')}
          {truth.length > 0 && <>　|　正解: {truth.slice(0, 4).join(' / ')}</>}
        </div>
      )}
      {side.sql && <pre className="sql">{side.sql}</pre>}
    </div>
  )
}

export function EffectScreen() {
  const [data, setData] = useState<EvalCompare | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [sel, setSel] = useState<string | null>(null)

  useEffect(() => {
    api.evalCompare().then(setData).catch((e) => setErr(String(e)))
  }, [])

  const item = useMemo(
    () => data?.items.find((x) => x.id === sel) ?? data?.items[0] ?? null, [data, sel])

  const b: EvalSummary | null = data?.before ?? null
  const a: EvalSummary | null = data?.after ?? null
  const flipped = data?.items.filter((x) => x.flipped).length ?? 0

  return (
    <div style={{ display: 'grid', gridTemplateRows: 'auto minmax(0,1fr)', gap: 16, minHeight: 0 }}>
      <div className="kpis">
        <Kpi k="正しい数字を返した率" before={b?.total} after={a?.total}
             basis="49問・部門別 Genie Agent にルーティング・許容誤差2%・正解は SQL で定義。出所 04_eval/eval_*.json" />
        <Kpi k="正本を引用した率" before={b?.source} after={a?.source}
             basis="生成SQL が参照したオブジェクトに、正本として定義したものが含まれる割合。出所 同左" />
        <Kpi k="聞き返して止まった率" before={b?.clarified} after={a?.clarified}
             basis="数値を返さず問い返して終わった割合。統治前は正しい振る舞いでもある。統治後に下がるのが期待。出所 同左" />
      </div>

      <div className="cols cols-46">
        <div className="panel">
          <div className="panel-head">
            <h2>同じ49問の、統治前と統治後</h2>
            <span className="hint">
              {a ? `判定が変わった ${flipped} 問を上に表示` : '統治後は未測定'}
            </span>
          </div>
          <div className="panel-body-flush">
            {err && <p className="empty">{err}</p>}
            {!err && !data?.items.length && <p className="empty">評価結果がまだありません。</p>}
            {data?.items.map((x) => (
              <button key={x.id} className="flip" aria-current={x.id === item?.id}
                      onClick={() => setSel(x.id)}>
                <span className="q-id">{x.id}</span>
                <span className="text">
                  {x.question}
                  {x.conflict && <> <Chip kind="trap">定義が割れる</Chip></>}
                </span>
                <span className="flip-verdicts">
                  <Verdict v={x.before.verdict} />
                  <span style={{ color: 'var(--text-soft)' }}>→</span>
                  <Verdict v={x.after.verdict} />
                </span>
              </button>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <h2>{item ? item.id : '詳細'}</h2>
            <span className="hint">{item?.authoritative}</span>
          </div>
          <div className="panel-body">
            {!item && <p className="empty">左から質問を選んでください。</p>}
            {item && (
              <div className="ba">
                <p style={{ margin: 0, fontSize: 'var(--t-body)', fontWeight: 600 }}>{item.question}</p>
                <div className="chips">
                  <Chip>{item.dept}</Chip>
                  <Chip>{item.persona}</Chip>
                  {item.conflict && <Chip kind="trap">定義が割れる問い</Chip>}
                </div>
                <Side title="統治前" side={item.before} truth={item.truth} />
                <Side title="統治後" side={item.after} truth={item.truth} />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
