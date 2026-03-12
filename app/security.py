from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__truncate_error=False,  # important
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)