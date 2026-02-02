from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
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
ACCESS_TOKEN_EXPIRE_HOURS = 8

# =====================
# APP  ⚠️ مهم: لازم يكون اسمه app
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
users_col = db.users

# =====================
# SECURITY
# =====================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)

# =====================
# MODELS
# =====================
class UserOut(BaseModel):
    id: str
    email: EmailStr
    role: str
    slaughterhouse_id: Optional[str]
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

    user = users_col.find_one({"_id": ObjectId(user_id)})
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
    print("username received:", repr(form_data.username))
    print("password length:", len(form_data.password) if form_data.password else None)

    user = users_col.find_one({"email": form_data.username.lower()})
    print("user found in DB:", bool(user))

    if not user:
        print("ERROR: user not found")
        print("=== LOGIN DEBUG END ===")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    password_ok = verify_password(form_data.password, user["password_hash"])
    print("password valid:", password_ok)

    if not password_ok:
        print("ERROR: password invalid")
        print("stored hash:", user["password_hash"])
        print("=== LOGIN DEBUG END ===")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    access_token = create_access_token(
        data={"sub": str(user["_id"]), "role": user["role"]},
        expires_delta=timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
    )

    print("LOGIN SUCCESS")
    print("=== LOGIN DEBUG END ===")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "role": user["role"],
            "slaughterhouse_id": user.get("slaughterhouse_id"),
            "created_at": user["created_at"],
        },
    }

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "role": user.get("role", "user"),
            "slaughterhouse_id": user.get("slaughterhouse_id"),
            "created_at": user.get("created_at", datetime.utcnow()),
        },
    }

# ---------- CURRENT USER ----------
@app.get("/api/users/me", response_model=UserOut)
def get_me(current_user=Depends(get_current_user)):
    return {
        "id": str(current_user["_id"]),
        "email": current_user["email"],
        "role": current_user.get("role", "user"),
        "slaughterhouse_id": current_user.get("slaughterhouse_id"),
        "created_at": current_user.get("created_at", datetime.utcnow()),
    }
