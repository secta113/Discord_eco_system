# Discord Duel — Economy & Game Bot

> Discordサーバー内の経済圏とゲームを統合した、長期コミュニティ向けの Discord Bot。  
> テキサス・ホールデム、ブラックジャック、チンチロリン、そして独自育成ゲーム「怒武者（ドブモン）」を搭載。

---

## ✨ 特徴

- 💰 **永続的な経済圏** — SQLite による残高永続化・エスクロー決済・ジャックポットプール
- 🃏 **複数のカジノゲーム** — ブラックジャック（スプリット対応）、テキサス・ホールデム（NPC AI）、チンチロリン
- 🐉 **怒武者（ドブモン）育成** — メンデル型遺伝、交配、野生戦闘、ショップ、家系図マップ
- 🎰 **ガチャシステム** — 1日3回・コスト増分・全250種の日常イベントコレクション
- 🛡️ **接待アルゴリズム** — 資産ランク連動の Bad Luck Protection で逆転機会を保証
- ⚙️ **堅牢な CI/CD** — `ruff` + `pytest` による自動品質チェックと安全なリモートデプロイ
- 🔁 **ステートレス設計** — プロセス再起動後もゲームセッション・残高を完全復元

---

## 🎮 機能一覧

| 機能 | 概要 |
| :--- | :--- |
| **Economy System** | ポイント口座管理・送金・デイリーボーナス（セーフティネット型） |
| **Blackjack** | ディーラー vs プレイヤー、8デッキ416枚、スプリット対応、希少役ジャックポット |
| **Texas Hold'em** | 最大多人数対戦、NPC AI（ランク別・お仕置き発動）、Canvas 合成テーブル画像 |
| **Chinchiro** | 6面ダイス×3のロールシミュレーション・役判定・Winner Takes All |
| **Match（エスクロー）** | 外部ゲーム（麻雀・FPS等）の結果に基づく自動エスクロー決済 |
| **Gacha** | 1日3回・コスト増分・全250種の日常イベントコレクション |
| **Jackpot** | 希声役発生時にシステムプールから特別配当 |
| **怒武者（ドブモン）** | 育成・遺伝配合・対人/野生戦闘・トレーニング・ショップ・家系図 |

---

## 🏗️ アーキテクチャ

```
┌─────────────────────────────────────────────────────┐
│  Presentation Layer                                  │
│  cogs/ — コマンド定義 / main.py — 起動・拡張管理       │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│  Session Management Layer                            │
│  managers/ — チャンネル別セッション一元管理             │
│  core/ui/  — ゲーム開始UI制御                         │
└──────┬──────────────────────┬───────────────────────┘
       │ ゲームロジック         │ 経済ルール
┌──────▼──────────┐  ┌────────▼──────────────────────┐
│  Game Engines   │  │  Economy Facade               │
│  logic/blackjack│  │  logic/bet_service.py         │
│  logic/chinchiro│  │  logic/economy/               │
│  logic/poker    │  └───────────────────────────────┘
│  logic/dobumon  │
└──────┬──────────┘
       │
┌──────▼──────────────────────────────────────────────┐
│  Data Access Layer                                   │
│  core/economy.py  — WalletManager                   │
│  core/handlers/   — SQL CRUD / Storage              │
│  data/            — SQLite DB / カード画像 / フォント  │
└─────────────────────────────────────────────────────┘
```

詳細は [`docs/architecture.md`](docs/architecture.md) および [`docs/directory_structure.md`](docs/directory_structure.md) を参照してください。

---

## 📋 必要条件

