from app.rag import rrf, tokenize
from app.security import create_token, decode_token, hash_password, verify_password

def test_password():
    h=hash_password('StrongPassword123!'); assert verify_password('StrongPassword123!',h); assert not verify_password('wrong',h)
def test_token(): assert decode_token(create_token('u1'))=='u1'
def test_tokenizer():
    t=tokenize('DATABASE_URL AUTH-104 api/v1'); assert 'database_url' in t and 'auth-104' in t
def test_rrf():
    s=rrf(['a','b'],['b','c']); assert s['b']>s['c'] and s['b']>s['a']
