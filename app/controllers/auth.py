# app/controllers/auth.py
from app.models.db import get_connection
import bcrypt
from typing import Optional

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False

def authenticate(username: str, password: str) -> Optional[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username=?", (username,))
    row = cur.fetchone()
    conn.close()
    if row and verify_password(password, row["password"]):
        return {"id": row["id"], "username":row["username"], "role":row["role"], "nama":row["nama"], "nip":row["nip"], "email":row["email"]}
    return None

def register_user(nip, nama, email, username, password, role):
    if role not in ("admin","leader","programmer"):
        raise ValueError("Invalid role")
    hashed = hash_password(password)
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO users (nip,nama,email,username,password,role)
            VALUES (?,?,?,?,?,?)
        """, (nip, nama, email, username, hashed, role))
        conn.commit()
    finally:
        conn.close()
