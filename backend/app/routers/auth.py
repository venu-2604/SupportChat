from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from ..models.schemas import UserCreate, UserLogin, TokenResponse
from ..core.security import get_password_hash, verify_password, create_access_token, get_current_user, require_admin
from ..core.config import settings
import pyotp
import psycopg2
from ..db.postgres import get_postgres_connection


router = APIRouter()


@router.post("/auth/register", response_model=TokenResponse)
def register(payload: UserCreate):
    conn = get_postgres_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE email=%s", (payload.email,))
    if cur.fetchone():
        raise HTTPException(status_code=400, detail="Email already registered")
    secret = pyotp.random_base32()
    cur.execute(
        "INSERT INTO users (email, password_hash, twofa_secret) VALUES (%s, %s, %s) RETURNING id",
        (payload.email, get_password_hash(payload.password), secret),
    )
    conn.commit()
    cur.close(); conn.close()
    token = create_access_token(subject=payload.email)
    return TokenResponse(access_token=token)


@router.post("/auth/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    conn = get_postgres_connection()
    cur = conn.cursor()
    cur.execute("SELECT password_hash, twofa_secret FROM users WHERE email=%s", (form_data.username,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    password_hash, twofa_secret = row
    if not verify_password(form_data.password, password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    # If 2FA is set, require subsequent verify endpoint
    if twofa_secret:
        # In a full implementation, issue a temp token and require /2fa/verify
        token = create_access_token(subject=form_data.username)
        return TokenResponse(access_token=token)
    token = create_access_token(subject=form_data.username)
    return TokenResponse(access_token=token)


@router.get("/auth/me")
def me(user=Depends(get_current_user)):
    return user


@router.post("/auth/2fa/enable")
def enable_2fa(user=Depends(get_current_user)):
    current_email = user["email"]
    conn = get_postgres_connection()
    cur = conn.cursor()
    secret = pyotp.random_base32()
    cur.execute("UPDATE users SET twofa_secret=%s WHERE email=%s", (secret, current_email))
    conn.commit()
    cur.close(); conn.close()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=current_email, issuer_name=settings.TWOFA_ISSUER)
    return {"otpauth_uri": uri}


@router.post("/auth/2fa/verify")
def verify_2fa(email: str, otp: str):
    conn = get_postgres_connection()
    cur = conn.cursor()
    cur.execute("SELECT twofa_secret FROM users WHERE email=%s", (email,))
    row = cur.fetchone()
    cur.close(); conn.close()
    if not row or not row[0]:
        raise HTTPException(status_code=400, detail="2FA not enabled")
    totp = pyotp.TOTP(row[0])
    if not totp.verify(otp):
        raise HTTPException(status_code=400, detail="Invalid OTP")
    token = create_access_token(subject=email)
    return TokenResponse(access_token=token)


