export type Verdict = 'ok' | 'ng' | 'clarified' | null

export interface Question {
  id: string
  q: string
  conflict: boolean
  authoritative: string
  trap: string[]
  score_type: string
}

export interface Persona {
  id: string
  dept: string
  role: string
  name: string
  title: string
  asks: string
  space_id: string
  questions: Question[]
}

export interface Citation {
  ref: string
  comment: string | null
  certification: string | null
  department: string | null
}

export interface Answer {
  status: string | null
  text: string
  description: string
  sql: string
  refs: string[]
  result: { columns: string[]; rows: string[][]; note?: string } | null
  citations: Citation[]
}

export interface Candidate {
  candidate_id: number
  object_name: string
  object_type: string
  department: string | null
  measure_expr: string | null
  role: string
  observed_value: number | null
  note: string | null
}

export interface ConflictEvidence {
  summary?: string
  candidate_count?: number
  max_over_min?: number
  values?: Record<string, number>
  departments?: string[]
  detector?: string
}

export interface Conflict {
  conflict_id: number
  term: string
  term_normalized: string
  evidence: ConflictEvidence | null
  measure_name: string
  status: string
  ml_score: number | null
  detector_version: string | null
  detected_at: string | null
  decision: string | null
  authoritative_object: string | null
  rationale: string | null
  decided_by: string | null
  decided_at: string | null
  candidates: Candidate[]
}

export interface LabelRow {
  term_normalized: string
  measure_name: string
  label: number
  n: number
}

export interface Rate { k: number; n: number; pct: number | null }

export interface EvalSummary {
  label: string
  total: Rate
  source: Rate
  trap: Rate
  clarified: Rate
  wrong_direct: Rate
  conflict: Rate
  conflict_source: Rate
  by_dept: Record<string, Rate>
  by_type: Record<string, Rate>
}

export interface EvalSide {
  verdict: Verdict
  text: string
  sql: string
  refs: string[]
  numbers: number[]
}

export interface EvalItem {
  id: string
  dept: string
  persona: string
  conflict: boolean
  question: string
  authoritative: string
  before: EvalSide
  after: EvalSide
  truth: number[]
  flipped: boolean
}

export interface EvalCompare {
  before: EvalSummary | null
  after: EvalSummary | null
  items: EvalItem[]
}

export interface Me {
  email: string
  catalog: string
  spaces: Record<string, string>
  can_review: boolean
}
