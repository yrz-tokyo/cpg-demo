import type { Verdict as V } from '../types'

const LABEL: Record<string, string> = {
  ok: '正解', ng: '不正解', clarified: '聞き返し',
}

/** 統治前に聞き返すのは不正解ではない。別の状態として扱う。 */
export function Verdict({ v }: { v: V }) {
  if (!v) return <span className="verdict verdict-none">未実施</span>
  const cls = v === 'ok' ? 'ok' : v === 'ng' ? 'ng' : 'clar'
  return <span className={`verdict verdict-${cls}`}>{LABEL[v]}</span>
}
