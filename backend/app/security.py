from datetime import datetime,timedelta,timezone
import jwt
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from app.config import settings
ph=PasswordHash.recommended(); DUMMY_HASH=ph.hash('dummy-password')
def hash_password(p): return ph.hash(p)
def verify_password(p,h): return ph.verify(p,h)
def create_token(user_id):
    now=datetime.now(timezone.utc)
    return jwt.encode({'sub':user_id,'iat':now,'exp':now+timedelta(minutes=settings.access_token_expire_minutes)},settings.jwt_secret_key,algorithm=settings.jwt_algorithm)
def decode_token(token):
    try: data=jwt.decode(token,settings.jwt_secret_key,algorithms=[settings.jwt_algorithm])
    except InvalidTokenError as e: raise ValueError('Invalid or expired token') from e
    if not data.get('sub'): raise ValueError('Missing token subject')
    return str(data['sub'])
