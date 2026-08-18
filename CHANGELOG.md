# Changelog

## 0.1.0 (2026-08-19)

- 初版。`template/multi-agent-workflow/` v0.3.0の内容をClaude Codeプラグイン構造へ移植した
- 新規: `skills/workflow-dashboard/SKILL.md`、`tools/render_dashboard.py`、`docs/agent-workflow/cycle-log-schema.md`、`examples/cycle-logs/sample-cycle.jsonl` — 進捗・各AIの提案を可視化するHTMLダッシュボード機能
- `.claude/agents/` → `agents/`、`.claude/skills/` → `skills/`へ配置変更（プラグイン規約に合わせた）
- 導入先プロジェクト固有のプレースホルダー（`{{PROJECT_NAME}}`等）は、リテラルなプレースホルダー文字列としては持たず、導入先プロジェクト自身のルール文書を参照する記述へ書き換えた
- 旧テンプレートの`manifest.json`（SHA-256自己整合性検証）・`tools/verify_workflow_template.py`は移植していない（プラグインのバージョニングはgitコミット/`plugin.json`の`version`が担う）
- `tools/render_dashboard.py`に17件のユニットテストを追加（`tests/test_render_dashboard.py`）
- `tools/outcome_gatekeeper.py`とその既存ユニットテスト（`tests/test_outcome_gatekeeper.py`）を移植元から無改変で移植
- 未実施: Claude Codeプラグインとしての実機インストール検証、異種モデルによる独立レビュー
