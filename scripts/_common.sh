# scripts/*.sh から source する共通ヘルパー（単体では実行しない）。

die() {
  echo "error: $*" >&2
  exit 1
}

# 標準入力が端末のとき（対話形式で質問できるとき）真
interactive() {
  [[ -t 0 ]]
}

# ask <変数名> <質問> [既定値]: 質問して答えを変数に入れる（空欄なら既定値。先頭の ~ はホームに展開）
ask() {
  local __var="$1" __prompt="$2" __default="${3:-}" __answer
  if [[ -n "$__default" ]]; then
    read -r -p "$__prompt [$__default]: " __answer
  else
    read -r -p "$__prompt: " __answer
  fi
  __answer="${__answer:-$__default}"
  __answer="${__answer/#\~/$HOME}"
  printf -v "$__var" '%s' "$__answer"
}

# ask_secret <変数名> <質問>: 入力を画面に出さずに質問する
ask_secret() {
  local __var="$1" __prompt="$2" __answer
  read -r -s -p "$__prompt: " __answer
  echo
  printf -v "$__var" '%s' "$__answer"
}

# confirm <質問>: y/N で確認する（y なら真）
confirm() {
  local answer
  read -r -p "$1 [y/N]: " answer
  [[ "$answer" =~ ^[Yy] ]]
}

# Google Drive のフォルダ URL（https://drive.google.com/drive/folders/<ID>?...）からも ID を取り出す
folder_id_from() {
  local id="${1##*folders/}"
  printf '%s' "${id%%[?/]*}"
}
