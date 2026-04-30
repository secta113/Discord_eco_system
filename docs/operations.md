# 運用・デプロイ手順書 (operations.md)

> **最終更新**: 2026-03-27  
> *旧ドキュメント「DealerBot_CheatSheet.md」「deploy.md」を統合*

---

## 1. ディレクトリ構造（リモートサーバー）

```
~/Discord_eco_system/
├── main.py               # エントリポイント
├── .env                  # 環境変数 (TOKEN等) [chmod 600]
├── requirements.txt      # 依存ライブラリ
├── admintool.py          # 管理者用CLIツール
├── core/                 # コアシステム層 (DB, Storage, Logger)
├── logic/                # ゲーム・経済ロジック (Blackjack, Chinchiro, BetService等)
├── managers/             # セッション管理
└── data/                 # 永続化データ [chmod 700]
    └── discord_eco_sys.db  # SQLiteデータベース [chmod 600]
```

---

## 2. デプロイ（PC → Raspberry Pi）

PCから Raspberry Pi（サービス名: `Dealer-bot.local`）へコードを転送するには `deploy.py` を使います。

```powershell
# PC側（プロジェクトルートで実行）
python deploy.py
```

### deploy.py が行う処理（自動）

```
1. CI チェックを実行   → run_ci.py (Lint, Format, Test)
2. Bot サービスを停止  → sudo systemctl stop dealerbot.service
3. 本番 DB を取得      → scp Dealer-bot.local:.../discord_eco_sys.db ./data/
4. ローカルでマイグレーション実行 → init_db() でカラム追加
5. デプロイ ZIP 生成   → 対象ファイルのみを抽出し ZIP アーカイブ化
6. 転送と展開          → scp で ZIP 転送後にリモートで unzip
7. Bot サービスを再起動 → sudo systemctl start dealerbot.service
```

> [!IMPORTANT]
> 本番 DB は毎回ローカルに取得してからアップロードします。これにより、コードアップロード時に最新データが上書きされるリスクを防ぎます。

### 転送対象ファイル

`main.py`, `admintool.py`, `core/`, `logic/`, `managers/`, `data/discord_eco_sys.db`, `data/gacha_event.json`, `requirements.txt`

> [!NOTE]
> `.env`（BOT トークン）は転送対象外です。リモートで直接管理してください。

### 部分的な手動上書き（特定ファイルのみ更新する場合）

ZIP を介さず、1ファイルのみを緊急修正して反映させたい場合：

```bash
# 1. ファイルを転送
scp main.py secta113@Dealer-bot.local:/home/secta113/Discord_eco_system/
# 2. サービスを再起動して反映
ssh secta113@Dealer-bot.local "sudo systemctl restart dealerbot.service"
```

---

## 3. サービス管理（systemd）

| 操作 | コマンド |
| :--- | :--- |
| **起動** | `sudo systemctl start dealerbot.service` |
| **停止** | `sudo systemctl stop dealerbot.service` |
| **再起動（コード反映）** | `sudo systemctl restart dealerbot.service` |
| **自動起動の有効化** | `sudo systemctl enable dealerbot.service` |
| **ステータス確認** | `systemctl status dealerbot.service` |
| **設定ファイルの反映** | `sudo systemctl daemon-reload` |

### ログの確認（デバッグ）

```bash
# リアルタイムでログを追跡
sudo journalctl -u dealerbot.service -f

# 直近50行のみ表示
sudo journalctl -u dealerbot.service -n 50 --no-pager
```

---

## 4. セキュリティ・権限設定

| 対象 | コマンド | 意味 |
| :--- | :--- | :--- |
| **データフォルダ** | `chmod 700 data` | 所有者以外進入禁止 |
| **DBファイル** | `chmod 600 data/*.db` | 所有者以外読み書き禁止 |
| **環境変数ファイル** | `chmod 600 .env` | トークン漏洩防止 |
| **SSH ディレクトリ** | `chmod 700 ~/.ssh` | 鍵情報の保護 |
| **SSH 公開鍵** | `chmod 600 ~/.ssh/authorized_keys` | 認証情報の改ざん防止 |
| **所有権の一括修正** | `sudo chown -R secta113:secta113 .` | 所有者をカレントユーザーへ |

