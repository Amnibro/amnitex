"""auth: HMAC-signed cookie issuance and verification for the sample project."""
import hashlib,hmac
SECRET=b'fixture-secret-do-not-use-in-production'
def issue(user_id:str)->str:
    sig=hmac.new(SECRET,user_id.encode(),hashlib.sha256).hexdigest()
    return f'{user_id}.{sig}'
def verify(token:str)->bool:
    if '.' not in token:return False
    user_id,sig=token.rsplit('.',1)
    expected=hmac.new(SECRET,user_id.encode(),hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig,expected)
