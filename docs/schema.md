# DBスキーマ設計 (schema.md)

本ドキュメントは、Discord Economy Bot のデータを Raspberry Pi 上の SQLite で管理するためのスキーマを定義します。`core/sql_handler.py` の `init_db()` 関数が起動時に自動的にテーブルおよびカラムを作成・マイグレーションします。

**最終更新**: 2026-03-30 (v2.11: `jackpot_logs` テーブル追加)

---

## 1. `wallets` (ユーザー口座情報)

ユーザーの所持ポイント・デイリーボーナス・統計・ガチャ情報を管理します。

| カラム名 | 型 | 説明 |
| :--- | :--- | :--- |
| `user_id` | TEXT (PK) | Discord ユーザーID（`user_id=0` はシステム/ジャックポットアカウント） |
| `balance` | INTEGER | 現在の所持ポイント（初期値: `10000`、システム口座は `0`） |
| `last_daily` | TEXT | デイリーボーナスを最後に受け取った日付 (`YYYY-MM-DD`、JST) |
| `last_gacha_daily` | TEXT | ガチャを最後に実行した日付 (`YYYY-MM-DD`、JST)。当日リセット管理用 |
| `gacha_count_today` | INTEGER | 当日のガチャ実行回数（最大3回。JST 0:00 にリセット） |
| `gacha_collection` | TEXT (JSON) | 過去に引いたガチャイベントIDのリスト（JSON配列形式） |
| `total_wins` | INTEGER | 累計ゲーム勝利数 |
| `games_played` | INTEGER | 累計ゲーム参加数 |
| `max_win_amount` | INTEGER | 一発勝負の最大獲得ポイント（最大一撃記録） |
| `history` | TEXT (JSON) | 直近のポイント取引履歴リスト（JSON配列形式） |
| `updated_at` | TEXT | 最終更新日時（ISO 8601 形式、JST） |

### 🚀 アクセスパターン

- **残高照会**: `SELECT * FROM wallets WHERE user_id = ?`
- **残高更新**: `ON CONFLICT(user_id) DO UPDATE SET ...`（Upsert）
- **全体ランキング**: `SELECT * FROM wallets WHERE user_id != '0' ORDER BY balance DESC`

---

## 2. `game_sessions` (ゲーム進行状態)

Bot 再起動時にも現在のゲームを復旧・継続できるよう、進行中のゲーム情報を DB に保存します。

| カラム名 | 型 | 説明 |
| :--- | :--- | :--- |
| `channel_id` | TEXT (PK) | ゲームが行われているチャンネルの Discord ID |
| `game_type` | TEXT | `chinchiro` / `blackjack` / `match` など |
| `status` | TEXT | `recruiting` / `playing` / `settled` / `cancelled` |
| `host_id` | TEXT | 募集者の Discord ユーザーID |
| `bet_amount` | INTEGER | 参加に必要な賭け金 |
| `pot` | INTEGER | 現在のプール金合計 |
| `session_data` | TEXT (JSON) | 参加プレイヤーリスト・現在ターン・ゲーム固有の進行状態を保持する JSON |

### 🚀 アクセスパターン

- **セッション取得**: `SELECT session_data FROM game_sessions WHERE channel_id = ?`
- **セッション作成/更新**: `INSERT ... ON CONFLICT(channel_id) DO UPDATE ...`（Upsert）
- **セッション終了**: `DELETE FROM game_sessions WHERE channel_id = ?`

---

## マイグレーション方式

`sql_handler.py` の `init_db()` が `PRAGMA table_info(wallets)` を使って既存カラムを確認し、不足カラムがあれば `ALTER TABLE ... ADD COLUMN` で自動追加します。これにより、既存 DB を壊さずに新機能追加が可能です。

1. **Phase 1（完了）**: `WalletManager` / `GameManager` からのデータ保存を `IStorage` インターフェース経由に切り離しリアーキテクチャ。
2. **Phase 2（完了）**: `SQLiteStorage` および `sql_handler.py` による CRUD 処理を実装し、 Raspberry Pi 上での運用開始。
3. **Phase 3（完了）**: `jackpot_logs` テーブルを追加し、ジャックポット放出履歴の監査パスを確立 (v2.11)。
