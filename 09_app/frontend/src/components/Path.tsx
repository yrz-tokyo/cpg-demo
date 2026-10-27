import type { Answer, Persona } from '../types'

/** 下段はログではなく、動作する構成図。
 *  質問が答えになるまでに通る5つのノードを、実際の応答で埋めていく。 */
export function Path({ persona, question, answer, busy }: {
  persona: Persona | null
  question: string | null
  answer: Answer | null
  busy: boolean
}) {
  const certified = answer?.citations.filter((c) => c.certification === 'certified') ?? []
  const nodes: { k: string; v: string; live: boolean }[] = [
    { k: '聞く人', v: persona ? `${persona.name}（${persona.dept}）` : '—', live: !!persona },
    { k: '問い', v: question ?? '—', live: !!question },
    {
      k: 'Genie Agent',
      v: persona ? `Brickshouse ${persona.dept}` : '—',
      live: busy || !!answer,
    },
    {
      k: '引用元',
      v: answer ? (answer.refs.length ? answer.refs.join(' / ') : '文章で回答') : (busy ? '照会中' : '—'),
      live: !!answer,
    },
    {
      k: '認定',
      v: answer ? (certified.length ? `${certified.length}件が認定済み` : '認定なし') : '—',
      live: !!answer && certified.length > 0,
    },
  ]
  return (
    <div className="path">
      {nodes.map((n) => (
        <div key={n.k} className={`path-node ${n.live ? 'path-node-live' : 'path-node-idle'}`}>
          <div className="k">{n.k}</div>
          <div className="v" title={n.v}>{n.v}</div>
        </div>
      ))}
    </div>
  )
}
