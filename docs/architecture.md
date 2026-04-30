# アーキテクチャ概要 (architecture.md)

> **最終更新**: 2026-05-01  
> *v2.2 モノリシックServiceの完全分解と画像アセット動的合成の実装*

---

## 1. ディレクトリ構造

システムの詳細なディレクトリ構造については、別ファイル [directory_structure.md](file:///d:/python_project/Discord_eco_system/docs/directory_structure.md) を参照してください。

### プロジェクト構成の概要

- **`main.py`**: エントリポイント
- **`core/`**: システム基盤（DBハンドラ、バリデーション、UI共通部品）
- **`cogs/`**: Discord Bot の機能拡張（コマンド定義）
- **`logic/`**: ゲームエンジンおよびビジネスロジック
- **`managers/`**: ステートレスなセッション管理
- **`tests/`**: 自動テストスイート
- **`docs/`**: システム仕様書・設計ドキュメント

---

## 2. レイヤー構造と責務

```
┌─────────────────────────────────────────────────────┐
│  Presentation Layer（プレゼンテーション層）              │
│  cogs/ — コマンド定義 / main.py — 起動・拡張管理         │
└──────────────────────┬──────────────────────────────┘
                       │ 委譲
┌──────────────────────▼──────────────────────────────┐
│  Session Management Layer（セッション管理層）            │
│  managers/manager.py    — チャンネル別セッション一元管理  │
│  managers/game_session.py — BaseGameSession 基底クラス │
│  core/ui/starter.py     — ゲーム開始時のUI制御           │
└──────┬──────────────────────┬───────────────────────┘
       │ ゲームロジック         │ 経済ルール
┌──────▼──────────┐  ┌────────▼──────────────────────┐
│  Game Engines   │  │  Economy Facade               │
│  logic/blackjack│  │  logic/bet_service.py (BetSvc)│
│  logic/chinchiro│  └────────┬──────────────────────┘
│  logic/poker    │           │ 専門サービスへ委譲
│  logic/dobumon  │  ┌────────▼──────────────────────┐
│  logic/match_   │  │  logic/economy/               │
│  service.py     │  │  provider.py  / bonus.py      │
└──────┬──────────┘  │  jackpot.py   / status.py     │
       │             │  game_logic.py                │
       └─────────────┴────────┬──────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────┐
│  Data Access Layer（データアクセス層）                  │
│  core/economy.py    — WalletManager（残高操作窓口）    │
│  core/handlers/     — SQL CRUD / Storage実体         │
│  core/models/       — Pydanticバリデーション          │
│  core/utils/        — Logger / Config / Exceptions  │
│  data/               — SQLite DB本体 (環境別)          │
└─────────────────────────────────────────────────────┘
```

---

## 3. 各コンポーネントの役割

### main.py（プレゼンテーション層）
- `EconomyBot` クラスとして定義された Discord Bot の起動スクリプト。
- `setup_hook()` で `cogs/` 下の拡張機能を読み込み、スラッシュコマンドを同期する。
- `bot.maintenance_mode` フラグを保持し、`@check_maintenance` デコレータから参照される。

### cogs/（拡張機能層）
`discord.ext.commands.Cog` を継承したクラス群。各カテゴリのコマンドをモジュール化して管理。

- **`economy.py`** — ユーザー向けの経済操作コマンド全般。
- **`admin.py`** — 開発者・サーバー管理者向けの特権操作コマンド。
- **`games.py`** — 各種ゲームの開始エントリポイント（blackjack, chinchiro, poker, gacha等）。
- **`dobumon.py`** — 怒武者のステータス確認、トレーニング、決闘などのコマンド。
- **`system.py`** — グローバルエラーハンドラおよびシステムユーティリティ。

> [!TIP]
> **Context Menu の実装パターン**  
> `discord.py` の仕様により、Cog 内のメソッドに対して `@app_commands.context_menu` デコレータを直接使うことはできません。Cog 内でコンテキストメニューを実装する場合は、`__init__` 内で `app_commands.ContextMenu` を明示的にインスタンス化し、`self.bot.tree.add_command(self.ctx_menu)` で登録する必要があります。

### core/ui/（UI共通コンポーネント）
- **`view_base.py`** — `DobumonBaseView`: `interaction_check` による認可チェックを内包した全Viewの基底クラス。
- **`starter.py`** — `execute_game_start()`: `JoinView` の「開始」ボタン押下後に呼ばれる。セッションの型（Blackjack/Chinchiro/Poker/Match）を判別し、各ゲームのViewを生成・表示する。

### managers/（セッション管理）
- **`manager.py`** — `GameManager` クラス。各チャンネルのゲームセッションの一元管理。同チャンネルでの二重起動を防止し、DBを経由したステートレス設計を実現。`create_blackjack()` / `create_chinchiro()` / `create_poker()` / `create_match()` でゲーム別セッションを生成。
- **`game_session.py`** — `BaseGameSession`。参加者管理・Pot管理・ターンローテーション・返金処理などの共通機能。`to_dict()` / `from_dict()` によるゲーム状態のシリアライズ対応。

### logic/blackjack/ と logic/chinchiro/（ゲームエンジン）
各ゲームは **Service**（純粋なロジック）と **View**（Discord UI）に分離されています。

#### 画像アセットの動的合成 (Dynamic Synthesis) - v2.2 導入
メモリ消費を抑えるため、カード画像は個別のファイルとして保持せず、実行時にパーツ（背景、スート、ランク）を合成して生成します。
- **仕組み**: `core/utils/card_assets.py` が `data/card/components/` から部品を読み込み、PIL (Pillow) を用いて合成。
- **キャッシュ**: 生成された画像はメモリにキャッシュされ、再利用されます。
- **メリット**: 52枚＋αの画像を個別に保持する場合と比較し、配布サイズとメモリ使用量を劇的に削減。

| ファイル | 役割 |
| :--- | :--- |
| `blackjack/bj_deck.py` | 8デッキ（416枚）の構築・シャッフル・ドロー |
| `blackjack/bj_service.py` | ゲーム進行管理、外部（SessionManager）とのインターフェース |
| `blackjack/bj_view.py` | Embed生成・ボタンView・インタラクション処理 |
| `blackjack/bj_canvas.py` | `data/card/` のカード画像を合成した手札表示 Canvas |
| `blackjack/bj_models.py` | 手札とプレイヤーの状態保持とスコア計算 |
| `blackjack/bj_rules.py` | 勝敗判定、配当倍率、特殊役のボーナス定義 |
| `blackjack/bj_formatter.py` | Embed フォーマッタ |
| `blackjack/bj_exceptions.py` | BJ固有例外クラス |
| `blackjack/bj_hospitality.py` | バースト回避・ディーラー誘導などの接待ロジック実体 |
| `chinchiro/cc_service.py` | ゲーム進行管理、外部とのインターフェース |
| `chinchiro/cc_view.py` | Embed生成・ボタンView・インタラクション処理 |
| `chinchiro/cc_models.py` | 手番とプレイヤーの状態保持、ダイスの目管理 |
| `chinchiro/cc_rules.py` | 役判定、勝利判定、配当・親の責任税の定義 |
| `chinchiro/cc_hospitality.py` | 3投目の目なし回避などの接待ロジック実体 |

### logic/poker/（テキサス・ホールデム エンジン）
対人戦ポーカーモジュール。接待ロジックは発動しない。AI サブパッケージが分離されている。

| ファイル | 役割 |
| :--- | :--- |
| `poker/pk_deck.py` | 52枚デッキの構築・シャッフル・ドロー（`data/card/` 画像使用） |
| `poker/pk_service.py` | `TexasPokerService`: セッション管理・各工程のコーディネーター |
| `poker/pk_round_manager.py` | ベッティングラウンド管理（手番、アクションバリデーション） |
| `poker/pk_settlement_manager.py` | 精算管理（勝者特定、配当計算、サイドポット考慮） |
| `poker/pk_view.py` | `PokerView`: UI・ボタンインタラクション・手札確認（ephemeral） |
| `poker/pk_canvas.py` | `data/card/` 画像を用いたテーブル Canvas 合成 |
| `poker/pk_models.py` | `PokerPlayer`: カード・ベット状態保持。手役情報の静的保持 |
| `poker/pk_rules.py` | `PokerRules`: 7枚→最强5枚の役判定 |
| `poker/pk_formatter.py` | Embed フォーマッタ |
| `poker/pk_exceptions.py` | ポーカー固有例外クラス |
| `poker/ai/` | AI エンジン サブパッケージ（`base_ai`, `brains`, `evaluator`, `personality`） |

### logic/dobumon/（怒武者育成エンジン詳細）
v2.16 で6サブパッケージへの完全分解が完了。モノリシックな `DobumonService` は廃止され、専門サービス群に置き換えられた。

#### サブパッケージ構成

| サブパッケージ | 役割 |
| :--- | :--- |
| `core/` | コアロジック群。DB操作・個体管理・各種サービスファサード |
| `dob_battle/` | 戦闘計算パッケージ。エンジン・計算・精算・野生戦闘 |
| `dob_shop/` | ショップシステム。アイテム定義・効果適用・UI |
| `dob_views/` | Discord UI パッケージ。各アクション用の View クラス群 |
| `genetics/` | 遺伝・配合計算パッケージ。メンデル型＋血統遺伝・近親判定 |
| `training/` | トレーニングエンジンパッケージ。能力上昇・コスト計算・技定義 |

#### core/ 主要クラス

| ファイル | クラス / 役割 |
| :--- | :--- |
| `dob_manager.py` | `DobumonManager`: DB操作・個体の読み書き基盤 |
| `dob_factory.py` | `DobumonFactory`: 個体生成（初期値・野生個体） |
| `dob_models.py` | `DobumonData` 等: データ構造・バリデーション |
| `dob_traits.py` | 特性（トレイト）定義・効果計算 |
| `dob_battle_service.py` | 対人・野生戦闘の統括サービスファサード |
| `dob_breeding_service.py` | 配合サービスファサード |
| `dob_training_service.py` | トレーニングサービスファサード |
| `dob_market_service.py` | マーケット（売買）サービス |
| `dob_chronicle.py` | 個体の戦歴・記録管理 |
| `dob_logger.py` | `DobumonLogger`: ログ出力（アクション・スペック）の一元管理 |
| `dob_exceptions.py` | ドブモン固有例外クラス群 |

#### dob_battle/ 主要構成

| ファイル | 役割 |
| :--- | :--- |
| `dob_engine.py` | 戦闘メインエンジン（ターン進行） |
| `dob_calculator.py` | ダメージ計算・命中判定 |
| `dob_settlement.py` | 報酬・統計処理（勝敗確定後） |
| `battle_handler.py` | 戦闘リクエストのディスパッチャ |
| `battle_session.py` | 戦闘セッション状態管理 |
| `wild/` | 野生戦闘サブパッケージ（難易度ランク制・3ステップUIウィザード） |

#### dob_views/ 主要 View

| ファイル | 役割 |
| :--- | :--- |
| `dob_formatter.py` | ANSI装飾Embed生成（ステータス表示） |
| `dob_kinship_tree.py` | 家系図 Canvas 生成（交差最小化アルゴリズム） |
| `dob_map_view.py` | 家系図表示対象の選択UI（ドロップダウンメニュー） |
| `dob_battle.py` | 対人戦闘UI |
| `dob_breeding.py` | 交配UI |
| `dob_training.py` | トレーニングUI |
| `dob_buy.py` / `dob_sell.py` | マーケット売買UI |
| `dob_skill.py` | 技命名UI |
| `dob_status.py` | ステータス表示View |

### logic/bet_service.py（ファサード）
全ゲームからの経済ルール呼び出しを一本化する窓口。実体は `logic/economy/` に委譲。

```python
BetService.escrow()         # 賭け金徴収
BetService.payout()         # 払い出し（ラバーバンド適用）
BetService.execute_jackpot() # ジャックポット配当
BetService.claim_daily()    # デイリーボーナス実行
```

### logic/economy/（経済専門サービス）

| サービス | 役割 |
| :--- | :--- |
| `provider.py` | `escrow`（徴収）・`payout`（配当）・`split_payout`（山分け） |
| `bonus.py` | デイリーボーナス（BI成分+SN成分の二階建て方式） |
| `jackpot.py` | ジャックポットへの積立（`add_to_jackpot`）と放出処理（`execute_jackpot`） |
| `status.py` | 資産ランク（Prime/Standard/Recovery）と中央値の算出 |
| `game_logic.py` | 接待アルゴリズム（Bad Luck Protection）の共通ロジック |

### core/（共通基盤層）

| 分類 | ファイル/ディレクトリ | 役割 |
| :--- | :--- | :--- |
| **Facade** | `economy.py` | `WalletManager`: 残高・統計・ガチャ情報の読み書き窓口 |
| **Handlers** | `handlers/` | `sql_handler/` (分割済パッケージ) / `storage.py` (永続化実体) |
| **Models** | `models/` | `validation.py`: Pydantic によるデータ構造定義・検証 |
| **UI** | `ui/` | `common.py` (JoinView/MatchJoinView) / `starter.py` (ゲーム開始制御) |
| **Utils** | `utils/` | `logger`, `config`, `exceptions`, `decorators` 等の共通機能 |
| **Data** | `data/` | `discord_eco_sys.db` (本番) / `gacha_event.json` / `card/` (カード画像53枚) / `fonts/` / `dobumon/` |

---

## 4. ステートレス設計とDB永続化

Bot のプロセス再起動に対して堅牢なステートレス設計を採用しています。

```
ゲーム進行中
  ├── ゲーム状態（参加者・ターン・手札等）
  │   → game_sessions テーブルに JSON で保存 (upsert_session)
  │   → 再起動後も channel_id で復元可能
  │
  └── ユーザー残高・統計・ガチャ情報
      → wallets テーブルに保存 (upsert_user)
      → 再起動してもポイントは保持される
```

詳細なカラム定義は `schema.md` を参照してください。

---

## 5. データフロー例

### 5.1 ブラックジャック一局

1.  **ユーザー**: `/dd-game blackjack`
    - `cogs/games.py` が受け取り、`GameManager` に開始要求。
2.  **GameManager**: `game_sessions` DB で既存セッション有無を確認。
3.  **BetService.escrow()**: 全参加者の賭け金を `wallets` から徴収。
4.  **BlackjackService**: ゲーム進行（Hit/Stand/Bust）。
    - `GameLogicService`: 資産ランク参照 → 接待判定。
5.  **勝敗確定**:
    - `BetService.payout()`: 勝者に配当（ラバーバンド適用）。
    - 希少役 → `JackpotService.execute_jackpot()`: JP配当計算・セーフティキャップ適用。
6.  **GameManager**: `game_sessions` からセッションを削除。

### 5.2 テキサス・ホールデム一局

```
2.  募集 (JoinView): `/dd-game poker players:N` 等で募集開始。他の人間が参加。
3.  ゲーム開始 (starter.py): 不足人数をNPCで自動補充（TexasPokerService._fill_npcs()）
    - AIランク決定（動的ウェイト: Primeユーザーがいると MONSTER 出現率アップ）
    - NPCのバイイン原資をシステム供給
4.  ポーカー進行: プリフロップ〜リバー
    - プレイヤー（人間/NPC）が順次アクション。NPCは `pk_ai.py` のランク別ロジックで自動決定。
    - MONSTER AI: 必要に応じて他人の手札を覗き、勝利のために手札を入れ替えるお仕置き発動.
5.  ショウダウン (phase == "showdown")
    - PokerSettlementManager.execute():
         - 人間勝者: Pot全額配当 (BetService.payout) + 希少役JPボーナス
         - NPC勝者: **純粋な利益分（配当 - ベット額）のみをジャックポットプールへ積立。残スタックは消滅。** (BetService.add_to_jackpot)
6.  GameManager: game_sessions からセッションを削除
```

---

## 6. CI/CD パイプライン

1. **CI Check (`run_ci.py`)**: `ruff` による整形と `pytest` による検証。
2. **Secure Deploy (`deploy.py`)**: リモート DB 同期、ZIP パッケージ作成、クリーン転送、`systemd` 再起動。

---

## 7. テスト構成 (Testing Architecture)

`pytest` をフレームワークとして採用し、モックを活用して外部依存を切り離したテストを実施しています。

- **経済ロジック検証**: ステータスごとのデイリーボーナス計算、ベンチマークの平均/中央値切り替えなどを検証。
- **ゲームエンジン検証**: ブラックジャック・チンチロリン・ポーカーの役判定、ジャックポット配当、接待発動条件などを検証。
- **スプリット検証**: `test_blackjack_split.py` でスプリット時のハンド分割・接待ペナルティ・バリュー一致条件を詳細検証。
- **ポーカー検証**: `test_poker.py` で役判定（10段階）・ゲームフロー（プリフロップ→フロップ遷移）・ショウダウン判定を検証。
- **ドブモン系検証** (`tests/unit/dobumon/`, 29ファイル): 遺伝計算・トレーニングコスト・野生戦闘・血縁判定・ショップ効果・タブー配合・大成功確率・寿命・感情システムなど網羅的に検証。
- **データアクセス検証**: SQLite に対する Upsert 処理や、スキーマ変更時の自動マイグレーションを検証。
- **継続的テスト**: `run_ci.py` を通じてデプロイ前に全テストが自動実行され、品質を担保。

> [!IMPORTANT]
> テスト実行時は `APP_ENV=test` が設定され、`data/test_db.db` を使用することで本番 DB を汚染しない隔離設計になっています。

---

## 8. ドキュメント一覧

### 8.0 共通・全体設計

| ファイル | 内容 |
| :--- | :--- |
| `overview.md` | プロジェクト概要・機能スコープ・実装進捗 |
| `architecture.md` | **本ファイル**。コード構造・レイヤー設計 |
| `directory_structure.md` | **ディレクトリ構造詳細**。全ファイルの一覧と役割 |
| `game_design.md` | **サービス概要層**。経済圏の全体像 |
| `hospitality_logic.md` | **共通ロジック層**。接待アルゴリズムの定義 |
| `economy_design.md` | 経済ロジック設計（ラバーバンド・デイリーボーナス等） |
| `economy_error_handling.md` | 経済エラー処理・例外ハンドリング仕様 |
| `schema.md` | SQLite DB の全テーブル・カラム定義 |
| `commands_design.md` | スラッシュコマンド一覧と設計思想 |
| `operations.md` | デプロイ・systemd管理・SSH・セキュリティ設定 |
| `TODO.md` | 将来の課題・システム改善・機能ロードマップ |

### 8.0.1 ゲーム個別仕様

| ファイル | 内容 |
| :--- | :--- |
| `blackjack.md` | ブラックジャックの個別仕様 |
| `chinchiro.md` | チンチロリンの個別仕様 |
| `poker.md` | テキサス・ホールデムの個別仕様 |
| `gacha.md` | ガチャイベント設計（仕様・確率・フレーバーテキスト） |
| `Roulette System Specification.md` | ルーレットシステム仕様書 |

### 8.0.2 怒武者（ドブモン）関連 (`docs/dobumon/`)

| ファイル | 内容 |
| :--- | :--- |
| `dobumon/dobumon.md` | 主仕様書。育成・血統・技・戦闘仕様 |
| `dobumon/dobumon_system.md` | システム設計概要（サービス分解・依存関係） |
| `dobumon/dobumon_shop_design.md` | ショップ設計・アイテム効果仕様 |
| `dobumon/怒武者ショップアイテム定義書.md` | アイテム詳細定義書（全アイテムの効果・価格） |

### 8.0.3 リファクタリング記録 (`docs/refactoring/`)

| ファイル | 内容 |
| :--- | :--- |
| `refactoring/dob_wild_battle_refactoring.md` | 野生戦闘リファクタリング記録 |
| `refactoring/date_utils_migration.md` | 日付ユーティリティ移行記録 |

### 8.1 ドキュメントの階層構造 (Hierarchy)

保守性と可読性を保つため、以下の3層構造を徹底しています。

1.  **概要・全体設計層** (`game_design.md`, `architecture.md` 等)
    - 共通の経済圏、設計思想、レイヤー構造を定義。
2.  **共通ロジック詳細層** (`hospitality_logic.md`, `schema.md`)
    - 接待アルゴリズムや DB 構造など、実装と密に連動する技術仕様。
3.  **各ゲーム・機能詳細層** (`blackjack.md`, `dobumon/dobumon.md` 等)
    - そのゲーム固有の役、配当、確率設定など。
4.  **怒武者専用ディレクトリ** (`docs/dobumon/`)
    - 怒武者関連ドキュメントをサブディレクトリに集約。ショップ設計・アイテム定義・システム設計を一元管理。

### 8.2 現状のメンテナンス状況 (Cleaning)

- **非推奨ファイル**: `daily_logic_update.md` は `economy_design.md` に統合済み（ファイルは参照用に残存）。
- **移動済みファイル**: `dobumon.md`, `dobumon_shop_design.md`, `dobumon_system.md`, `怒武者ショップアイテム定義書.md` → `docs/dobumon/` に移動。
- **今後の課題**: Match (対人戦) の詳細仕様ドキュメント (`match.md`) の作成を推奨。
