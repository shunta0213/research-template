@AGENTS.md

## Claude Code

- 共通の指示は上の `AGENTS.md`。ここには Claude Code 固有のことだけを書く
- スキル（`.claude/skills/`）:
  - `/new-experiment`: 新しい実験（`src/`・`experiments/`・`analysis/`・テスト・`docs/experiments-io.md`）を追加する
  - `/research-note`: 今日の研究ノート（`notes/YYYY-MM-DD.md`）を作る・追記する
- `.claude/settings.json` で `.secrets/` などの読み取りを禁止し，push・投入系のコマンドは毎回確認するよう設定している
