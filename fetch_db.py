import datetime
import os
import shutil
import subprocess

# --- 設定項目 (deploy.py と同期) ---
REMOTE_USER = "secta113"
REMOTE_HOST = "Dealer-bot.local"
REMOTE_DIR = "/home/secta113/Discord_eco_system"
DB_NAME = "discord_eco_sys.db"


def stop_remote_service():
    """リモートのボットサービスを停止する"""
    print(f"🛑 Stopping dealerbot.service on {REMOTE_HOST}...")
    cmd = ["ssh", f"{REMOTE_USER}@{REMOTE_HOST}", "sudo systemctl stop dealerbot.service"]
    try:
        subprocess.run(cmd, check=False)
    except Exception as e:
        print(f"⚠️ Warning: Could not stop service: {e}")


def restart_remote_service():
    """リモートのボットサービスを再起動する"""
    print(f"🔄 Restarting dealerbot.service on {REMOTE_HOST}...")
    cmd = ["ssh", f"{REMOTE_USER}@{REMOTE_HOST}", "sudo systemctl restart dealerbot.service"]
    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"❌ Error: Could not restart service: {e}")


def fetch_db():
    """リモートから本番DBを取得し、ローカルを最新化する"""
    remote_path = f"{REMOTE_DIR}/data/{DB_NAME}"
    local_path = os.path.abspath(f"./data/{DB_NAME}")

    print(f"🚀 Starting database fetch from {REMOTE_HOST}...")

    try:
        # 1. サービスの停止 (DB整合性のため & ロック回避の可能性)
        stop_remote_service()

        # 2. バックアップ
        if os.path.exists(local_path):
            os.makedirs("./backups", exist_ok=True)
            now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            bak_path = os.path.abspath(f"./backups/local_fetch_backup_{DB_NAME}_{now_str}.bak")
            shutil.copy2(local_path, bak_path)
            print(f"📦 Existing local DB backed up to {bak_path}")

        # 3. 一時ファイルとしてダウンロード
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        tmp_local_path = local_path + ".tmp"
        print("📥 Downloading remote DB to temporary file...")
        cmd_scp = ["scp", f"{REMOTE_USER}@{REMOTE_HOST}:{remote_path}", tmp_local_path]
        subprocess.run(cmd_scp, check=True)

        # 4. 本番ファイルへのリネーム
        if os.path.exists(local_path):
            try:
                os.remove(local_path)
            except Exception:
                print("❌ Error: Could not remove local file (WinError 32).")
                print("   The file is locked by another process (Local Bot?).")
                print(f"   Please close any application using {DB_NAME} and try again.")
                return

        os.rename(tmp_local_path, local_path)
        print(f"✅ DB sync completed: {local_path}")

        # サイズの確認
        size_kb = os.path.getsize(local_path) / 1024
        print(f"📊 Final DB size: {size_kb:.1f} KB")

    except Exception as e:
        print(f"❌ Fetch process failed: {e}")
    finally:
        # 5. サービスの再開
        restart_remote_service()


if __name__ == "__main__":
    fetch_db()
