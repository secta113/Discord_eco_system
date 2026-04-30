import os
import subprocess
import zipfile

# --- 設定項目 ---
REMOTE_USER = "secta113"
REMOTE_HOST = "Dealer-bot.local"
REMOTE_DIR = "/home/secta113/Discord_eco_system"

# 転送対象のディレクトリとファイル
TARGETS = [
    "main.py",
    "cogs/",
    "core/",
    "logic/",
    "managers/",
    "data/",
    "requirements.txt",
]


def download_db() -> bool:
    """リモートから本番DBを取得し、ローカルを最新化する"""
    db_name = "discord_eco_sys.db"
    remote_path = f"{REMOTE_DIR}/data/{db_name}"
    local_path = f"./data/{db_name}"

    print(f"📥 Pulling production DB from {REMOTE_HOST}...")
    os.makedirs("./data", exist_ok=True)

    # 既存のローカルDBがある場合は念のためバックアップ (別フォルダへ)
    if os.path.exists(local_path):
        os.makedirs("./backups", exist_ok=True)
        import shutil

        bak_path = f"./backups/local_predeploy_{db_name}.bak"
        shutil.copy2(local_path, bak_path)
        print(f"📦 Local DB backed up to {bak_path}")

    cmd = ["scp", f"{REMOTE_USER}@{REMOTE_HOST}:{remote_path}", local_path]
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ DB synced: {remote_path} -> {local_path}")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Error: Remote DB ({remote_path}) could not be retrieved from {REMOTE_HOST}.")
        print(
            "💡 Safety Abort: To prevent overwriting remote data with an empty local DB, deployment is stopped."
        )
        return False


def local_migrate():
    """ローカルに落としたDBに対してスキーマ更新（マイグレーション）を適用する"""
    print("⚙️ Running local database migration...")
    try:
        from core.handlers.sql_handler import init_db

        db_path = "data/discord_eco_sys.db"
        init_db(db_path)
        print("✅ Migration / Initialization completed.")
    except Exception as e:
        print(f"❌ Migration failed: {e}")


def stop_service():
    """リモートのボットサービスを停止する"""
    print(f"🛑 Stopping dealerbot.service on {REMOTE_HOST}...")
    cmd = ["ssh", f"{REMOTE_USER}@{REMOTE_HOST}", "sudo systemctl stop dealerbot.service"]
    try:
        subprocess.run(cmd, check=False)  # 失敗しても続行（サービス未登録等の場合）
    except Exception as e:
        print(f"⚠️ Warning: Could not stop service: {e}")


def restart_service():
    """リモートのボットサービスを再起動する"""
    print(f"🔄 Restarting dealerbot.service on {REMOTE_HOST}...")
    cmd = ["ssh", f"{REMOTE_USER}@{REMOTE_HOST}", "sudo systemctl restart dealerbot.service"]
    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"❌ Error: Could not restart service: {e}")


def update_remote_dependencies():
    """リモート環境の依存関係を更新する"""
    print(f"📦 Updating dependencies on {REMOTE_HOST}...")
    # リモートの venv 内の pip を使用
    remote_pip = f"{REMOTE_DIR}/venv/bin/pip"
    # --no-cache-dir を指定して Pi Zero のメモリ消費を抑える
    cmd = f"cd {REMOTE_DIR} && {remote_pip} install --no-cache-dir -r requirements.txt"
    cmd_ssh = ["ssh", f"{REMOTE_USER}@{REMOTE_HOST}", cmd]
    try:
        subprocess.run(cmd_ssh, check=True)
        print("✅ Dependencies updated.")
    except Exception as e:
        print(f"⚠️ Warning: Dependency update failed: {e}")


def follow_logs():
    """リモートのログをリアルタイムで表示する (Ctrl+Cで終了)"""
    print(f"📋 Following dealerbot.service logs on {REMOTE_HOST}...")
    print("💡 Press Ctrl+C to stop following logs (the bot will keep running).")
    # -f: follow, -u: unit, -n 50: 最初の50行を表示
    cmd = ["ssh", f"{REMOTE_USER}@{REMOTE_HOST}", "journalctl -f -u dealerbot.service -n 50"]
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 Stopped following logs. The bot is still running in the background.")


