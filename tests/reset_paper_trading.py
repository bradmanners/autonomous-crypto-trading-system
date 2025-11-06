"""
Reset paper trading state for testing
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import DatabaseManager
from sqlalchemy import text

db = DatabaseManager()

with db.get_session() as session:
    # Reset capital to 100,000
    session.execute(text("""
        UPDATE paper_trading_config
        SET current_capital = 100000
        WHERE config_id = (SELECT config_id FROM paper_trading_config ORDER BY config_id DESC LIMIT 1)
    """))

    # Clear all positions
    session.execute(text("DELETE FROM paper_positions"))

    session.commit()
    print("✅ Reset complete:")
    print("   - Capital reset to $100,000")
    print("   - All positions cleared")
