# ディレクトリ構造 (directory_structure.md)

> **最終更新**: 2026-05-05  
> *v2.5 UIリファクタリング：ドブモンUIの一元化、ゲームUIのサブディレクトリ化、matchパッケージ化、starter.py移動*

---

## 全体ディレクトリツリー

```
. (Project Root)
├── main.py              — エントリポイント。EconomyBot クラス定義・Cog読み込み・起動
├── admintool.py         — 管理者用CLIツール (ポイント付与・回収・残高確認)
├── deploy.py            — デプロイ（CI・自動転送・再起動・ログ監視）
├── fetch_db.py          — リモートDBの取得スクリプト
├── run_ci.py            — CI自動化スクリプト (Lint・Format・Test)
├── requirements.txt     — 依存ライブラリ一覧
├── pyproject.toml       — プロジェクト設定 (ruff, pytest)
├── .env                 — 環境変数 (BOTトークン等) ※リポジトリ除外
├── core/                — システム基盤層
│   ├── handlers/        — 低レイヤー・データ操作
│   │   ├── sql_handler/ — SQLite CRUD操作パッケージ
│   │   │   ├── __init__.py      — クエリ関数の公開
│   │   │   ├── db_base.py       — 接続・初期化・システム統計
│   │   │   ├── user_sql.py      — ウォレット操作
│   │   │   ├── session_sql.py   — セッション管理
│   │   │   ├── economy_sql.py   — 経済統計・履歴
│   │   │   └── dobumon_sql.py   — 怒武者データ・JPログ
│   │   └── storage.py   — セッション/ウォレット情報の永続化インターフェース
│   ├── models/          — データモデル・バリデーション
│   │   └── validation.py — Pydantic によるデータ構造定義・検証
│   ├── ui/              — Discord UI 共通コンポーネント
│   │   └── view_base.py — BaseView/BaseModal/JoinView: 全Viewの基底クラス・エラーハンドラー
│   ├── utils/           — ユーティリティ
│   │   ├── config.py    — VERSION等の定数定義
│   │   ├── constants.py — 共通定数定義
│   │   ├── logger.py    — ログ出力 (Logger クラス)
│   │   ├── exceptions.py — カスタム例外クラス群
│   │   ├── decorators.py — @check_maintenance / @defer_response 等
│   │   ├── card_assets.py — カード画像アセット管理
│   │   ├── font_manager.py — フォント管理 (Canvas描画用)
│   │   ├── time_utils.py — 日時ユーティリティ
│   │   └── formatters.py — 数字フォーマット (カンマ区切り、pts付与)
│   └── economy.py       — WalletManager: 残高・統計操作の窓口
├── cogs/                — Discord 拡張機能 (Extension)
│   ├── economy.py       — 経済関連コマンド (balance, top, daily)
│   ├── admin.py         — 管理者用コマンド (gift, take, reset)
│   ├── games.py         — ゲーム起動コマンド (blackjack, chinchiro, poker, match, gacha)
│   ├── dobumon.py       — 怒武者関連コマンド (status, train, battle, breed, shop, map 等)
│   └── system.py        — システム管理 (error handling, context menu)
├── logic/               — ビジネスロジック・ゲームエンジン
│   ├── bet_service.py   — 経済ルールのファサード
│   ├── gacha_service.py — ガチャ抽選ロジック
│   ├── match/           — 外部マッチ（エスクロー）パッケージ
│   │   ├── __init__.py
│   │   ├── match_service.py — 1vs1外部ゲーム用エスクローマッチ管理
│   │   └── ui/
│   │       ├── __init__.py
│   │       └── match_view.py — マッチ用Discord UI
│   ├── blackjack/       — ブラックジャック ゲームエンジン
│   │   ├── ui/                  — Discord UI サブパッケージ
│   │   │   ├── __init__.py
│   │   │   └── bj_view.py       — UI
│   │   ├── bj_service.py        — 進行管理
│   │   ├── bj_deck.py           — デッキ（data/card/ のカード画像を使用）
│   │   ├── bj_canvas.py         — 手札画像合成 Canvas
│   │   ├── bj_models.py         — データモデル
│   │   ├── bj_rules.py          — ルール判定
│   │   ├── bj_formatter.py      — Embed フォーマッタ
│   │   ├── bj_exceptions.py     — 例外クラス
│   │   └── bj_hospitality.py    — 接待
│   ├── chinchiro/       — チンチロリン ゲームエンジン
│   │   ├── ui/                  — Discord UI サブパッケージ
│   │   │   ├── __init__.py
│   │   │   └── cc_view.py       — UI
│   │   ├── cc_service.py        — 進行管理
│   │   ├── cc_models.py         — モデル
│   │   ├── cc_rules.py          — ルール
│   │   └── cc_hospitality.py    — 接待
│   ├── poker/           — テキサス・ホールデム ゲームエンジン
│   │   ├── ui/                  — Discord UI サブパッケージ
│   │   │   ├── __init__.py
│   │   │   └── pk_view.py       — UI
│   │   ├── pk_service.py        — コーディネーター
│   │   ├── pk_round_manager.py  — ベッティング管理
│   │   ├── pk_settlement_manager.py — 精算管理
│   │   ├── pk_deck.py           — デッキ（data/card/ のカード画像を使用）
│   │   ├── pk_canvas.py         — テーブル画像合成 Canvas
│   │   ├── pk_models.py         — モデル
│   │   ├── pk_rules.py          — 役判定
│   │   ├── pk_formatter.py      — Embed フォーマッタ
│   │   ├── pk_exceptions.py     — 例外クラス
│   │   └── ai/                  — AIエンジン サブパッケージ
│   │       ├── __init__.py
│   │       ├── base_ai.py       — AI 基底クラス
│   │       ├── brains.py        — ランク別 AI 思考ロジック
│   │       ├── evaluator.py     — ハンド評価ユーティリティ
│   │       └── personality.py   — AIパーソナリティ定義
│   ├── dobumon/         — 怒武者（ドブモン）育成エンジン
│   │   ├── __init__.py          — パッケージ公開インターフェース
│   │   ├── core/                — コアロジック群
│   │   │   ├── __init__.py
│   │   │   ├── dob_admin.py         — 管理者操作 (強制削除・DB修正等)
│   │   │   ├── dob_battle_service.py— 対人・野生戦闘の統括サービス
│   │   │   ├── dob_breeding_service.py — 配合サービスファサード
│   │   │   ├── dob_chronicle.py     — 個体の戦歴・記録管理
│   │   │   ├── dob_constants.py     — 共通定数
│   │   │   ├── dob_exceptions.py    — ドブモン固有例外
│   │   │   ├── dob_factory.py       — 個体生成ファクトリ（初期値・野生個体）
│   │   │   ├── dob_formatter.py     — ANSI装飾Embed生成 ※v2.5移動
│   │   │   ├── dob_manager.py       — DB操作・個体の読み書き基盤
│   │   │   ├── dob_market_service.py— マーケット（売買）サービス
│   │   │   ├── dob_buy_service.py   — 購入処理専用サービス
│   │   │   ├── dob_models.py        — データモデル (DobumonData 等)
│   │   │   ├── dob_logger.py        — ログ出力（アクション・スペック）の一元管理
│   │   │   ├── dob_training_service.py — トレーニングサービスファサード
│   │   │   └── dob_traits.py        — 特性（トレイト）定義・効果計算
│   │   ├── ui/                  — Discord UI パッケージ ※v2.5統合
│   │   │   ├── __init__.py
│   │   │   ├── dob_battle.py        — 対人戦闘UI
│   │   │   ├── dob_breeding.py      — 交配UI
│   │   │   ├── dob_buy.py           — 購入確認UI
│   │   │   ├── dob_common.py        — 共通コンポーネント (BaseView等)
│   │   │   ├── dob_kinship_tree.py  — 家系図Canvas生成
│   │   │   ├── dob_map_view.py      — 家系図表示対象の選択UI
│   │   │   ├── dob_sell.py          — 売却UI
│   │   │   ├── dob_shop_view.py     — ショップDiscord UI ※v2.5移動
│   │   │   ├── dob_skill.py         — 技命名UI
│   │   │   ├── dob_status.py        — ステータス表示View
│   │   │   ├── dob_training.py      — トレーニングUI
│   │   │   └── dob_wild_views.py    — 野生戦闘UIウィザード ※v2.5移動
│   │   ├── dob_battle/          — 戦闘計算パッケージ
│   │   │   ├── __init__.py
│   │   │   ├── battle_handler.py    — 戦闘リクエストのディスパッチャ
│   │   │   ├── battle_session.py    — 戦闘セッション状態管理
│   │   │   ├── dob_calculator.py    — ダメージ計算・命中判定
│   │   │   ├── dob_engine.py        — 戦闘メインエンジン（ターン進行）
│   │   │   ├── dob_settlement.py    — 報酬・統計処理（勝敗確定後）
│   │   │   └── wild/                — 野生戦闘サブパッケージ
│   │   │       ├── __init__.py
│   │   │       ├── wild_config.py   — 難易度ランク設定 (JSON定義)
│   │   │       ├── wild_handler.py  — 野生戦闘フロー制御
│   │   │       └── wild_settlement.py — 野生戦闘報酬処理
│   │   ├── dob_shop/            — ショップシステムパッケージ
│   │   │   ├── __init__.py
│   │   │   ├── dob_items.py         — アイテム定義・効果仕様
│   │   │   ├── dob_shop_effect_manager.py — アイテム効果の適用処理
│   │   │   └── dob_shop_service.py  — ショップビジネスロジック
│   │   ├── genetics/            — 遺伝・配合計算パッケージ
│   │   │   ├── __init__.py
│   │   │   ├── breeding_handler.py      — 配合リクエストのハンドラ
│   │   │   ├── dob_breeders.py          — 配合ロジック本体（遺伝計算）
│   │   │   ├── dob_mutation.py          — MutationEngine: 突然変異・固定管理
│   │   │   ├── dob_migration_v2_fix_loci.py — 遺伝子座修正マイグレーション
│   │   │   ├── dob_genetics_constants.py— 遺伝関連定数・確率テーブル
│   │   │   ├── dob_kinship.py           — 血縁関係・近親交配判定
│   │   │   ├── dob_mendel.py            — メンデル型遺伝計算
│   │   │   └── dob_taboo.py             — タブー（禁忌）配合ルール
│   │   └── training/            — トレーニングエンジンパッケージ
│   │       ├── __init__.py
│   │       ├── dob_skills.py            — 技定義・スキルセット
│   │       ├── dob_train.py             — トレーニングロジック本体
│   │       ├── dob_train_config.py      — トレーニング設定・コスト定義
│   │       ├── dob_wild_performance.py  — 野生戦闘パフォーマンス評価
│   │       └── training_handler.py      — トレーニングリクエストのハンドラ
│   └── economy/         — 経済ルール専門サービス群
│       ├── provider.py      — escrow / payout
│       ├── bonus.py         — デイリーボーナス
│       ├── jackpot.py       — ジャックポット
│       ├── status.py        — 資産ランク算出
│       ├── game_logic.py    — 接待アルゴリズム
│       ├── eco_exceptions.py— 経済系カスタム例外
│       ├── eco_formatter.py — 経済系Embedフォーマッタ
│       └── config.json      — 経済パラメータ設定
├── managers/            — セッション管理
│   ├── manager.py       — GameManager: チャンネル別一元管理
│   ├── game_session.py  — BaseGameSession: 基底クラス
│   └── starter.py       — execute_game_start(): ゲーム開始UI制御
├── data/                — 永続化データ
│   ├── discord_eco_sys.db     — 本番DB
│   ├── gacha_event.json       — ガチャ設定
│   ├── npc_names.json         — NPC名前リスト
│   ├── poker_blueprints.json  — ポーカーAIブループリント設定
│   ├── card/                  — トランプカード画像
│   │   ├── card_back.png      — カード裏面画像
│   │   └── components/        — カードコンポーネント画像 (動的合成用)
│   │       ├── base_card.png  — カードベース
│   │       ├── suit_{S,H,D,C}.png — 各スートマーク
│   │       └── text_{A,2-10,J,Q,K}.png — 数字・記号テキスト
│   ├── dobumon/               — ドブモン関連データ
│   │   └── wild_maps.json     — 野生戦闘マップ定義
│   └── fonts/                 — フォントファイル
│       └── ja_font_subset.ttf — 日本語フォント (Canvas 描画用・軽量サブセット版)
├── tests/               — 自動テスト (Pytest)
│   ├── conftest.py      — フィクスチャ共通定義
│   ├── unit/            — ユニットテスト
│   │   ├── blackjack/   — ブラックジャック系テスト
│   │   ├── common/      — 共通ロジックテスト
│   │   ├── core/        — core層テスト
│   │   ├── dobumon/     — ドブモン系テスト (29ファイル)
│   │   ├── economy/     — 経済ロジックテスト
│   │   ├── games/       — ゲームエンジンテスト
│   │   └── poker/       — ポーカー系テスト
│   ├── integration/     — 統合テスト
│   │   ├── cogs/
│   │   └── common/
│   └── simulations/     — シミュレーションテスト
│       ├── dobumon/
│       └── poker/
└── docs/                — ドキュメント
    ├── architecture.md        — アーキテクチャ概要
    ├── directory_structure.md — 本ファイル
    ├── overview.md            — プロジェクト概要・機能スコープ
    ├── game_design.md         — 経済圏の全体設計
    ├── economy_design.md      — 経済ロジック設計
    ├── economy_error_handling.md — 経済エラー処理仕様
    ├── hospitality_logic.md   — 接待アルゴリズム仕様
    ├── schema.md              — SQLite DB スキーマ定義
    ├── commands_design.md     — スラッシュコマンド一覧・設計
    ├── blackjack.md           — ブラックジャック個別仕様
    ├── chinchiro.md           — チンチロリン個別仕様
    ├── poker.md               — テキサス・ホールデム個別仕様
    ├── gacha.md               — ガチャイベント設計
    ├── operations.md          — デプロイ・運用仕様
    ├── TODO.md                — 将来課題・ロードマップ
    ├── CHANGELOG.md           — バージョン更新履歴 (v2.2 以降)
    ├── Roulette System Specification.md — ルーレット仕様書
    ├── dobumon/               — 怒武者関連ドキュメント
    │   ├── dobumon.md             — 育成・血統・技・戦闘仕様 (主仕様書)
    │   ├── dobumon_system.md      — システム設計概要
    │   ├── dobumon_shop_design.md — ショップ設計・アイテム効果
    │   └── 怒武者ショップアイテム定義書.md — アイテム詳細定義書
    └── refactoring/           — リファクタリング記録
        ├── date_utils_migration.md     — 日付ユーティリティ移行記録
        └── dob_wild_battle_refactoring.md — 野生戦闘リファクタリング記録
```
