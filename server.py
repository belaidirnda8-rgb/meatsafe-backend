from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any, Dict, List, Literal
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
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-secret-please-use-32-chars-min")
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
slaughterhouses_col = db["slaughterhouses"]
seizures_col = db["seizures"]

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
    for key in ["password_hash", "hashed_password", "password"]:
        val = user.get(key)
        if isinstance(val, str) and val.strip():
            return val
    return None

def normalize_email(email: str) -> str:
    return (email or "").strip().lower()

def oid_or_400(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")

def to_iso(dt: Any) -> str:
    if isinstance(dt, datetime):
        return dt.isoformat()
    if isinstance(dt, str):
        return dt
    return datetime.utcnow().isoformat()

# =====================
# MODELS
# =====================
Role = Literal["admin", "inspector"]

class UserOut(BaseModel):
    id: str
    email: EmailStr
    role: Role
    slaughterhouse_id: Optional[str] = None
    created_at: datetime

class SlaughterhouseIn(BaseModel):
    name: str = Field(min_length=1)
    code: str = Field(min_length=1)
    location: Optional[str] = None

class SlaughterhouseOut(BaseModel):
    id: str
    name: str
    code: str
    location: Optional[str] = None
    created_at: datetime

class CreateUserIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=4)
    role: Role
    slaughterhouse_id: Optional[str] = None

class UserListOut(BaseModel):
    id: str
    email: EmailStr
    role: Role
    slaughterhouse_id: Optional[str] = None
    created_at: datetime

class SeizureIn(BaseModel):
    species: str
    seized_part: str
    seizure_type: str
    reason: str
    quantity: float
    unit: str
    notes: Optional[str] = None
    photos: Optional[List[str]] = None  # base64 list

class SeizureOut(BaseModel):
    id: str
    species: str
    seized_part: str
    seizure_type: str
    reason: str
    quantity: float
    unit: str
    notes: Optional[str] = None
    photos: Optional[List[str]] = None
    slaughterhouse_id: Optional[str] = None
    inspector_id: Optional[str] = None
    created_at: datetime

class AnalyticsSummary(BaseModel):
    total_cases: int
    by_species: List[Dict[str, Any]]
    by_reason: List[Dict[str, Any]]
    by_seizure_type: List[Dict[str, Any]]

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

    oid = oid_or_400(user_id)
    user = users_col.find_one({"_id": oid})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

