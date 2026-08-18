# multi-agent-workflow

Claude Code plugin: a design-only, permission-separated multi-agent development workflow — Claude Code as Implementation Owner, Codex as Independent Architect, an anonymous Design Judge, plus an opt-in Outcome Improvement Cycle with a deterministic read-only Gatekeeper — packaged so it can be installed into any project instead of copy-pasted.

このファイルおよびパッケージ内の各文書本文は日本語で記述する。ただし、ファイル名・ディレクトリ名・JSONキー・CLI名・プレースホルダー名・論理ロール名は英語のまま使用する。

## これは何か、何ではないか

- 独立した設計討論（Claude Codeの4 project subagents + Codex MCP）を、他プロジェクトへ`plugin install`一つで持ち込むためのパッケージである
- 進捗と各AIの提案を、追記専用JSONLログとHTMLダッシュボードで可視化する仕組みを含む
- **自動でファイルを上書き・merge・commitする機能は持たない。** 実装権限を持つのは常にImplementation Owner（導入先プロジェクトのユーザー自身が操作するClaude Codeセッション）のみで、他のロールはすべてread-only
- 実際の設計判断・commit・push・PR・mergeは、常にユーザーの明示指示に基づいて行われる。このプラグイン自体が判断を代行することはない

## インストール

```text
claude --plugin-dir /path/to/multi-agent-workflow
```

またはmarketplace経由での配布（`marketplace.json`を用意する場合）:

```text
/plugin install multi-agent-workflow@<marketplace-name>
```

インストール後、Skill/Agentはプラグイン名で名前空間化される:

- Skill: `/multi-agent-workflow:multi-agent-design [設計タスク]`、`/multi-agent-workflow:outcome-improvement-cycle [...]`、`/multi-agent-workflow:workflow-dashboard`
- Agent: `@multi-agent-workflow:claude-architect` など

Codex側のMCPサーバー（`.mcp.json`同梱）は、Claude Code再起動後に承認プロンプトが出る。承認手順は[`docs/agent-workflow/mcp-connection.md`](docs/agent-workflow/mcp-connection.md)を参照。

## 含まれるもの

```text
.claude-plugin/plugin.json     プラグインマニフェスト
agents/                        4つのClaude project subagents（read-only）
skills/
  multi-agent-design/          設計討論Skill（design-only）
  outcome-improvement-cycle/   Outcome Improvement Cycle Skill（opt-in）
  workflow-dashboard/          進捗・提案ログの記録とダッシュボード生成
.mcp.json                      Codex MCPサーバー設定
tools/
  outcome_gatekeeper.py        外部Evidence専用の決定論的read-onlyゲート
  render_dashboard.py          cycle-log JSONL → HTML ダッシュボード生成（read-only）
tests/                         上記2ツールのユニットテスト
examples/
  app-profiles/                App Profileのサンプル（example_only）
  cycle-logs/                  cycle-logのサンプル
docs/agent-workflow/           役割定義・レビュー手順・安全境界・トラブルシューティング
docs/decisions/                ADRテンプレート（導入先で採番してコピー）
```

## クイックスタート

1. このプラグインをインストールする
2. 導入先プロジェクトの`CLAUDE.md`/`AGENTS.md`相当のファイルへ、[`PROJECT_RULES_SNIPPET.md`](PROJECT_RULES_SNIPPET.md)を参考に、プロジェクト固有の制約（変更禁止ファイル・検証コマンド・既定ブランチ等）を追記する
3. `/multi-agent-workflow:multi-agent-design [設計タスク]` を明示的に起動する
4. 進捗・各AIの提案を追跡したい場合は`/multi-agent-workflow:workflow-dashboard`を使い、`docs/agent-workflow/cycle-log-schema.md`のイベントをログへ追記しながら進める。任意のタイミングで`python tools/render_dashboard.py <log>.jsonl`を実行すればダッシュボードが更新される

## 進捗・提案ダッシュボード

`tools/render_dashboard.py`は、`docs/agent-workflow/cycle-log-schema.md`で定義したJSONLログ（1サイクル1ファイル、追記専用）を読み、どの段階まで進んだか・各AIが何を提案したか・匿名評価の結果を1枚のHTMLにまとめる。ログファイル自体は一切書き換えない。サンプル:

```text
python tools/render_dashboard.py examples/cycle-logs/sample-cycle.jsonl
```

## 安全に関する設計判断

- 実装権限はImplementation Ownerのみ。他のロール（Requirements Auditor / Simplifier / Independent Architect / Design Judge）は`Read`/`Glob`/`Grep`のみで、ファイル変更・commit・push・PR・mergeはできない
- `tools/outcome_gatekeeper.py`はEvidence比較のみを行い、測定・Git操作・ネットワーク・書き込みは一切行わない
- `tools/render_dashboard.py`は入力ログを一切書き換えない読み取り専用ツール
- 詳細は[`docs/agent-workflow/review-protocol.md`](docs/agent-workflow/review-protocol.md)・[`docs/agent-workflow/git-safety.md`](docs/agent-workflow/git-safety.md)を参照

## 移行元について

このパッケージの大半のコンテンツは、単一リポジトリ内の手動コピー用テンプレート（`template/multi-agent-workflow/` v0.3.0）から移植した。主な変更点:

- 配置を`.claude/agents/`・`.claude/skills/`から、プラグイン規約に沿った`agents/`・`skills/`直下へ変更
- Skill/Agentの呼び出しが`multi-agent-workflow:`名前空間付きになった
- 旧テンプレートの`manifest.json`（SHA-256自己整合性検証）と`tools/verify_workflow_template.py`は、プラグイン配布モデル（gitコミット単位のバージョニング）に役割が置き換わるため移植していない
- 新規: `skills/workflow-dashboard/`、`tools/render_dashboard.py`、`docs/agent-workflow/cycle-log-schema.md`、`examples/cycle-logs/`

導入先プロジェクト固有の値（プロジェクト名・既定ブランチ・検証コマンド・変更禁止パス等）は、このプラグイン内には持たない。導入先プロジェクト自身のルール文書を参照する設計にしている。

## Known limitations

- Claude Codeプラグインとしての実機インストール検証（`claude --plugin-dir`での動作確認）はまだ行っていない
- `docs/agent-workflow/*`の一部の文書は、旧テンプレートからの移植時に機械的なパス置換＋部分的な手動修正で更新しており、全文の見直しは完了していない
- 異種モデルによる独立レビュー（heterogeneous review）は本パッケージ自体に対しては未実施
