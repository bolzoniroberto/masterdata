"""
Migration 002: Aggiungi colonne certified e description per checkpoint/milestone
Permette di distinguere tra checkpoint veloci e milestone certificate
"""
import sqlite3
from pathlib import Path


def migrate(db_path: Path):
    """
    Aggiunge colonne per supporto checkpoint/milestone:
    - certified: BOOLEAN (0 = checkpoint, 1 = milestone)
    - description: TEXT (descrizione dettagliata per milestone)
    """
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # Check se colonne esistono già
        cursor.execute("PRAGMA table_info(import_versions)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'certified' not in columns:
            print("⏳ Aggiunta colonna 'certified' a import_versions...")
            cursor.execute("""
                ALTER TABLE import_versions
                ADD COLUMN certified BOOLEAN DEFAULT 0
            """)
            print("✅ Colonna 'certified' aggiunta")
        else:
            print("ℹ️ Colonna 'certified' già presente")

        if 'description' not in columns:
            print("⏳ Aggiunta colonna 'description' a import_versions...")
            cursor.execute("""
                ALTER TABLE import_versions
                ADD COLUMN description TEXT
            """)
            print("✅ Colonna 'description' aggiunta")
        else:
            print("ℹ️ Colonna 'description' già presente")

        conn.commit()
        print("✅ Migration 002 completata con successo")

    except Exception as e:
        conn.rollback()
        print(f"❌ Errore migration 002: {str(e)}")
        raise
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    # Test migration
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    import config

    print("🧪 Test migration 002...")
    migrate(config.DB_PATH)