def require_admin(current_user=Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return current_user

# =====================
# ROUTES
# =====================
@app.get("/")
def root():
    return {"status": "MeatSafe API running"}

# ---------- LOGIN ----------
@app.post("/api/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    email = normalize_email(form_data.username)
    user = users_col.find_one({"email": email})

    if not user:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    stored_hash = pick_password_hash_field(user)
    if not stored_hash:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    try:
        ok = verify_password(form_data.password or "", stored_hash)
    except Exception:
        ok = False

    if not ok:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    access_token = create_access_token(
        data={"sub": str(user["_id"]), "role": user.get("role", "inspector")},
        expires_delta=timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
    )

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
            "role": user.get("role", "inspector"),
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
        "role": current_user.get("role", "inspector"),
        "slaughterhouse_id": current_user.get("slaughterhouse_id"),
        "created_at": created_at,
    }

# ---------- ADMIN: SLAUGHTERHOUSES ----------
@app.get("/api/slaughterhouses", response_model=List[SlaughterhouseOut])
def list_slaughterhouses(_: dict = Depends(require_admin)):
    docs = list(slaughterhouses_col.find().sort("created_at", -1))
    out = []
    for d in docs:
        created_at = d.get("created_at") or datetime.utcnow()
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except Exception:
                created_at = datetime.utcnow()
        out.append({
            "id": str(d["_id"]),
            "name": d.get("name", ""),
            "code": d.get("code", ""),
            "location": d.get("location"),
            "created_at": created_at,
        })
    return out

@app.post("/api/slaughterhouses", response_model=SlaughterhouseOut)
def create_slaughterhouse(payload: SlaughterhouseIn, _: dict = Depends(require_admin)):
    now = datetime.utcnow()
    doc = {
        "name": payload.name.strip(),
        "code": payload.code.strip(),
        "location": payload.location.strip() if payload.location else None,
        "created_at": now,
        "updated_at": now,
    }
    res = slaughterhouses_col.insert_one(doc)
    doc["_id"] = res.inserted_id
    return {
        "id": str(doc["_id"]),
        "name": doc["name"],
        "code": doc["code"],
        "location": doc["location"],
        "created_at": doc["created_at"],
    }

@app.put("/api/slaughterhouses/{slaughterhouse_id}", response_model=SlaughterhouseOut)
def update_slaughterhouse(slaughterhouse_id: str, payload: SlaughterhouseIn, _: dict = Depends(require_admin)):
    oid = oid_or_400(slaughterhouse_id)
    now = datetime.utcnow()
    update = {
        "name": payload.name.strip(),
        "code": payload.code.strip(),
        "location": payload.location.strip() if payload.location else None,
        "updated_at": now,
    }
    r = slaughterhouses_col.update_one({"_id": oid}, {"$set": update})
    if r.matched_count == 0:
        raise HTTPException(status_code=404, detail="Slaughterhouse not found")
    d = slaughterhouses_col.find_one({"_id": oid})
    created_at = d.get("created_at") or now
    if isinstance(created_at, str):
        try:
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except Exception:
            created_at = now
    return {
        "id": str(d["_id"]),
        "name": d.get("name", ""),
        "code": d.get("code", ""),
        "location": d.get("location"),
        "created_at": created_at,
    }

@app.delete("/api/slaughterhouses/{slaughterhouse_id}")
def delete_slaughterhouse(slaughterhouse_id: str, _: dict = Depends(require_admin)):
    oid = oid_or_400(slaughterhouse_id)
    r = slaughterhouses_col.delete_one({"_id": oid})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Slaughterhouse not found")
    return {"ok": True}

# ---------- ADMIN: USERS ----------
@app.get("/api/users", response_model=List[UserListOut])
def list_users(
    role: Optional[str] = Query(default=None),
    _: dict = Depends(require_admin),
):
    q: Dict[str, Any] = {}
    if role:
        q["role"] = role
    docs = list(users_col.find(q).sort("created_at", -1))
    out = []
    for d in docs:
        created_at = d.get("created_at") or datetime.utcnow()
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except Exception:
                created_at = datetime.utcnow()
        out.append({
            "id": str(d["_id"]),
            "email": d.get("email", ""),
            "role": d.get("role", "inspector"),
            "slaughterhouse_id": d.get("slaughterhouse_id"),
            "created_at": created_at,
        })
    return out

@app.post("/api/users", response_model=UserListOut)
def create_user(payload: CreateUserIn, _: dict = Depends(require_admin)):
    email = normalize_email(payload.email)
    exists = users_col.find_one({"email": email})
    if exists:
        raise HTTPException(status_code=409, detail="Email already exists")

    if payload.role == "inspector" and not payload.slaughterhouse_id:
        raise HTTPException(status_code=422, detail="slaughterhouse_id is required for inspector")

    sh_id = payload.slaughterhouse_id
    if sh_id:
        sh_oid = oid_or_400(sh_id)
        sh = slaughterhouses_col.find_one({"_id": sh_oid})
        if not sh:
            raise HTTPException(status_code=404, detail="Slaughterhouse not found")

    now = datetime.utcnow()
    doc = {
        "email": email,
        "password_hash": hash_password(payload.password),
        "role": payload.role,
        "slaughterhouse_id": sh_id,
        "created_at": now,
        "updated_at": now,
    }
    res = users_col.insert_one(doc)
    doc["_id"] = res.inserted_id

    return {
        "id": str(doc["_id"]),
        "email": doc["email"],
        "role": doc["role"],
        "slaughterhouse_id": doc.get("slaughterhouse_id"),
        "created_at": doc["created_at"],
    }

# ---------- INSPECTOR/ADMIN: SEIZURES ----------
@app.get("/api/seizures", response_model=List[SeizureOut])
def list_seizures(current_user=Depends(get_current_user)):
    role = current_user.get("role", "inspector")
    q: Dict[str, Any] = {}

    if role == "inspector":
        # inspector يرى فقط الخاص به أو الخاص بمذبحة معيّنة
        sh_id = current_user.get("slaughterhouse_id")
        if sh_id:
            q["slaughterhouse_id"] = sh_id
        q["inspector_id"] = str(current_user["_id"])

    docs = list(seizures_col.find(q).sort("created_at", -1))
    out = []
    for d in docs:
        created_at = d.get("created_at") or datetime.utcnow()
        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except Exception:
                created_at = datetime.utcnow()
        out.append({
            "id": str(d["_id"]),
            "species": d.get("species", ""),
            "seized_part": d.get("seized_part", ""),
            "seizure_type": d.get("seizure_type", ""),
            "reason": d.get("reason", ""),
            "quantity": float(d.get("quantity", 0)),
            "unit": d.get("unit", ""),
            "notes": d.get("notes"),
            "photos": d.get("photos") or [],
            "slaughterhouse_id": d.get("slaughterhouse_id"),
            "inspector_id": d.get("inspector_id"),
            "created_at": created_at,
        })
    return out

@app.post("/api/seizures", response_model=SeizureOut)
def create_seizure(payload: SeizureIn, current_user=Depends(get_current_user)):
    role = current_user.get("role", "inspector")
    now = datetime.utcnow()

    # منطق: inspector لازم يكون مربوط بمذبح
    sh_id = current_user.get("slaughterhouse_id")
    if role == "inspector" and not sh_id:
        raise HTTPException(status_code=422, detail="Inspector has no slaughterhouse_id")

    doc = {
        "species": payload.species,
        "seized_part": payload.seized_part,
        "seizure_type": payload.seizure_type,
        "reason": payload.reason,
        "quantity": payload.quantity,
        "unit": payload.unit,
        "notes": payload.notes,
        "photos": payload.photos or [],
        "slaughterhouse_id": sh_id,
        "inspector_id": str(current_user["_id"]),
        "created_at": now,
        "updated_at": now,
    }

    res = seizures_col.insert_one(doc)
    doc["_id"] = res.inserted_id

    return {
        "id": str(doc["_id"]),
        "species": doc["species"],
        "seized_part": doc["seized_part"],
        "seizure_type": doc["seizure_type"],
        "reason": doc["reason"],
        "quantity": float(doc["quantity"]),
        "unit": doc["unit"],
        "notes": doc.get("notes"),
        "photos": doc.get("photos") or [],
        "slaughterhouse_id": doc.get("slaughterhouse_id"),
        "inspector_id": doc.get("inspector_id"),
        "created_at": doc["created_at"],
    }

# ---------- ADMIN: ANALYTICS ----------
@app.get("/api/analytics/summary", response_model=AnalyticsSummary)
def analytics_summary(_: dict = Depends(require_admin)):
    total = seizures_col.count_documents({})

    by_species = list(seizures_col.aggregate([
        {"$group": {"_id": "$species", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$project": {"_id": 0, "species": "$_id", "count": 1}},
    ]))

    by_reason = list(seizures_col.aggregate([
        {"$group": {"_id": "$reason", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$project": {"_id": 0, "reason": "$_id", "count": 1}},
    ]))

    by_seizure_type = list(seizures_col.aggregate([
        {"$group": {"_id": "$seizure_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$project": {"_id": 0, "seizure_type": "$_id", "count": 1}},
    ]))

    return {
        "total_cases": int(total),
        "by_species": by_species,
        "by_reason": by_reason,
        "by_seizure_type": by_seizure_type,
    }

# ---------- DEBUG: RESET ADMIN PASSWORD ----------
@app.post("/api/debug/reset-admin-password")
def reset_admin_password():
    email = "admin@meatsafe.com"
    new_password = "Admin123"
    new_hash = hash_password(new_password)

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
