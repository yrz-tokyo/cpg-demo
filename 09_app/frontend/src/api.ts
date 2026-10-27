import type { Answer, Conflict, EvalCompare, LabelRow, Me, Persona } from './types'

async function get<T>(path: string): Promise<T> {
  const r = await fetch(path)
  if (!r.ok) throw new Error(`${r.status} ${await r.text()}`)
  return r.json() as Promise<T>
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(path, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) {
    const t = await r.text()
    try { throw new Error(JSON.parse(t).detail ?? t) } catch { throw new Error(t) }
  }
  return r.json() as Promise<T>
}

export const api = {
  me: () => get<Me>('/api/me'),
  personas: () => get<{ personas: Persona[] }>('/api/personas'),
  ask: (persona_id: string, question: string) =>
    post<Answer>('/api/ask', { persona_id, question }),
  conflicts: () => get<{ conflicts: Conflict[]; labels: LabelRow[] }>('/api/conflicts'),
  decide: (body: {
    conflict_id: number
    decision: string
    authoritative_object?: string | null
    rationale?: string
    term?: string
  }) => post<{ conflict_id: number; decision: string; labels: LabelRow[] }>('/api/decide', body),
  evalCompare: () => get<EvalCompare>('/api/eval'),
}
