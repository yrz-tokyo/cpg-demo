import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import type { Conflict, LabelRow } from '../types'
import { Chip } from './Chip'

const fmt = (n: number | null) =>
  n === null ? '—' : n.toLocaleString('ja-JP', { maximumFractionDigits: 0 })

const ROLE_LABEL: Record<string, string> = {
  authoritative: '正本',
  not_this_concept: 'この概念ではない',
  variant: '別の切り口',
  candidate: '未判断',
}

export function ReviewScreen({ canReview }: { canReview: boolean }) {
  const [conflicts, setConflicts] = useState<Conflict[]>([])
  const [labels, setLabels] = useState<LabelRow[]>([])
  const [cid, setCid] = useState<number | null>(null)
  const [decision, setDecision] = useState('approve')
  const [auth, setAuth] = useState('')
  const [term, setTerm] = useState('')
  const [why, setWhy] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [note, setNote] = useState<string | null>(null)

  async function load() {
    setErr(null)
    try {
      const d = await api.conflicts()
      setConflicts(d.conflicts)
      setLabels(d.labels)
      setCid((c) => c ?? d.conflicts[0]?.conflict_id ?? null)
    } catch (e) {
      setErr(String(e))
    }
  }
  useEffect(() => { void load() }, [])

  const cur = useMemo(
    () => conflicts.find((c) => c.conflict_id === cid) ?? null, [conflicts, cid])

  useEffect(() => {
    if (!cur) return
    const lead = [...cur.candidates].sort(
      (a, b) => (b.observed_value ?? -1) - (a.observed_value ?? -1))[0]
    setAuth(cur.authoritative_object ?? lead?.object_name ?? '')
    setTerm(cur.term)
    setDecision(cur.decision ?? 'approve')
    setWhy(cur.rationale ?? '')
    setNote(null)
  }, [cur?.conflict_id])

  async function submit() {
    if (!cur) return
    setBusy(true); setErr(null); setNote(null)
    try {
      const r = await api.decide({
        conflict_id: cur.conflict_id,
        decision,
        authoritative_object: decision === 'approve' ? auth : null,
        rationale: why,
        term,
      })
      setLabels(r.labels)
      setNote(decision === 'reject'
        ? 'Lakebase に記録しました。却下したペアは次回の検出で再提案されません。'
        : 'Lakebase に記録しました。この判断が ML の学習ラベルになります。')
      await load()
    } catch (e) {
      setErr(String(e))
    } finally {
      setBusy(false)
    }
  }

  const pos = labels.filter((l) => l.label === 1).reduce((s, l) => s + Number(l.n), 0)
  const neg = labels.filter((l) => l.label === 0).reduce((s, l) => s + Number(l.n), 0)

  return (
    <div className="cols cols-37">
      <div className="panel">
        <div className="panel-head">
          <h2>検出された定義の衝突</h2>
          <span className="hint">未判断が上</span>
        </div>
        <div className="panel-body-flush">
          {err && <p className="empty">Lakebase: {err}</p>}
          {!err && !conflicts.length && <p className="empty">検出結果がありません。</p>}
          {conflicts.map((c) => (
            <button key={c.conflict_id} className="conf" aria-current={c.conflict_id === cid}
                    onClick={() => setCid(c.conflict_id)}>
              <span className="term">{c.term}</span>
              <span className="measure">{c.measure_name}</span>
              <span className="meta" style={{ display: 'flex', gap: 6, paddingTop: 3 }}>
                <Chip>{c.candidates.length} 候補</Chip>
                {c.ml_score !== null && <Chip mono>score {c.ml_score.toFixed(2)}</Chip>}
                {c.decision === 'approve' && <Chip kind="on">正本を決定</Chip>}
                {c.decision === 'reject' && <Chip kind="off">却下</Chip>}
                {!c.decision && <Chip kind="warn">未判断</Chip>}
              </span>
            </button>
          ))}
        </div>
      </div>

      <div className="panel">
        <div className="panel-head">
          <h2>{cur ? `「${cur.term}」を名乗っている定義` : '候補'}</h2>
          <span className="hint">
            {cur ? `measure: ${cur.measure_name} / 検出器 ${cur.detector_version ?? '—'}` : ''}
          </span>
        </div>
        <div className="panel-body">
          {!cur && <p className="empty">左から衝突を選んでください。</p>}
          {cur && (
            <div style={{ display: 'grid', gap: 18 }}>
              {cur.evidence?.summary && (
                <div className="answer-text" style={{ fontSize: 'var(--t-small)' }}>
                  {cur.evidence.summary}
                  <div className="chips" style={{ paddingTop: 8 }}>
                    <Chip mono>最大/最小 {cur.evidence.max_over_min ?? '—'} 倍</Chip>
                    <Chip>{cur.evidence.candidate_count ?? cur.candidates.length} 候補</Chip>
                    {(cur.evidence.departments ?? []).map((d) => <Chip key={d}>{d}</Chip>)}
                    <Chip mono>{cur.evidence.detector ?? '—'}</Chip>
                  </div>
                </div>
              )}
              <table className="cand-table">
                <thead>
                  <tr>
                    <th>オブジェクト</th>
                    <th>部門</th>
                    <th>種別</th>
                    <th className="num">その定義で出る値</th>
                    <th>いまの役割</th>
                  </tr>
                </thead>
                <tbody>
                  {[...cur.candidates]
                    .sort((a, b) => (b.observed_value ?? -1) - (a.observed_value ?? -1))
                    .map((c, i) => (
                      <tr key={c.candidate_id}>
                        <td className="cand-obj">
                          {c.object_name}
                          {c.note && <div className="cite-comment">{c.note}</div>}
                        </td>
                        <td>{c.department ?? '—'}</td>
                        <td style={{ fontSize: 'var(--t-micro)', color: 'var(--text-soft)' }}>
                          {c.object_type}
                        </td>
                        <td className={`num${i === 0 ? ' num-lead' : ''}`}>{fmt(c.observed_value)}</td>
                        <td>
                          {c.object_name === auth && decision === 'approve'
                            ? <Chip kind="cert">正本にする</Chip>
                            : <Chip kind={c.role === 'candidate' ? 'warn' : 'off'}>
                                {ROLE_LABEL[c.role] ?? c.role}
                              </Chip>}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>

              <div className="decide">
                <label>
                  業務用語（検出器が付けた候補。会話で使う言葉に直してください）
                  <input value={term} onChange={(e) => setTerm(e.target.value)}
                         placeholder="例: 売上" />
                </label>
                <label>
                  判断
                  <select value={decision} onChange={(e) => setDecision(e.target.value)}>
                    <option value="approve">これは本当の衝突 — 正本を決める</option>
                    <option value="reject">衝突ではない — 却下する</option>
                    <option value="defer">保留する</option>
                  </select>
                </label>
                {decision === 'approve' && (
                  <label>
                    正本にするオブジェクト
                    <select value={auth} onChange={(e) => setAuth(e.target.value)}>
                      {cur.candidates.map((c) => (
                        <option key={c.candidate_id} value={c.object_name}>{c.object_name}</option>
                      ))}
                    </select>
                  </label>
                )}
                <label>
                  理由（Page の下書きと監査ログに残ります）
                  <textarea value={why} onChange={(e) => setWhy(e.target.value)}
                            placeholder="例: 請求総額から販促値引と控除を引いた額を全社の売上とする。受注は着地見込みであって売上ではない。" />
                </label>
                <div className="btn-row">
                  <button className="btn btn-primary" disabled={busy || !canReview} onClick={submit}>
                    {busy ? '書き込み中…' : 'Lakebase に記録する'}
                  </button>
                  {!canReview && <span className="chip chip-warn">この権限がありません</span>}
                  {cur.decided_by && (
                    <span className="chip">
                      前回: {cur.decision} / {cur.decided_by} / {cur.decided_at?.slice(0, 16)}
                    </span>
                  )}
                </div>
                {note && <p className="empty" style={{ padding: '2px 0', color: 'var(--success)' }}>{note}</p>}
                {err && <p className="empty" style={{ padding: '2px 0', color: 'var(--danger)' }}>{err}</p>}
              </div>

              <div>
                <h3 style={{ fontSize: 'var(--t-micro)', letterSpacing: '0.1em',
                             color: 'var(--text-soft)', margin: '0 0 8px' }}>
                  この判断から機械的に導かれた学習ラベル
                </h3>
                <div className="labels">
                  <div className="label-card label-card-1">
                    <span className="k">本当の衝突（label = 1）</span>
                    <span className="v">{pos}</span>
                  </div>
                  <div className="label-card label-card-0">
                    <span className="k">衝突ではない（label = 0）</span>
                    <span className="v">{neg}</span>
                  </div>
                  {labels.map((l) => (
                    <div key={`${l.term_normalized}-${l.measure_name}-${l.label}`} className="label-card">
                      <span className="k">{l.term_normalized} / {l.measure_name}</span>
                      <span className="v">{l.label === 1 ? '1' : '0'} × {l.n}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
