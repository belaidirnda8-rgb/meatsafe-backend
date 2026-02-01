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
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", "8"))

if not MONGO_URL:
    raise RuntimeError("MONGO_URL is missing in environment variables")

# =====================
# APP
# =====================
app = FastAPI(
    title="MeatSafe API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS (اختياري لكن مهم للتطبيق)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # في الإنتاج حط دوميناتك فقط
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

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

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
    slaughterhouse_id: Optional[str] = None
    created_at: datetime

# =====================
# HELPERS
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
        user = users_col.find_one({"_id": ObjectId(user_id)})
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid user id")

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user

# =====================
# ROUTES
# =====================
@app.get("/")
def root():
    return {"status": "MeatSafe API running"}

@app.post("/api/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    email = (form_data.username or "").strip().lower()
    password = form_data.password or ""

    user = users_col.find_one({"email": email})

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    if "password_hash" not in user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User record missing password_hash",
        )

    if not verify_password(password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
        )

    access_token = create_access_token(
        data={"sub": str(user["_id"]), "role": user.get("role", "user")},
        expires_delta=timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
    )

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

@app.get("/api/users/me", response_model=UserOut)
def get_me(current_user=Depends(get_current_user)):
    return {
        "id": str(current_user["_id"]),
        "email": current_user["email"],
        "role": current_user.get("role", "user"),
        "slaughterhouse_id": current_user.get("slaughterhouse_id"),
        "created_at": current_user.get("created_at", datetime.utcnow()),
    }
