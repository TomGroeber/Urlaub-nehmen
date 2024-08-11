import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import init_db, session, Settings

# Initialisieren der Datenbank
init_db()

# Ensure that settings are initialized
def initialize_settings():
    settings = session.query(Settings).first()
    if not settings:
        settings = Settings(dreher_limit=2, fraeser_limit=2, schweisser_limit=2)
        session.add(settings)
        session.commit()

initialize_settings()

print("Datenbank initialisiert.")
