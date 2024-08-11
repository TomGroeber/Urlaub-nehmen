import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.user_auth import register_user

# Benutzer registrieren mit einer bestimmten Anzahl von Urlaubstagen, Rollen und monatlichen Urlaubstagen
register_user("user1", "user1@example.com", "user1pass", 14, "Dreher", 2)
register_user("user2", "user2@example.com", "user2pass", 14, "Dreher", 2)
register_user("user3", "user3@example.com", "user3pass", 14, "Dreher", 2)
register_user("user4", "user4@example.com", "user4pass", 14, "Fräser", 2)
register_user("user5", "user5@example.com", "user5pass", 14, "Fräser", 2)
register_user("user6", "user6@example.com", "user6pass", 14, "Schweißer", 2)
register_user("admin", "admin@example.com", "adminpass", 0, "Admin", 0)  # Admin hat keine Urlaubstage benötigt

print("Test users created successfully.")
