from passlib.context import CryptContext
from itsdangerous import URLSafeTimedSerializer, BadSignature
from config import SECRET_KEY

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
_signer = URLSafeTimedSerializer(SECRET_KEY)

SESSION_COOKIE = "wc_session"
MAX_AGE = 60 * 60 * 24 * 7  # 7 days


def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


def make_session_token(user_id: str) -> str:
    return _signer.dumps(user_id)


def decode_session_token(token: str) -> str | None:
    try:
        return _signer.loads(token, max_age=MAX_AGE)
    except BadSignature:
        return None


def set_session(response, user_id: str):
    token = make_session_token(user_id)
    response.set_cookie(
        SESSION_COOKIE, token, max_age=MAX_AGE, httponly=True, samesite="lax"
    )


def clear_session(response):
    response.delete_cookie(SESSION_COOKIE)


async def get_current_user(request, db_get_user_by_id):
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    user_id = decode_session_token(token)
    if not user_id:
        return None
    return await db_get_user_by_id(user_id)
