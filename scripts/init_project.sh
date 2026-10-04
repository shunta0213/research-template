#!/usr/bin/env bash
# テンプレートのコピーを，その場で新しい研究プロジェクトとして初期化する（使い方: scripts/README.md）。
#
#   scripts/init_project.sh                                          # 対話形式
#   scripts/init_project.sh [--name NAME] [--description TEXT] [--yes]
#
# GitHub の "Use this template" で作ったリポジトリを clone した直後に実行する。
# scripts/new_project.sh からも呼ばれる。テンプレート専用のファイル（このスクリプトと new_project.sh）と
# Markdown の見出しが「（テンプレート専用）」で終わる節は初期化時に削除される。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/_common.sh
source "$SCRIPT_DIR/_common.sh"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
  sed -n '3,4p' "$0" | sed 's/^# \{0,1\}//' >&2
  exit 2
}

NAME="$(basename "$ROOT")"
DESCRIPTION=""
YES=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) [[ $# -ge 2 ]] || usage; NAME="$2"; shift 2 ;;
    --description) [[ $# -ge 2 ]] || usage; DESCRIPTION="$2"; shift 2 ;;
    --yes) YES=true; shift ;;
    -h | --help) usage ;;
    *) usage ;;
  esac
done

cd "$ROOT"
grep -q '^name = "research-template"$' pyproject.toml || die "既に初期化済み（pyproject.toml の name が research-template ではない）"

if ! $YES; then
  interactive || die "対話形式で実行するか，--yes を付ける"
  echo "$ROOT を新しい研究プロジェクトとして初期化します（Ctrl-C で中止）"
  ask NAME "プロジェクト名" "$NAME"
  ask DESCRIPTION "プロジェクトの一行説明（空欄可）" "$DESCRIPTION"
  confirm "$ROOT を $NAME として初期化しますか" || die "中止した"
fi

[[ "$NAME" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || die "プロジェクト名に使えるのは英数字と . _ - のみ: $NAME"
[[ "$NAME" != "research-template" ]] || die "テンプレート自身は初期化しない（プロジェクト名を research-template 以外にする）"

# --- プロジェクト名・説明 ---
escape() { printf '%s' "$1" | sed -e 's/[|&\\]/\\&/g'; }
sed -i.bak "s|^name = \"research-template\"|name = \"$NAME\"|" pyproject.toml
if [[ -n "$DESCRIPTION" ]]; then
  sed -i.bak "s|^description = .*|description = \"$(escape "$DESCRIPTION")\"|" pyproject.toml
fi
sed -i.bak "1s|^# research-template$|# $NAME|" README.md
rm -f pyproject.toml.bak README.md.bak

# --- テンプレート専用の部分・ファイルを削除 ---
# 見出しが「（テンプレート専用）」で終わる ## 節を，次の # / ## 見出しの手前まで削除する（コードブロック内は見ない）
while IFS= read -r file; do
  awk '
    /^```/ { fence = !fence }
    !fence && /^## / { skip = ($0 ~ /（テンプレート専用）[[:space:]]*$/) }
    !fence && /^# / { skip = 0 }
    !skip { print }
  ' "$file" > "$file.tmp"
  mv "$file.tmp" "$file"
done < <(grep -rlE --include='*.md' --exclude-dir=.venv --exclude-dir=.git '^## .*（テンプレート専用）[[:space:]]*$' .)
rm -f scripts/new_project.sh scripts/init_project.sh # 実行中のこのスクリプトを消しても最後まで実行される

# --- 環境構築・テスト・コミット ---
[[ -d .git ]] || git init -q
uv sync
uv run pytest -q
git add -A
git commit -q -m "Initialize $NAME from research-template"

echo
echo "initialized $ROOT ($NAME)"
if git remote get-url origin > /dev/null 2>&1; then
  echo "  リモートに反映する: git push"
fi
