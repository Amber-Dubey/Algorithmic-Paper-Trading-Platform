import bcrypt
from database.models import SessionLocal, User

def hash_password(password: str) -> str:
    """Hash a plain text password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against the hashed database version."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def register_user(username: str, password: str) -> bool:
    """Register a new user with a starting balance of $100,000.00."""
    session = SessionLocal()
    try:
        existing_user = session.query(User).filter_by(username=username).first()
        if existing_user:
            return False  # Username already taken
        
        pwd_hash = hash_password(password)
        new_user = User(username=username, password_hash=pwd_hash, balance=100000.0)
        session.add(new_user)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        return False
    finally:
        session.close()

def authenticate_user(username: str, password: str):
    """Authenticate user credentials and return the user object or None."""
    session = SessionLocal()
    try:
        user = session.query(User).filter_by(username=username).first()
        if user and verify_password(password, user.password_hash):
            return user
        return None
    finally:
        session.close()