import json
import os
import shutil
import sqlite3

backup_db = "backups/local_fetch_backup_discord_eco_sys.db_20260429_194938.bak"
current_db = "data/discord_eco_sys.db"

# Restore from backup
shutil.copy(backup_db, current_db)

conn = sqlite3.connect(current_db)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT dobumon_id, traits, genetics, lifespan FROM dobumons")
rows = cursor.fetchall()
migrated_count = 0

for row in rows:
    traits_str = row["traits"]
    if traits_str:
        traits = json.loads(traits_str)
        if "the_forbidden" in traits:
            genetics_str = row["genetics"]
            genetics = json.loads(genetics_str) if genetics_str else {}
            forbidden_depth = genetics.get("forbidden_depth", 0)

            # 発生した寿命 × 禁忌深度
            original_lifespan = row["lifespan"]
            new_lifespan = max(1.0, float(int(original_lifespan * max(1, forbidden_depth))))

            cursor.execute(
                "UPDATE dobumons SET lifespan = ?, max_lifespan = ? WHERE dobumon_id = ?",
                (new_lifespan, new_lifespan, row["dobumon_id"]),
            )
            migrated_count += 1
            print(f"Migrated ID {row['dobumon_id']}: {original_lifespan} -> {new_lifespan}")

conn.commit()
print(f"Migrated {migrated_count} the_forbidden dobumons.")
conn.close()