- Python 3.11+
- Discord Bot Token（[Discord Developer Portal](https://discord.com/developers/applications) で取得）
- Raspberry Pi 5 または常時稼働 Linux 環境（推奨）

---

## 🚀 セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/<your-username>/Discord_eco_system.git
cd Discord_eco_system
```

### 2. 仮想環境の作成と依存パッケージのインストール

```bash
python -m venv venv
# Windows
venv\Scripts\pip.exe install -r requirements.txt
# Linux / macOS
venv/bin/pip install -r requirements.txt
```

### 3. 環境変数の設定

`.env.example` をコピーして `.env` を作成し、値を入力します。

```bash
cp .env.example .env
```

```dotenv
DISCORD_BOT_TOKEN = 'your_bot_token_here'
DISCORD_GUILD_ID  = 'your_guild_id_here'
```

### 4. Bot の起動

```bash
# Windows
venv\Scripts\python.exe main.py
# Linux / macOS
venv/bin/python main.py
```

---

## 🕹️ コマンド一覧

### 🎮 ゲーム (`dd-game`)

| コマンド | 説明 |
| :--- | :--- |
| `/dd-game chinchiro` | チンチロリンの参加募集を開始 |
| `/dd-game blackjack` | ブラックジャックの参加募集を開始 |
| `/dd-game poker` | テキサス・ホールデムの参加募集を開始 |
| `/dd-game match` | 外部ゲーム用エスクローマッチの募集を開始 |
| `/dd-game gacha` | 1日3回限定のデイリーガチャ |

### 💳 ウォレット (`dd-wallet`)

| コマンド | 説明 |
| :--- | :--- |
| `/dd-wallet balance` | 現在の所持ポイントを確認 |
| `/dd-wallet stats` | プロフィール（残高・戦績・ガチャコンプ率）を表示 |
| `/dd-wallet jackpot` | ジャックポットプールの総額を確認 |
| `/dd-wallet daily` | 1日1回のデイリーボーナスを受け取る |
| `/dd-wallet pay` | 別ユーザーへポイントを送金 |

### 🐉 怒武者 (`dd-dobumon`)

| コマンド | 説明 |
| :--- | :--- |
| `/dd-dobumon status` | 所持怒武者のステータス表示 |
| `/dd-dobumon train` | トレーニングで能力値を強化 |
| `/dd-dobumon battle` | 他プレイヤーの怒武者と対人戦闘 |
| `/dd-dobumon wild-battle` | 野生の怒武者と戦闘（難易度選択制） |
| `/dd-dobumon breed` | 2体の怒武者を交配（メンデル型遺伝） |
| `/dd-dobumon shop` | ドブモンショップでアイテムを購入 |
| `/dd-dobumon market` | マーケットで怒武者を売買 |
| `/dd-dobumon map` | 家系図（キンシップマップ）を表示 |

### ⚙️ 管理 (`dd-mod`)

| コマンド | 説明 |
| :--- | :--- |
| `/dd-mod maintenance` | システムの緊急停止 / 再開 |
| `/dd-mod logs` | 指定ユーザーのポイント履歴を表示 |
| `/dd-mod status` | Bot のバージョン・Uptime・総流通ポイントを表示 |
| `/dd-mod winner` | 殿堂入りプレイヤーを表彰（公開） |

### 🛡️ フェイルセーフ

| コマンド | 説明 |
| :--- | :--- |
| `/dd-cancel` | 現在のゲームを強制終了し、参加者に全額返金 |

---

## 🔧 開発

### CI チェック（Lint + テスト）

コード変更後は必ず CI チェックを実行してください。

```bash
venv\Scripts\python.exe run_ci.py
```

`ruff` によるフォーマット・Lint と `pytest` による自動テストが実行されます。

### テスト単体実行

```bash
venv\Scripts\python.exe -m pytest tests/ -v
```

> テスト実行時は `APP_ENV=test` が設定され、`data/test_db.db` を使用するため本番 DB を汚染しません。

### CLI 管理ツール

```bash
# ポイント付与
venv\Scripts\python.exe admintool.py give <user_id> <amount> --reason "理由"

# ポイント回収
venv\Scripts\python.exe admintool.py remove <user_id> <amount> --reason "理由"

# 残高確認
venv\Scripts\python.exe admintool.py balance <user_id>
```

---

## 📦 デプロイ

`deploy.py` はリモートサーバーへの安全なデプロイを自動化します。

```bash
venv\Scripts\python.exe deploy.py
```

実行される処理：
1. `run_ci.py` で CI チェック（失敗時はデプロイ中断）
2. リモート DB の同期 (`fetch_db.py`)
3. ZIP パッケージ作成
4. SSH でリモートサーバーへ転送
5. `systemd` サービスを再起動

---

## 🛠️ 技術スタック

| 項目 | 内容 |
| :--- | :--- |
| **Language** | Python 3.11+ |
| **Framework** | discord.py 2.7.1 (Gateway API) |
| **Database** | SQLite（WAL モード） |
| **Validation** | Pydantic v2 |
| **Image Processing** | Pillow（Canvas合成 / カード画像 / 家系図） |
| **Linter / Formatter** | Ruff |
| **Testing** | pytest / pytest-asyncio / pytest-mock |
| **Infrastructure** | Raspberry Pi 5 / 常時稼働 Linux 環境 |

---

## 📁 プロジェクト構成（抜粋）

```
.
├── main.py              — エントリポイント
├── deploy.py            — 自動デプロイスクリプト
├── run_ci.py            — CI自動化（Lint + Test）
├── admintool.py         — CLI管理ツール
├── cogs/                — Discord拡張機能（コマンド定義）
├── logic/               — ゲームエンジン・ビジネスロジック
│   ├── blackjack/       — ブラックジャックエンジン
│   ├── chinchiro/       — チンチロリンエンジン
│   ├── poker/           — テキサス・ホールデムエンジン（AI搭載）
│   ├── dobumon/         — 怒武者育成エンジン
│   └── economy/         — 経済専門サービス群
├── core/                — システム基盤（DB・バリデーション・UI共通部品）
├── managers/            — セッション管理
├── data/                — SQLite DB・カード画像・フォント
├── tests/               — 自動テストスイート（unit / integration / simulations）
└── docs/                — 設計ドキュメント
```

詳細は [`docs/directory_structure.md`](docs/directory_structure.md) を参照。

---

## 📄 ドキュメント

| ドキュメント | 内容 |
| :--- | :--- |
| [`docs/architecture.md`](docs/architecture.md) | アーキテクチャ・レイヤー設計 |
| [`docs/commands_design.md`](docs/commands_design.md) | コマンド一覧と設計思想 |
| [`docs/economy_design.md`](docs/economy_design.md) | 経済ロジック設計（ラバーバンド・デイリーボーナス等） |
| [`docs/dobumon/dobumon.md`](docs/dobumon/dobumon.md) | 怒武者育成・遺伝・戦闘の主仕様書 |
| [`docs/blackjack.md`](docs/blackjack.md) | ブラックジャック個別仕様 |
| [`docs/poker.md`](docs/poker.md) | テキサス・ホールデム個別仕様 |
| [`docs/schema.md`](docs/schema.md) | SQLite DB スキーマ定義 |
| [`docs/operations.md`](docs/operations.md) | デプロイ・運用仕様 |

---

## ⚠️ 注意事項

- `.env` ファイルには Bot トークンが含まれます。絶対にリポジトリへコミットしないでください（`.gitignore` で除外済み）。
- `data/discord_eco_sys.db`（本番DB）もリポジトリには含めないでください（`.gitignore` で除外済み）。

---

*本プロジェクトは特定のプライベートDiscordサーバー向けに開発されたものです。*
