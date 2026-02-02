from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import os
import jwt
from passlib.context import CryptContext
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

# =====================
# ENV
# =====================
load_dotenv()

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "meatsafe_db")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-secret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "8"))

if not MONGO_URL:
    raise RuntimeError("MONGO_URL is missing in environment variables")

# =====================
# APP  (لازم الاسم app)
# =====================
app = FastAPI(
    title="MeatSafe API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================
# DB
# =====================
client = MongoClient(MONGO_URL)
db = client[DB_NAME]
users_col = db["users"]

# =====================
# SECURITY
# =====================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)

def pick_password_hash_field(user: Dict[str, Any]) -> Optional[str]:
    """
    يدعم أسماء مختلفة للحقل في Mongo.
    """
    for key in ["password_hash", "hashed_password", "password"]:
        val = user.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return None

def normalize_email(email: str) -> str:
    return (email or "").strip().lower()

# =====================
# MODELS
# =====================
class UserOut(BaseModel):
    id: str
    email: EmailStr
    role: str
    slaughterhouse_id: Optional[str] = None
    created_at: datetime

# =====================
# AUTH HELPERS
# =====================
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token sub")

    user = users_col.find_one({"_id": oid})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# =====================
# ROUTES
# =====================
@app.get("/")
def root():
    return {"status": "MeatSafe API running"}

# ---------- LOGIN ----------
@app.post("/api/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    print("=== LOGIN DEBUG START ===")
    print("grant_type:", getattr(form_data, "grant_type", None))
    print("username received:", repr(form_data.username))
    print("password length:", len(form_data.password) if form_data.password else None)

    email = normalize_email(form_data.username)
    print("email normalized:", repr(email))

    user = users_col.find_one({"email": email})
    print("user found in DB:", bool(user))

    if user:
        try:
            print("USER KEYS:", list(user.keys()))
            print("EMAIL IN DB:", user.get("email"))
            print("HAS password_hash:", "password_hash" in user)
            print("HAS hashed_password:", "hashed_password" in user)
            print("HAS password:", "password" in user)
        except Exception as e:
            print("ERROR printing user keys:", repr(e))

    if not user:
        print("ERROR: user not found")
        print("=== LOGIN DEBUG END ===")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    stored_hash = pick_password_hash_field(user)
    print("stored hash exists:", bool(stored_hash))
    print("stored hash prefix:", (stored_hash[:12] if stored_hash else None))

    if not stored_hash:
        print("ERROR: No password hash field found on user")
        print("=== LOGIN DEBUG END ===")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    password_ok = False
    try:
        password_ok = verify_password(form_data.password or "", stored_hash)
    except Exception as e:
        print("ERROR verifying password:", repr(e))

    print("password valid:", password_ok)

    if not password_ok:
        print("ERROR: password invalid")
        print("=== LOGIN DEBUG END ===")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    access_token = create_access_token(
        data={"sub": str(user["_id"]), "role": user.get("role", "user")},
        expires_delta=timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
    )

    print("LOGIN SUCCESS")
    print("=== LOGIN DEBUG END ===")

    created_at = user.get("created_at") or datetime.utcnow()
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except Exception:
            created_at = datetime.utcnow()

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user["_id"]),
            "email": user.get("email", email),
            "role": user.get("role", "user"),
            "slaughterhouse_id": user.get("slaughterhouse_id"),
            "created_at": created_at,
        },
    }

# ---------- CURRENT USER ----------
@app.get("/api/users/me", response_model=UserOut)
def get_me(current_user=Depends(get_current_user)):
    created_at = current_user.get("created_at") or datetime.utcnow()
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except Exception:
            created_at = datetime.utcnow()

    return {
        "id": str(current_user["_id"]),
        "email": current_user["email"],
        "role": current_user.get("role", "user"),
        "slaughterhouse_id": current_user.get("slaughterhouse_id"),
        "created_at": created_at,
    }

# ---------- DEBUG: RESET ADMIN PASSWORD ----------
# ⚠️ استعمله فقط مؤقتاً ثم احذفه بعد ما يشتغل login
@app.post("/api/debug/reset-admin-password")
def reset_admin_password():
    email = "admin@meatsafe.com"
    new_password = "Admin123"
    new_hash = hash_password(new_password)

    # نخزّن في password_hash (واضح ومباشر)
    result = users_col.update_one(
        {"email": email},
        {"$set": {"password_hash": new_hash}},
        upsert=False,
    )

    return {
        "email": email,
        "new_password": new_password,
        "hash_created": True,
        "matched": result.matched_count,
        "modified": result.modified_count,
    }
