#!/usr/bin/env bash
# research-template から新しい研究プロジェクトを作る（使い方: scripts/README.md）。
#
#   bash <(curl -fsSL https://raw.githubusercontent.com/shunta0213/research-template/main/scripts/new_project.sh)
#   scripts/new_project.sh                                               # 対話形式
#   scripts/new_project.sh <作成先> [--description TEXT] [--folder-id ID --key KEY.json] [--github OWNER [--public]]
#
# テンプレートを作成先にコピーし（.venv・データ・キャッシュ・秘密情報は除く），作成先で
# scripts/init_project.sh（名前の書き換え → uv sync → pytest → 最初のコミット）を実行する。
# --folder-id と --key を指定すると scripts/setup_dvc.sh も，--github を指定すると GitHub への
# リポジトリ作成と push も行う（対話形式では質問に答える）。
# curl で取ってきて実行したとき（テンプレートの外から実行したとき）は，テンプレートを git clone してから行う。
set -euo pipefail

TEMPLATE_REPO="${RESEARCH_TEMPLATE_REPO:-https://github.com/shunta0213/research-template.git}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" && pwd)"

# --- テンプレートの外から実行されたとき: テンプレートを clone して，その中の new_project.sh を実行し直す ---
if [[ ! -f "$SCRIPT_DIR/_common.sh" ]]; then
  command -v git > /dev/null || { echo "error: git が必要" >&2; exit 1; }
  workdir="$(mktemp -d)"
  trap 'rm -rf "$workdir"' EXIT
  echo "[new_project] downloading template: $TEMPLATE_REPO"
  git clone -q --depth 1 "$TEMPLATE_REPO" "$workdir/research-template"
  if [[ -t 0 || $# -gt 0 ]]; then
    "$workdir/research-template/scripts/new_project.sh" "$@"
  else
    # curl ... | bash のときは標準入力がスクリプト本体なので，質問の答えは端末から読む
    "$workdir/research-template/scripts/new_project.sh" < /dev/tty
  fi
  exit
fi

# shellcheck source=scripts/_common.sh
source "$SCRIPT_DIR/_common.sh"
TEMPLATE="$(cd "$SCRIPT_DIR/.." && pwd)"

usage() {
  sed -n '4,6p' "$0" | sed 's/^# \{0,1\}//' >&2
  exit 2
}

DEST=""
DESCRIPTION=""
FOLDER_ID=""
KEY=""
GITHUB_OWNER=""
GITHUB_VISIBILITY="private"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --description) [[ $# -ge 2 ]] || usage; DESCRIPTION="$2"; shift 2 ;;
    --folder-id) [[ $# -ge 2 ]] || usage; FOLDER_ID="$(folder_id_from "$2")"; shift 2 ;;
    --key) [[ $# -ge 2 ]] || usage; KEY="$2"; shift 2 ;;
    --github) [[ $# -ge 2 ]] || usage; GITHUB_OWNER="$2"; shift 2 ;;
    --public) GITHUB_VISIBILITY="public"; shift ;;
    -h | --help) usage ;;
    -*) usage ;;
    *) [[ -z "$DEST" ]] || usage; DEST="$1"; shift ;;
  esac
done

gh_ready() {
  command -v gh > /dev/null && gh auth status > /dev/null 2>&1
}

# --- 対話形式 ---
if [[ -z "$DEST" ]]; then
  interactive || usage
  echo "research-template から新しい研究プロジェクトを作ります（Ctrl-C で中止）"
  echo
  ask DEST "作成先ディレクトリ（ディレクトリ名がプロジェクト名になる。例: ~/research/my-study）"
  ask DESCRIPTION "プロジェクトの一行説明（空欄可）"
  echo
  echo "DVC（データのスナップショットを Google Drive に保存）の設定には，Google Drive のフォルダと"
  echo "サービスアカウントの鍵が必要（docs/setup.md「4. データのアーカイブ」）。後から scripts/setup_dvc.sh でも設定できる。"
  if confirm "続けて DVC の設定もしますか"; then
    ask FOLDER_ID "Google Drive のフォルダの URL または ID"
    FOLDER_ID="$(folder_id_from "$FOLDER_ID")"
    ask KEY "サービスアカウントの鍵（JSON）のパス"
  fi
  echo
  if gh_ready; then
    if confirm "GitHub にこのプロジェクトのリポジトリを作って push しますか"; then
      ask GITHUB_OWNER "GitHub のアカウントまたは organization" "$(gh api user --jq .login)"
      if confirm "public にしますか（N なら private）"; then GITHUB_VISIBILITY="public"; fi
    fi
  else
    echo "（gh が無いかログインしていないので，GitHub へのリポジトリ作成はスキップする。後から gh repo create で作れる）"
  fi
  echo
fi

# --- 入力の確認（ここまででは何も作らない） ---
[[ -n "$DEST" ]] || die "作成先が空"
if [[ -n "$FOLDER_ID" && -z "$KEY" ]] || [[ -z "$FOLDER_ID" && -n "$KEY" ]]; then
  die "--folder-id と --key は両方指定する"
fi
[[ -z "$KEY" || -f "$KEY" ]] || die "鍵が見つからない: $KEY"
[[ -z "$KEY" ]] || KEY="$(cd "$(dirname "$KEY")" && pwd)/$(basename "$KEY")"

NAME="$(basename "$DEST")"
[[ "$NAME" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || die "プロジェクト名（ディレクトリ名）に使えるのは英数字と . _ - のみ: $NAME"
[[ ! -e "$DEST" ]] || die "$DEST は既に存在する"
if [[ -n "$GITHUB_OWNER" ]]; then
  gh_ready || die "GitHub にリポジトリを作るには gh にログインしておく（gh auth login）"
  ! gh repo view "$GITHUB_OWNER/$NAME" > /dev/null 2>&1 || die "GitHub に $GITHUB_OWNER/$NAME が既に存在する"
fi
mkdir -p "$(dirname "$DEST")"
DEST="$(cd "$(dirname "$DEST")" && pwd)/$NAME"
[[ "$DEST" != "$TEMPLATE"/* ]] || die "テンプレートの中には作れない: $DEST"

# --- コピー（生成物・データ・秘密情報・このスクリプト自身は除く） ---
mkdir -p "$DEST"
rsync -a \
  --exclude .git --exclude .venv --exclude __pycache__ --exclude .DS_Store \
  --exclude .pytest_cache --exclude .ruff_cache --exclude htmlcov --exclude .coverage \
  --exclude .secrets --exclude /.dvc/config.local --exclude /.dvc/cache --exclude /.dvc/tmp \
  --include /data/README.md --exclude '/data/*' \
  --include /cache/.gitkeep --exclude '/cache/*' \
  --include /tmp/.gitkeep --exclude '/tmp/*' \
  --exclude '/archive/data-*' \
  --exclude /scripts/new_project.sh \
  "$TEMPLATE/" "$DEST/"
echo "[new_project] copied template -> $DEST"

# --- 初期化（名前の書き換え → uv sync → pytest → 最初のコミット） ---
"$DEST/scripts/init_project.sh" --name "$NAME" --description "$DESCRIPTION" --yes

# --- DVC ---
DVC_DONE=false
if [[ -n "$FOLDER_ID" ]]; then
  if (cd "$DEST" && scripts/setup_dvc.sh --folder-id "$FOLDER_ID" --key "$KEY"); then
    git -C "$DEST" commit -q -m "Set DVC remote" .dvc/config
    DVC_DONE=true
    echo "[new_project] DVC の設定をコミットした"
  else
    echo "warning: DVC の設定に失敗した。原因を直してから $DEST で scripts/setup_dvc.sh を実行する" >&2
  fi
fi

# --- GitHub ---
GITHUB_URL=""
if [[ -n "$GITHUB_OWNER" ]]; then
  gh_args=("$GITHUB_OWNER/$NAME" "--$GITHUB_VISIBILITY" --source "$DEST" --remote origin --push)
  [[ -z "$DESCRIPTION" ]] || gh_args+=(--description "$DESCRIPTION")
  if gh repo create "${gh_args[@]}"; then
    GITHUB_URL="https://github.com/$GITHUB_OWNER/$NAME"
  else
    echo "warning: GitHub へのリポジトリ作成に失敗した。$DEST で gh repo create を実行する" >&2
  fi
fi

echo
echo "できたプロジェクト: $DEST"
[[ -z "$GITHUB_URL" ]] || echo "GitHub: $GITHUB_URL ($GITHUB_VISIBILITY)"
echo
echo "次にやること（docs/setup.md）:"
echo "  cd $DEST"
$DVC_DONE || echo "  scripts/setup_dvc.sh                 # DVC（Google Drive）の設定（対話形式）"
echo "  README.md の概要を自分の研究の説明に書き換える"
