import type { Citation } from '../types'
import { Chip } from './Chip'

/** 答えの根拠。どのオブジェクトから来たか、それは組織が認定したものか。 */
export function Citations({ items }: { items: Citation[] }) {
  if (!items.length) {
    return <p className="empty">引用元なし（SQL を生成せずに文章で答えています）。</p>
  }
  return (
    <div className="cites">
      {items.map((c) => (
        <div key={c.ref} className={`cite${c.certification === 'certified' ? ' cite-certified' : ''}`}>
          <div className="cite-head">
            <span className="cite-name">{c.ref}</span>
            {c.certification === 'certified'
              ? <Chip kind="cert">認定済み</Chip>
              : <Chip kind="off">未認定</Chip>}
            {c.department && <Chip>{c.department}</Chip>}
          </div>
          {c.comment && <div className="cite-comment">{c.comment}</div>}
        </div>
      ))}
    </div>
  )
}
