import type { ReactNode } from 'react'

/** 状態は色だけで区別しない。必ず文字でも書く。 */
export function Chip({ kind, mono, children }: {
  kind?: 'on' | 'off' | 'cert' | 'warn' | 'trap'
  mono?: boolean
  children: ReactNode
}) {
  const cls = ['chip', kind ? `chip-${kind}` : '', mono ? 'chip-mono' : '']
    .filter(Boolean).join(' ')
  return <span className={cls}>{children}</span>
}
