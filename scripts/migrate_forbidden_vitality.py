import json
import sqlite3

db_path = "data/discord_eco_sys.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

cursor.execute("SELECT dobumon_id, traits, genetics, lifespan, max_lifespan FROM dobumons")
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

            if row["lifespan"] != new_lifespan or row["max_lifespan"] != new_lifespan:
                cursor.execute(
                    "UPDATE dobumons SET lifespan = ?, max_lifespan = ? WHERE dobumon_id = ?",
                    (new_lifespan, new_lifespan, row["dobumon_id"]),
                )
                migrated_count += 1
                print(f"Migrated ID {row['dobumon_id']}: {original_lifespan} -> {new_lifespan}")

conn.commit()
print(f"Migrated {migrated_count} the_forbidden dobumons.")
conn.close()
