# multi-agent-workflow

Claude Code plugin: a design-only, permission-separated multi-agent development workflow — Claude Code as Implementation Owner, Codex as Independent Architect, an anonymous Design Judge, plus an opt-in Outcome Improvement Cycle with a deterministic read-only Gatekeeper — packaged so it can be installed into any project instead of copy-pasted.

このファイルおよびパッケージ内の各文書本文は日本語で記述する。ただし、ファイル名・ディレクトリ名・JSONキー・CLI名・プレースホルダー名・論理ロール名は英語のまま使用する。

## これは何か、何ではないか

- 独立した設計討論（Claude Codeの4 project subagents + Codex MCP）を、他プロジェクトへ`plugin install`一つで持ち込むためのパッケージである
- 進捗と各AIの提案を、追記専用JSONLログとHTMLダッシュボードで可視化する仕組みを含む
- **自動でファイルを上書き・merge・commitする機能は持たない。** 実装権限を持つのは常にImplementation Owner（導入先プロジェクトのユーザー自身が操作するClaude Codeセッション）のみで、他のロールはすべてread-only
- 実際の設計判断・commit・push・PR・mergeは、常にユーザーの明示指示に基づいて行われる。このプラグイン自体が判断を代行することはない

## 他AIへの技術ブリーフィング

このセクションだけを読めば、他のAI（別セッション・別ツールのAI）にこのリポジトリの仕組みを一通り説明できるよう、要点を集約している。各項目の完全版は末尾のリンク先を参照。

### 役割（論理ロール）と実行主体

| 論理ロール | 実行主体 | model alias | 権限 |
|---|---|---|---|
| Requirements Auditor | `agents/requirements-auditor.md` | haiku | read-only |
| Simplifier | `agents/simplifier.md` | haiku | read-only |
| Main/Primary Architect | `agents/claude-architect.md` | sonnet | read-only（設計案作成のみ、実装しない） |
| Independent Architect | Codex（`.mcp.json`の`codex-reviewer`経由） | - | read-only |
| Design Judge / Integrator | `agents/design-judge.md` | opus | read-only（匿名評価と統合設計の作成のみ） |
| Implementation Owner | 親のClaude Codeセッション自身 | - | **編集権限を持つのはこのロールのみ** |

Alternative Architect・Red Team Reviewer・Final Auditorは、重大な対立時やユーザー指定時のみ追加される任意ロール。full model IDはどこにもハードコードしない（aliasのみ使用）。

### フェーズの流れ（`docs/agent-workflow/review-protocol.md`）

1. **タスク入力の明示化** — 目的・背景・対象範囲・対象外・変更可能/禁止ファイル・制約・受入条件・検証コマンド・実装可否・commit/push/PR可否。不足項目は勝手に補完せず`Unknown`として報告する
2. **独立提案** — Main ArchitectとIndependent Architectが、互いの案を見ずにそれぞれ設計案を作成する
3. **Round 1**（相互批評・Red Teamレビュー・反論と修正版）
4. **Round 2**（**条件付き** — 重大な未解決事項があり、新しい証拠か具体的な反証がある場合のみ。同じ主張の繰り返しは禁止）
5. **匿名評価** — モデル名を伏せて「案1」「案2」として、正確性30/根拠の強さ20/安全性と変更範囲の遵守20/単純さ・保守性15/テスト可能性・ロールバック性15の100点満点でDesign Judgeが評価する
6. **統合設計** — Design Judgeが採用案・不採用理由・対象ファイル・変更順序・テスト計画・ロールバック方法・ユーザー承認が必要な事項をまとめる
7. **ユーザー承認** → **実装**（Implementation Ownerのみ、承認済みの統合設計から逸脱しない）

証拠は常に **Confirmed / Inference / Unknown** で分類する。実行していないテストを「成功」と書くことは禁止。

opt-inの**Outcome Improvement Cycle**（`skills/outcome-improvement-cycle/SKILL.md`）は、外部Evidence（実際の勝率測定等）を`tools/outcome_gatekeeper.py`（決定論的・read-only・標準ライブラリのみ）で評価する、上記フローの拡張。App Profile契約は`docs/agent-workflow/app-profile.md`を参照。

### 進捗・提案の可視化（`docs/agent-workflow/cycle-log-schema.md`）

親セッションが、各フェーズの完了時に追記専用JSONLへ1行ずつ記録する（`task_input_recorded` / `proposal_submitted` / `round1_critique` / `round2_critique` / `anonymous_evaluation` / `integrated_design` / `implementation_gate`）。エージェント自身はログに書き込まない。`python tools/render_dashboard.py <log>.jsonl`でHTMLダッシュボードを生成できる（ログは一切書き換えない読み取り専用）。

### 安全境界（`docs/agent-workflow/git-safety.md`）

- 実装権限はImplementation Ownerのみ。他ロールは`Read`/`Glob`/`Grep`のみで、ファイル変更・commit・push・PR・mergeは一切できない
- 自動commit・auto-mergeを行わない。push/PR/mergeは常にユーザーの明示指示が必要
- `git add .`を使わない、未コミット変更を破棄しない、入れ子のGitリポジトリを作らない
- このプラグイン自体（`tools/`配下）も、書き込み・subprocess・ネットワークアクセスを行わない読み取り専用ツールのみで構成されている

### 詳細を読む場合

`docs/agent-workflow/README.md`が全文書への入口。特に`review-protocol.md`（レビュー手順）、`subagents.md`（4エージェントの定義方法）、`multi-agent-design-skill.md`（Skillのオーケストレーション手順）、`mcp-connection.md`（Codex接続）、`troubleshooting.md`を参照。

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
