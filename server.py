import os
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Literal, Any, Dict

from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

from jose import jwt, JWTError
from passlib.context import CryptContext

from pymongo import MongoClient
from bson import ObjectId

# ----------------------------
# Config
# ----------------------------
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "meatsafe_db")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-secret-in-prod")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

app = FastAPI(title="MeatSafe API")

# CORS (for Expo web + mobile)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------
# Helpers
# ----------------------------
def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def oid(s: str) -> ObjectId:
    try:
        return ObjectId(s)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ObjectId")

def obj_id_str(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc["id"] = str(doc.pop("_id"))
    # normalize nested ObjectIds if present
    for k in ["slaughterhouse_id", "inspector_id"]:
        if k in doc and doc[k] is not None:
            doc[k] = str(doc[k])
    return doc

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = now_utc() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def get_user_by_email(email: str) -> Optional[dict]:
    return db.users.find_one({"email": email.lower().strip()})

def require_role(user: dict, role: str) -> dict:
    if user.get("role") != role:
        raise HTTPException(status_code=403, detail="Forbidden")
    return user

def serialize_user(user: dict) -> dict:
    out = {
        "id": str(user["_id"]),
        "email": user["email"],
        "role": user["role"],
        "slaughterhouse_id": str(user["slaughterhouse_id"]) if user.get("slaughterhouse_id") else None,
        "created_at": user.get("created_at"),
        "updated_at": user.get("updated_at"),
    }
    return out

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.users.find_one({"_id": oid(sub)})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

async def get_current_admin(user: dict = Depends(get_current_user)) -> dict:
    return require_role(user, "admin")

async def get_current_inspector(user: dict = Depends(get_current_user)) -> dict:
    return require_role(user, "inspector")

# ----------------------------
# Seed admin (optional helper endpoint)
# NOTE: For MVP phone-only deploy, we provide a guarded seed endpoint.
# Disable in production by setting ALLOW_SEED=false (default false).
# ----------------------------
ALLOW_SEED = os.getenv("ALLOW_SEED", "false").lower() == "true"

@app.post("/api/admin/seed", tags=["dev"])
def seed_admin(email: str, password: str):
    if not ALLOW_SEED:
        raise HTTPException(status_code=403, detail="Seeding disabled")
    email = email.lower().strip()
    if get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Email already exists")

    doc = {
        "email": email,
        "password_hash": hash_password(password),
        "role": "admin",
        "slaughterhouse_id": None,
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    res = db.users.insert_one(doc)
    user = db.users.find_one({"_id": res.inserted_id})
    return {"user": serialize_user(user)}

# ----------------------------
# Auth
# ----------------------------
@app.post("/api/auth/login", tags=["auth"])
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    email = form_data.username.lower().strip()
    password = form_data.password

    user = get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user["_id"]), "role": user["role"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": serialize_user(user),
    }

# ----------------------------
# Users
# ----------------------------
@app.get("/api/users/me", tags=["users"])
def me(user: dict = Depends(get_current_user)):
    return serialize_user(user)

@app.post("/api/users", tags=["users"])
def create_user(payload: dict, admin: dict = Depends(get_current_admin)):
    email = str(payload.get("email", "")).lower().strip()
    password = str(payload.get("password", ""))
    role = payload.get("role", "inspector")
    slaughterhouse_id = payload.get("slaughterhouse_id")

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")
    if role not in ["admin", "inspector"]:
        raise HTTPException(status_code=400, detail="Invalid role")
    if role == "inspector" and not slaughterhouse_id:
        raise HTTPException(status_code=400, detail="slaughterhouse_id required for inspector")

    if get_user_by_email(email):
        raise HTTPException(status_code=400, detail="Email already exists")

    doc = {
        "email": email,
        "password_hash": hash_password(password),
        "role": role,
        "slaughterhouse_id": oid(slaughterhouse_id) if (role == "inspector") else None,
        "created_at": now_utc(),
        "updated_at": now_utc(),
    }
    res = db.users.insert_one(doc)
    user = db.users.find_one({"_id": res.inserted_id})
    return serialize_user(user)

@app.get("/api/users", tags=["users"])
def list_users(
    role: Optional[str] = Query(default=None),
    slaughterhouse_id: Optional[str] = Query(default=None),
    admin: dict = Depends(get_current_admin),
):
    q: Dict[str, Any] = {}
    if role:
        q["role"] = role
    if slaughterhouse_id:
        q["slaughterhouse_id"] = oid(slaughterhouse_id)

    users = [serialize_user(u) for u in db.users.find(q).sort("created_at", -1)]
    return {"items": users, "total": len(users)}

# ----------------------------
# Slaughterhouses
# ----------------------------
@app.post("/api/slaughterhouses", tags=["slaughterhouses"])
def create_slaughterhouse(payload: dict, admin: dict = Depends(get_current_admin)):
    name = str(payload.get("name", "")).strip()
    code = str(payload.get("code", "")).strip()
    location = payload.get("location")

    if not name or not code:
        raise HTTPException(status_code=400, detail="Name and code required")

    if db.slaughterhouses.find_one({"code": code}):
        raise HTTPException(status_code=400, detail="Code already exists")

    doc = {
        "name": name,
        "code": code,
        "location": str(location).strip() if location else None,
        "created_at": now_utc(),
    }
    res = db.slaughterhouses.insert_one(doc)    sh = db.slaughterhouses.find_one({"_id": res.inserted_id})
    return obj_id_str(sh)

@app.get("/api/slaughterhouses", tags=["slaughterhouses"])
def list_slaughterhouses(admin: dict = Depends(get_current_admin)):
    items = [obj_id_str(s) for s in db.slaughterhouses.find({}).sort("created_at", -1)]
    return {"items": items, "total": len(items)}

@app.get("/api/slaughterhouses/{sh_id}", tags=["slaughterhouses"])
def get_slaughterhouse(sh_id: str, admin: dict = Depends(get_current_admin)):
    sh = db.slaughterhouses.find_one({"_id": oid(sh_id)})
    if not sh:
        raise HTTPException(status_code=404, detail="Not found")
    return obj_id_str(sh)

@app.put("/api/slaughterhouses/{sh_id}", tags=["slaughterhouses"])
def update_slaughterhouse(sh_id: str, payload: dict, admin: dict = Depends(get_current_admin)):
    update: Dict[str, Any] = {}
    for k in ["name", "code", "location"]:
        if k in payload and payload[k] is not None:
            update[k] = str(payload[k]).strip()

    if "code" in update:
        existing = db.slaughterhouses.find_one({"code": update["code"], "_id": {"$ne": oid(sh_id)}})
        if existing:

@app.get("/api/analytics/summary", tags=["analytics"])
def analytics_summary(
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    slaughterhouse_id: Optional[str] = Query(default=None),
    admin: dict = Depends(get_current_admin),
):
    match: Dict[str, Any] = {}
    dt_q: Dict[str, Any] = {}

    if start_date:
        dt_q["$gte"] = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
    if end_date:
        dt_q["$lte"] = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    if dt_q:
        match["seizure_datetime"] = dt_q
    if slaughterhouse_id:
        match["slaughterhouse_id"] = oid(slaughterhouse_id)

    total_cases = db.seizure_records.count_documents(match)

    # ---------- Analytics helper ----------
    by_species = [
        {"species": x["_id"], "count": x["count"]}
        for x in db.seizure_records.aggregate([
            {"$match": match},
            {"$group": {"_id": "$species", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ])
    ]

    by_reason = [
        {"reason": x["_id"], "count": x["count"]}
        for x in db.seizure_records.aggregate([
            {"$match": match},
            {"$group": {"_id": "$reason", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ])
    ]

    by_seizure_type = [
        {"seizure_type": x["_id"], "count": x["count"]}
        for x in db.seizure_records.aggregate([
            {"$match": match},
            {"$group": {"_id": "$seizure_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ])
    ]

    return {
        "total_cases": total_cases,
        "by_species": by_species,
        "by_reason": by_reason,
        "by_seizure_type": by_seizure_type
    }
