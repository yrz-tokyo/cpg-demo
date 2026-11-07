#!/usr/bin/env bash
# deck.html → deck.pdf（16:9・15枚）。WeasyPrint はこの Mac に入れられない
# （pypi が Jamf 管理のポリシーでブロック）ため、Chrome のヘッドレスで書き出す。
#
# 書き出した後は必ずテキスト抽出を確認する。採点AIはテキストを読むので、
# 「綺麗だが読めない PDF」が最悪のケースになる。
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$HERE/deck.pdf" "file://$HERE/deck.html" 2>/dev/null

pdftotext -layout "$HERE/deck.pdf" "$HERE/deck_extracted.txt"
# mdls は Spotlight のキャッシュを返し、上書き直後は古い値が出る。pdfinfo を使う。
pdfinfo "$HERE/deck.pdf" | grep -E "^Pages|^Page size"
echo "抽出:     $(wc -c < "$HERE/deck_extracted.txt") バイト"
