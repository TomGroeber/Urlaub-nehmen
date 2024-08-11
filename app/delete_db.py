import os

if os.path.exists("vacation_manager.db"):
    os.remove("vacation_manager.db")
    print("Old database deleted.")
else:
    print("The file does not exist")
