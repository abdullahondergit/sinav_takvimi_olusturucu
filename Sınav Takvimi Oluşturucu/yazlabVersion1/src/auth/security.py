import bcrypt

def hash_password(password: str) -> str:
    """Düz şifreyi bcrypt ile hashler."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(password: str, stored_hash: str) -> bool:
    """Hash’i bcrypt ile doğrular."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    except Exception:
        return False