def create_deploy_zip(zip_path, targets):
    """デプロイ対象をZIPにまとめる (__pycache__などは除外)"""
    print(f"📦 Creating archive {zip_path}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for target in targets:
            clean_target = target.rstrip("/")
            if not os.path.exists(clean_target):
                print(f"⚠️ Warning: {clean_target} not found. Skipping...")
                continue

            if os.path.isdir(clean_target):
                for root, dirs, files in os.walk(clean_target):
                    # __pycache__ を除外
                    if "__pycache__" in dirs:
                        dirs.remove("__pycache__")

                    for file in files:
                        # .pyc ファイルなどを除外
                        if file.endswith((".pyc", ".pyo", ".pyd")):
                            continue
                        file_path = os.path.join(root, file)
                        # ZIP内のパスは常にスラッシュ(/)に統一する (WindowsからLinuxへの転送対策)
                        archive_name = os.path.relpath(file_path, ".").replace("\\", "/")
                        zipf.write(file_path, archive_name)
            else:
                zipf.write(clean_target, os.path.relpath(clean_target, "."))


def run_ci():
    """CI スクリプトを実行し、成功するか確認する"""
    print("🧪 Running CI checks (Lint & Tests)...")
    try:
        # venv の python を使用して実行 (自動修正 --fix を有効化)
        venv_python = os.path.join(os.path.dirname(__file__), "venv", "Scripts", "python.exe")
        subprocess.run([venv_python, "run_ci.py", "--fix"], check=True)
        print("✅ CI passed. Proceeding to deploy.")
        return True
    except subprocess.CalledProcessError:
        print("❌ CI failed. Deployment aborted. Please fix the issues and try again.")
        return False


def deploy():
    # 0. CI チェックを実行 (テストや Lint が失敗した場合は中断)
    if not run_ci():
        return

    print(f"🚀 Starting deployment to {REMOTE_HOST}...")
    zip_name = "deploy_package.zip"

    try:
        # 0. サービスを停止 (DBのロックを解除)
        stop_service()

        # 1. 本番DBをローカルに同期
        if not download_db():
            print("❌ Deployment Aborted (DB Sync Failure).")
            return

        # 2. ローカルでマイグレーション実行
        local_migrate()

        # セキュリティ強化: パーミッションの付与 (所有者のみに制限)
        print("🔐 Hardening permissions on remote directories (Owner only)...")
        # 700: 所有者のみ rwx, 他は一切アクセス不可
        subprocess.run(
            ["ssh", f"{REMOTE_USER}@{REMOTE_HOST}", f"chmod -R 700 {REMOTE_DIR}"], check=False
        )

        # 4. 旧構造のクリア (ディレクトリごと削除してクリーンにする)
        print("🧹 Clearing remote directories for a fresh deployment...")
        dirs_to_clean = ["cogs", "core", "logic", "managers"]
        for d in dirs_to_clean:
            subprocess.run(
                ["ssh", f"{REMOTE_USER}@{REMOTE_HOST}", f"rm -rf {REMOTE_DIR}/{d}"], check=False
            )

        # 5. 改めてディレクトリ構造を作成
        print(f"📁 Creating remote directory structure on {REMOTE_HOST}...")
        dirs_to_create = [
            f"{REMOTE_DIR}/data",
            f"{REMOTE_DIR}/cogs",
            f"{REMOTE_DIR}/core/handlers",
            f"{REMOTE_DIR}/core/models",
            f"{REMOTE_DIR}/core/ui",
            f"{REMOTE_DIR}/core/utils",
            f"{REMOTE_DIR}/logic/blackjack",
            f"{REMOTE_DIR}/logic/chinchiro",
            f"{REMOTE_DIR}/logic/economy",
            f"{REMOTE_DIR}/logic/poker",
            f"{REMOTE_DIR}/managers",
        ]
        subprocess.run(
            ["ssh", f"{REMOTE_USER}@{REMOTE_HOST}", "mkdir -p " + " ".join(dirs_to_create)],
            check=True,
        )

        # 6. ZIPアーカイブの作成 (ローカル)
        create_deploy_zip(zip_name, TARGETS)

        # 7. アーカイブをアップロード
        print(f"📤 Transferring {zip_name}...")
        cmd_scp = ["scp", zip_name, f"{REMOTE_USER}@{REMOTE_HOST}:{REMOTE_DIR}/"]
        subprocess.run(cmd_scp, check=True)

        # 8. リモートで解凍
        print(f"📦 Extracting {zip_name} on {REMOTE_HOST}...")
        # unzip -o: 上書き強制, rm: ZIPの削除
        cmd_remote = f"cd {REMOTE_DIR} && unzip -o {zip_name} && rm {zip_name}"
        cmd_ssh = ["ssh", f"{REMOTE_USER}@{REMOTE_HOST}", cmd_remote]
        subprocess.run(cmd_ssh, check=True)
        print("✅ Extraction completed.")

        # 9. リモートの依存関係を更新
        update_remote_dependencies()

    except Exception as e:
        print(f"❌ Deployment failed: {e}")
    finally:
        # 7. サービスを再開・検証
        restart_service()
        # ローカルのZIPを削除
        if os.path.exists(zip_name):
            os.remove(zip_name)

    print("\n✨ Deployment completed!")
    # 自動的にログの追跡を開始 (Ctrl+C で中断しても、プロセス自体は背後で動き続けます)
    follow_logs()


if __name__ == "__main__":
    deploy()
