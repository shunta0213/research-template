#!/usr/bin/env bash
# archive/data-<日付>/ のスナップショットを data/ に展開する。
# スナップショットが手元に無ければ `dvc pull` で Google Drive から取ってくる。
# data/ に同名のディレクトリが既にあるものは上書きせずスキップする。
#
#   scripts/restore_data.sh data-20261004            # 全サブディレクトリ
#   scripts/restore_data.sh data-20261004 runs       # runs だけ
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <data-YYYYMMDD> [subdir ...]" >&2
  exit 2
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATA="${DATA_ROOT:-$ROOT/data}"
SNAPSHOT="$ROOT/archive/$1"
shift

cd "$ROOT"
if [[ ! -d "$SNAPSHOT" ]]; then
  echo "[$(date +%T)] dvc pull archive/$(basename "$SNAPSHOT").dvc"
  dvc pull "archive/$(basename "$SNAPSHOT").dvc"
fi

cd "$SNAPSHOT"
shasum -a 256 -c SHA256SUMS

if [[ $# -gt 0 ]]; then
  archives=("${@/%/.tar.zst}")
else
  archives=(*.tar.zst)
fi

mkdir -p "$DATA"
for a in "${archives[@]}"; do
  d="${a%.tar.zst}"
  if [[ -e "$DATA/$d" ]]; then echo "skip (exists): $DATA/$d"; continue; fi
  echo "[$(date +%T)] restoring $d"
  zstd -dc "$a" | tar -C "$DATA" -xf -
done
echo "[$(date +%T)] done -> $DATA"
