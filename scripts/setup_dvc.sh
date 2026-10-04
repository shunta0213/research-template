#!/usr/bin/env bash
# DVC の remote（Google Drive，API 経由）を設定する（使い方: scripts/README.md）。
#
#   scripts/setup_dvc.sh                                                    # 対話形式
#   scripts/setup_dvc.sh --folder-id <FOLDER_ID> --key <KEY.json>           # サービスアカウント（推奨）
#   scripts/setup_dvc.sh --key <KEY.json>                                   # 2 台目以降（フォルダ ID 設定済み）
#   scripts/setup_dvc.sh --folder-id <FOLDER_ID> --client-id <ID> --client-secret <SECRET>   # OAuth
#
# 鍵はこのリポジトリの .secrets/（git 管理外）にコピーし，その場所と client secret は
# .dvc/config.local（git 管理外）に書く。フォルダ ID は .dvc/config（git 管理）に書く。
# 最後に Google Drive のフォルダに接続できるかを確認する。--folder-id には URL も渡せる。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=scripts/_common.sh
source "$SCRIPT_DIR/_common.sh"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
KEY_DEST=".secrets/gdrive-service-account.json"
PLACEHOLDER="REPLACE_WITH_GOOGLE_DRIVE_FOLDER_ID"

usage() {
  sed -n '3,7p' "$0" | sed 's/^# \{0,1\}//' >&2
  exit 2
}

FOLDER_ID=""
KEY=""
CLIENT_ID=""
CLIENT_SECRET=""
while [[ $# -gt 0 ]]; do
  [[ "$1" != "-h" && "$1" != "--help" && $# -ge 2 ]] || usage
  case "$1" in
    --folder-id) FOLDER_ID="$(folder_id_from "$2")" ;;
    --key) KEY="$2" ;;
    --client-id) CLIENT_ID="$2" ;;
    --client-secret) CLIENT_SECRET="$2" ;;
    *) usage ;;
  esac
  shift 2
done

cd "$ROOT"
[[ -d .git ]] || die "git リポジトリではない（DVC は git が前提）。先に git init する"
[[ -d .dvc ]] || die ".dvc/ が無い"
CURRENT_ID="$(sed -n 's|^ *url = gdrive://||p' .dvc/config | head -1)"
[[ "$CURRENT_ID" != "$PLACEHOLDER" ]] || CURRENT_ID=""

# --- 対話形式 ---
if [[ -z "$KEY" && -z "$CLIENT_ID" ]]; then
  interactive || usage
  echo "DVC の remote（Google Drive）を設定します（Ctrl-C で中止）。準備は docs/setup.md「4. データのアーカイブ」"
  echo
  ask FOLDER_ID "Google Drive のフォルダの URL または ID" "${FOLDER_ID:-$CURRENT_ID}"
  FOLDER_ID="$(folder_id_from "$FOLDER_ID")"
  echo "認証方法: 1) サービスアカウント（推奨。共有ドライブが必要）  2) 自前の OAuth クライアント（個人アカウント）"
  ask METHOD "番号" "1"
  case "$METHOD" in
    1)
      DEFAULT_KEY=""
      [[ ! -f "$KEY_DEST" ]] || DEFAULT_KEY="$KEY_DEST"
      ask KEY "サービスアカウントの鍵（JSON）のパス" "$DEFAULT_KEY"
      ;;
    2)
      ask CLIENT_ID "OAuth クライアント ID"
      ask_secret CLIENT_SECRET "OAuth クライアントシークレット（入力は表示されない）"
      ;;
    *) die "1 か 2 を選ぶ" ;;
  esac
  echo
fi
[[ -n "$KEY" || -n "$CLIENT_ID" ]] || usage
[[ -z "$KEY" || -z "$CLIENT_ID" ]] || die "--key と --client-id はどちらか一方だけ指定する"
[[ -z "$CLIENT_ID" || -n "$CLIENT_SECRET" ]] || die "--client-id には --client-secret も必要"
[[ -n "$FOLDER_ID" || -n "$CURRENT_ID" ]] || die "フォルダ ID が未設定。--folder-id を指定する"

# --- DVC（Google Drive 対応・pyOpenSSL を新しくしたもの）---
# dvc[gdrive] が引き込む pyOpenSSL 22.0 は新しい cryptography と組み合わせると import 時に落ちる
dvc_ok() {
  command -v dvc > /dev/null && "$(uv tool dir)/dvc/bin/python" -c "import OpenSSL, pydrive2" 2> /dev/null
}
if ! dvc_ok; then
  echo "[dvc] installing dvc[gdrive] (with pyopenssl>=24.2) as a uv tool"
  uv tool install -q --force "dvc[gdrive]" --with "pyopenssl>=24.2"
  dvc_ok || die "dvc をインストールしたが使えない（PATH に $(uv tool dir --bin) があるか確認する）"
fi
echo "[dvc] $(dvc --version) at $(command -v dvc)"

# --- フォルダ ID ---
if [[ -n "$FOLDER_ID" ]]; then
  dvc remote modify gdrive url "gdrive://$FOLDER_ID"
fi

# --- 認証情報 ---
if [[ -n "$KEY" ]]; then
  [[ -f "$KEY" ]] || die "鍵が見つからない: $KEY"
  mkdir -p .secrets
  chmod 700 .secrets
  if [[ "$(cd "$(dirname "$KEY")" && pwd)/$(basename "$KEY")" != "$ROOT/$KEY_DEST" ]]; then
    cp "$KEY" "$KEY_DEST"
  fi
  chmod 600 "$KEY_DEST"
  dvc remote modify gdrive gdrive_use_service_account true
  # 相対パスで渡すと .dvc/ からの相対パスで保存されるので，リポジトリを移動しても使える
  dvc remote modify --local gdrive gdrive_service_account_json_file_path "$KEY_DEST"
  echo "[dvc] service account key -> $KEY_DEST (git 管理外。ダウンロードした元の鍵は消してよい)"
else
  dvc remote modify gdrive gdrive_use_service_account false
  dvc remote modify gdrive gdrive_client_id "$CLIENT_ID"
  dvc remote modify --local gdrive gdrive_client_secret "$CLIENT_SECRET"
  echo "[dvc] OAuth client を設定した（初回の接続でブラウザでの認可が必要）"
fi

# --- 接続確認 ---
echo "[dvc] checking connection to $(dvc remote list | awk '$1 == "gdrive" {print $2}')"
dvc ls-url remote://gdrive > /dev/null ||
  die "Google Drive に接続できない（フォルダ ID，共有ドライブへのサービスアカウントの追加，鍵を確認する）"
echo "[dvc] OK"

if ! git diff --quiet -- .dvc/config; then
  echo
  echo ".dvc/config が変わったのでコミットする:"
  echo "  git commit -m \"Set DVC remote\" .dvc/config"
fi