> [!TIP]
> **WAL モード**: `sql_handler.py` で有効化されているWALモードは書き込み中でも読み取り可能ですが、`data/` ディレクトリに書き込み権限がないと `readonly` エラーになります。必ず `chmod 700 data` にしてください。

---

## 5. SSH 鍵認証の設定

SSH鍵ペア認証を設定しておくと、`deploy.py` の実行時にパスワード入力が不要になります。

```bash
# 鍵ペア生成 (Ed25519)
ssh-keygen -t ed25519 -C "secta113@Dealer-bot"

# 公開鍵の転送 (Linux/Mac)
ssh-copy-id secta113@Dealer-bot.local

# ssh-agent への登録（パスフレーズ入力を1回にする）
eval `ssh-agent`
ssh-add ~/.ssh/id_ed25519
```

---

## 6. 初回セットアップ（Raspberry Pi 側）

```bash
# 1. SSH接続
ssh secta113@Dealer-bot.local

# 2. ディレクトリ作成と権限設定
mkdir -p ~/Discord_eco_system/data
chmod 700 ~/Discord_eco_system/data

# 3. .env を作成
nano ~/Discord_eco_system/.env
# DISCORD_TOKEN=your_token_here

# 4. 仮想環境を作成・依存ライブラリをインストール
cd ~/Discord_eco_system
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. systemd サービスを設定・有効化
sudo systemctl enable dealerbot.service
sudo systemctl start dealerbot.service
```

---

## 7. 開発・テスト環境の保護（隔離）

ユニットテストの実行時に本番用データベースを誤って書き換えないよう、自動的な隔離の仕組みが導入されています。

### データベースの自動切り替え (`APP_ENV=test`)
`core/storage.py` は、環境変数 `APP_ENV` が `test` に設定されている場合、自動的に **`data/test_db.db`** (テスト専用ファイル) を参照します。本番用の `data/discord_eco_sys.db` には一切アクセスしません。

### テストの実行
`pytest` を実行すると、`tests/conftest.py` によって自動的に隔離環境がセットアップされます。

```powershell
# 自動的に APP_ENV=test が設定され、data/test_db.db で実行される
venv\Scripts\pytest.exe tests
```

> [!CAUTION]
> 手動で調査用のスクリプト等を作成する場合、`SQLiteStorage()` をデフォルト引数で呼び出すと本番DBにアクセスします。安全のため、スクリプト実行前には `os.environ["APP_ENV"] = "test"` を設定することを推奨します。

---

## 8. Python / 開発環境 (共通)

```bash
# 仮想環境の有効化
source venv/bin/activate

# パッケージインストール
pip install -r requirements.txt

# 手動実行（テスト用）
python main.py
```

---

## 8. システム操作（OS）

| 操作 | コマンド |
| :--- | :--- |
| **安全なシャットダウン** | `sudo shutdown -h now` |
| **再起動** | `sudo reboot` |
| **プロセス監視** | `htop` |
| **ディスク使用量確認** | `df -h` |

---

## 9. トラブルシューティング

| 症状 | 原因 | 対処 |
| :--- | :--- | :--- |
| `scp: 接続拒否` | SSH設定未完了 / Pi未起動 | 鍵認証を設定するか疎通確認 |
| `data/` 書き込みエラー | ディレクトリ権限が不足 | `chmod 700 data` |
| Bot が起動しない | `.env` 未作成 / トークン不正 | `journalctl` でエラー確認 |
| DB の `readonly` エラー | WAL モードで書き込み権限なし | `chmod 700 data` |
