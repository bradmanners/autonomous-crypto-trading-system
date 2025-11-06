"""
Apply database migration from SQL file
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import DatabaseManager
from sqlalchemy import text

def apply_migration(sql_file_path):
    """Apply a migration SQL file"""
    db = DatabaseManager()

    # Read SQL file
    with open(sql_file_path, 'r') as f:
        sql_content = f.read()

    # Execute SQL
    with db.get_session() as session:
        # Split by semicolons and execute each statement
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]

        for stmt in statements:
            if stmt:
                try:
                    session.execute(text(stmt))
                except Exception as e:
                    print(f"Warning: {e}")
                    print(f"Statement: {stmt[:100]}...")

        session.commit()

    print(f"✅ Migration applied: {sql_file_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python apply_migration.py <sql_file_path>")
        sys.exit(1)

    apply_migration(sys.argv[1])
