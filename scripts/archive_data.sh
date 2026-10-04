#!/usr/bin/env bash
# data/ 以下の各サブディレクトリを archive/data-<日付>/ に圧縮スナップショットとして保存し，
# DVC が使えれば `dvc add` で追跡する（Google Drive への送信は `dvc push` を別途実行）。
# data/ に対しては読み取りのみ（tar で読むだけで，data/ 以下は変更・削除しない）。
# 要 zstd（docs/setup.md「前提」）。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA="${DATA_ROOT:-$ROOT/data}"
OUT="$ROOT/archive/data-$(date +%Y%m%d)"
mkdir -p "$OUT"

cd "$DATA"
for d in */; do
  d="${d%/}"
  dst="$OUT/$d.tar.zst"
  if [[ -e "$dst" ]]; then echo "skip (exists): $dst"; continue; fi
  echo "[$(date +%T)] archiving $d"
  tar -C "$DATA" -cf - "$d" | zstd -T0 -3 -q -o "$dst.partial"
  mv "$dst.partial" "$dst"

  # 検証: アーカイブ内のエントリ数 == ディスク上のエントリ数
  n_disk=$(find "$d" | wc -l)
  n_arc=$(zstd -dc "$dst" | tar -tf - | wc -l)
  if [[ "$n_disk" == "$n_arc" ]]; then
    echo "  OK  $d entries=$n_disk size=$(du -h "$dst" | cut -f1)"
  else
    echo "  MISMATCH $d disk=$n_disk archive=$n_arc" >&2
  fi
done

cd "$OUT"
shasum -a 256 ./*.tar.zst > SHA256SUMS
echo "[$(date +%T)] done -> $OUT"

cd "$ROOT"
if command -v dvc > /dev/null && [[ -d .dvc ]]; then
  dvc add "$OUT"
  name="archive/$(basename "$OUT")"
  echo
  echo "次の手順で Google Drive に送る:"
  echo "  git commit -m \"Archive data snapshot $(basename "$OUT")\" $name.dvc"
  echo "  dvc push $name.dvc"
else
  echo "dvc が見つからない（または .dvc/ が無い）ため dvc add をスキップした（docs/setup.md「4. データのアーカイブ」）"
fi
