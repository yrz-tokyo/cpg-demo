import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import type { Answer, Persona, Question } from '../types'
import { Chip } from './Chip'
import { Citations } from './Citations'
import { Path } from './Path'

const DEPTS = ['営業', '財務', 'マーケ']

export function PersonaScreen() {
  const [personas, setPersonas] = useState<Persona[]>([])
  const [pid, setPid] = useState<string | null>(null)
  const [q, setQ] = useState<Question | null>(null)
  const [answer, setAnswer] = useState<Answer | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    api.personas()
      .then((d) => { setPersonas(d.personas); setPid(d.personas[0]?.id ?? null) })
      .catch((e) => setErr(String(e)))
  }, [])

  const persona = useMemo(() => personas.find((p) => p.id === pid) ?? null, [personas, pid])

  async function ask(question: Question) {
    setQ(question); setAnswer(null); setErr(null); setBusy(true)
    try {
      setAnswer(await api.ask(persona!.id, question.q))
    } catch (e) {
      setErr(String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ display: 'grid', gridTemplateRows: 'minmax(0,1fr) auto', gap: 14, minHeight: 0 }}>
      <div className="cols cols-37">
        <div className="panel">
          <div className="panel-head">
            <h2>だれが聞くか</h2>
            <span className="hint">3部門 × 部長・現場</span>
          </div>
          <div className="panel-body-flush">
            {DEPTS.map((d) => (
              <div className="persona-group" key={d}>
                <div className="dept">{d}</div>
                {personas.filter((p) => p.dept === d).map((p) => (
                  <button key={p.id} className="persona" aria-current={p.id === pid}
                          onClick={() => { setPid(p.id); setQ(null); setAnswer(null) }}>
                    <span className="name">{p.name}</span>
                    <span className="role">{p.title}</span>
                  </button>
                ))}
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <h2>{persona ? `${persona.name} が聞くこと` : '問い'}</h2>
            <span className="hint">{persona?.asks}</span>
          </div>
          <div className="panel-body">
            {!persona && <p className="empty">読み込み中…</p>}
            {persona && (
              <div className="cols cols-46" style={{ alignItems: 'start' }}>
                <div className="qlist">
                  {persona.questions.map((x) => (
                    <button key={x.id} className="q" aria-current={x.id === q?.id}
                            disabled={busy} onClick={() => ask(x)}>
                      <span className="text">{x.q}</span>
                      <span className="meta">
                        <span className="q-id">{x.id}</span>
                        {x.conflict && <Chip kind="trap">定義が割れる問い</Chip>}
                      </span>
                    </button>
                  ))}
                </div>

                <div className="answer">
                  {err && <p className="empty">エラー: {err}</p>}
                  {busy && <p className="empty">Genie One に照会しています…</p>}
                  {!busy && !answer && !err && (
                    <p className="empty">左の問いを押すと、回答と引用元が出ます。</p>
                  )}
                  {answer && (
                    <>
                      <div className="answer-text">{answer.text || '（文章の回答なし）'}</div>
                      <Citations items={answer.citations} />
                      {answer.sql && <pre className="sql">{answer.sql}</pre>}
                    </>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <Path persona={persona} question={q?.q ?? null} answer={answer} busy={busy} />
    </div>
  )
}
