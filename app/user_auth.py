from werkzeug.security import generate_password_hash, check_password_hash
from app.database import session, User

def register_user(username, email, password, vacation_days, role, monthly_vacation_days):
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
    new_user = User(username=username, email=email, hashed_password=hashed_password, vacation_days=vacation_days, role=role, monthly_vacation_days=monthly_vacation_days)
    session.add(new_user)
    session.commit()
    print(f"Registered user {username} with {vacation_days} vacation days and role {role}")

def login_user(username, password):
    user = session.query(User).filter_by(username=username).first()
    if user and check_password_hash(user.hashed_password, password):
        return user
    return None
