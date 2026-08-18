# Cycle log schema（進捗・提案ログ）

`review-protocol.md` の各フェーズを、後から `tools/render_dashboard.py` で可視化できるよう記録するための、追記専用JSONL形式。1サイクル（1つの設計討論の実行）につき1ファイル、`cycle_id` を軸に1イベント1行で追記する。

## 誰が書くか

**親のClaude Codeセッション（Orchestrator）自身**が、各フェーズの完了時にイベントを1行追記する。エージェント自身（claude-architect等）はこのログに書き込まない — read-onlyの原則（`review-protocol.md`「実装権限」）と一致させるため。

このログは**追記専用**（immutable）である。既存行の書き換え・削除は行わない。誤記録があった場合も、訂正イベントを新しい行として追記する（訂正対象の`event`名を`_correction`扱いにする等、運用は導入先で定める）。

## ファイル配置

導入先プロジェクトの任意の場所（例: `.agent-workflow/cycles/<cycle_id>.jsonl`）。このプラグイン自体は配置場所を強制しない。`.gitignore` するか記録として残すかは導入先プロジェクトの判断。

## 共通フィールド

すべての行に共通:

| フィールド | 型 | 必須 | 意味 |
|---|---|---|---|
| `cycle_id` | string | 必須 | このサイクルを一意に識別する文字列 |
| `ts` | string | 必須 | ISO 8601（例: `2026-08-19T10:41:00+09:00`） |
| `event` | string | 必須 | 下記イベント種別のいずれか |

## イベント種別

順序は`review-protocol.md`のフェーズ順に対応する。`round2_critique`のみ条件付き（第2ラウンドを実施しない場合、行自体を出力しない）。

### `task_input_recorded`

```json
{"cycle_id": "...", "ts": "...", "event": "task_input_recorded",
 "task": {"title": "...", "purpose": "...", "background": "...",
          "scope": "...", "out_of_scope": "...",
          "editable_files": ["..."], "protected_files": ["..."],
          "constraints": "...", "acceptance_criteria": "...",
          "verification_commands": "...",
          "implementation_allowed": true, "commit_push_pr_allowed": false}}
```

### `proposal_submitted`

独立提案者（最低2、`claude-architect`と`Independent Architect`）ごとに1行。

```json
{"cycle_id": "...", "ts": "...", "event": "proposal_submitted",
 "agent": "claude-architect", "model_alias": "sonnet",
 "title": "...", "summary": "...",
 "evidence": {"confirmed": 4, "inference": 2, "unknown": 1}}
```

`agent`は論理ロール名（`claude-architect` / `codex-independent-architect` / `codex-alternative-architect`）。`title`/`summary`はUI表示用の短い要約であり、提案全文はこのログとは別に保存してよい（`summary`に全文を書く必要はない）。

### `round1_critique` / `round2_critique`

```json
{"cycle_id": "...", "ts": "...", "event": "round1_critique",
 "status": "done", "critiques": [
   {"from_agent": "codex-independent-architect", "target_agent": "claude-architect", "summary": "..."},
   {"from_agent": "claude-architect", "target_agent": "codex-independent-architect", "summary": "..."}
 ]}
```

`status`は`"in_progress"`または`"done"`。`round2_critique`は「重大な未解決事項があり、新しい証拠または具体的な反証がある場合だけ」実施するため、実施しなかったサイクルではこのイベント自体を出力しない（`render_dashboard.py`はその場合、該当ステージを pending ではなく "skipped" として表示する）。

### `anonymous_evaluation`

```json
{"cycle_id": "...", "ts": "...", "event": "anonymous_evaluation",
 "scores": [
   {"label": "案1", "accuracy": 27, "evidence_strength": 18, "safety_scope": 19,
    "simplicity": 12, "testability_rollback": 13, "total": 89},
   {"label": "案2", "accuracy": 24, "evidence_strength": 16, "safety_scope": 15,
    "simplicity": 13, "testability_rollback": 12, "total": 80}
 ],
 "verdict": "..."}
```

配点は`review-protocol.md`「匿名評価」の基準（正確性30/根拠20/安全性と変更範囲の遵守20/単純さ15/テスト可能性・ロールバック性15）に対応する。`label`は`案1`/`案2`/`案3`のように匿名化した表記を使う（モデル名を含めない）。

### `integrated_design`

```json
{"cycle_id": "...", "ts": "...", "event": "integrated_design",
 "adopted_from": "案1", "summary": "...",
 "rejected": [{"label": "案2", "reason": "..."}],
 "user_approval_items": ["..."]}
```

### `implementation_gate`

```json
{"cycle_id": "...", "ts": "...", "event": "implementation_gate",
 "decision": "proceed", "reason": "..."}
```

`decision`は`"proceed"`または`"blocked"`。

## 表示側の責務との分離

このログは**事実の記録のみ**を担う。表示（ダッシュボードHTML生成）は`tools/render_dashboard.py`が読み取り専用で行い、ログファイル自体は一切書き換えない。CLIでの表示（`magent status`相当）を将来追加する場合も、同じログを読むだけの別ツールとして追加でき、ログ形式自体の変更は不要である。

サンプルデータ: [`../../examples/cycle-logs/sample-cycle.jsonl`](../../examples/cycle-logs/sample-cycle.jsonl)。
