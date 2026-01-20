from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, List, Literal, Optional

import logging
import os

from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    Depends,
    FastAPI,
    HTTPException,
    status,
)
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware


# ---------------------------------------------------------------------------
# Environment & DB setup
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

# JWT settings (MVP defaults – can be moved to env later if needed)
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "changeme-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


# ---------------------------------------------------------------------------
# Security & auth helpers
# ---------------------------------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    user_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

Role = Literal["admin", "inspector"]
Species = Literal["bovine", "ovine", "caprine", "porcine", "camelid", "other"]
SeizedPart = Literal[
    "carcass",
    "liver",
    "lung",
    "heart",
    "kidney",
    "spleen",
    "head",
    "other",
]
SeizureType = Literal["partial", "total"]
Unit = Literal["kg", "g", "pieces"]


class UserBase(BaseModel):
    email: EmailStr
    role: Role
    slaughterhouse_id: Optional[str] = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: Role
    slaughterhouse_id: Optional[str] = None


class UserOut(UserBase):
    id: str
    created_at: datetime


class UserInDB(UserBase):
    id: str
    password_hash: str
    created_at: datetime
    updated_at: datetime


class SlaughterhouseBase(BaseModel):
    name: str
    code: str
    location: Optional[str] = None


class SlaughterhouseCreate(SlaughterhouseBase):
    pass


class SlaughterhouseUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    location: Optional[str] = None


class SlaughterhouseOut(SlaughterhouseBase):
    id: str
    created_at: datetime


class SeizureBase(BaseModel):
    seizure_datetime: datetime = Field(default_factory=datetime.utcnow)
    species: Species
    seized_part: SeizedPart
    seizure_type: SeizureType
    reason: str
    quantity: int
    unit: Unit
    notes: Optional[str] = None
    photos: Optional[List[str]] = None  # base64 strings


class SeizureCreate(SeizureBase):
    pass


class SeizureOut(SeizureBase):
    id: str
    slaughterhouse_id: str
    inspector_id: str
    created_at: datetime
    updated_at: datetime


class PaginatedSeizures(BaseModel):
    items: List[SeizureOut]
    total: int
    page: int
    page_size: int


class AnalyticsSummary(BaseModel):
    total_cases: int
    by_species: List[dict]
    by_reason: List[dict]
    by_seizure_type: List[dict]


# ---------------------------------------------------------------------------
# Utility functions for MongoDB <-> Pydantic
# ---------------------------------------------------------------------------


def mongo_obj_to_user(doc: dict) -> UserOut:
    return UserOut(
        id=str(doc["_id"]),
        email=doc["email"],
        role=doc["role"],
        slaughterhouse_id=(str(doc["slaughterhouse_id"]) if doc.get("slaughterhouse_id") else None),
        created_at=doc["created_at"],
    )


def mongo_obj_to_seizure(doc: dict) -> SeizureOut:
    return SeizureOut(
        id=str(doc["_id"]),
        seizure_datetime=doc["seizure_datetime"],
        species=doc["species"],
        seized_part=doc["seized_part"],
        seizure_type=doc["seizure_type"],
        reason=doc["reason"],
        quantity=doc["quantity"],
        unit=doc["unit"],
        notes=doc.get("notes"),
        photos=doc.get("photos", []),
        slaughterhouse_id=str(doc["slaughterhouse_id"]),
        inspector_id=str(doc["inspector_id"]),
        created_at=doc["created_at"],
        updated_at=doc["updated_at"],
    )


def mongo_obj_to_slaughterhouse(doc: dict) -> SlaughterhouseOut:
    return SlaughterhouseOut(
        id=str(doc["_id"]),
        name=doc["name"],
        code=doc["code"],
        location=doc.get("location"),
        created_at=doc["created_at"],
    )


# ---------------------------------------------------------------------------
# Auth & user dependency
# ---------------------------------------------------------------------------


async def get_user_by_id(user_id: str) -> Optional[dict]:
    from bson import ObjectId

    return await db.users.find_one({"_id": ObjectId(user_id)})


async def get_user_by_email(email: str) -> Optional[dict]:
    return await db.users.find_one({"email": email.lower()})


async def authenticate_user(email: str, password: str) -> Optional[dict]:
    user = await get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Identifiants invalides",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception

    user = await get_user_by_id(token_data.user_id)  # type: ignore[arg-type]
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: dict = Depends(get_current_user)) -> dict:
    # Placeholder for future "is_active" logic
    return current_user


async def get_current_admin(current_user: dict = Depends(get_current_active_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès réservé à l'administrateur")
    return current_user


async def get_current_inspector(current_user: dict = Depends(get_current_active_user)) -> dict:
    if current_user.get("role") != "inspector":
        raise HTTPException(status_code=403, detail="Accès réservé à l'inspecteur")
    return current_user


# ---------------------------------------------------------------------------
# FastAPI app & router
# ---------------------------------------------------------------------------

app = FastAPI()
api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root() -> dict:
    return {"message": "MeatSafe API"}


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


@api_router.post("/auth/login", response_model=LoginResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Any:
    # OAuth2PasswordRequestForm impose des champs "username" et "password"
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")

    access_token = create_access_token(data={"sub": str(user["_id"])})
    user_out = mongo_obj_to_user(user)
    return {"access_token": access_token, "token_type": "bearer", "user": user_out}


# ---------------------------------------------------------------------------
# User routes (admin)
# ---------------------------------------------------------------------------


@api_router.post("/users", response_model=UserOut)
async def create_user(user_in: UserCreate, admin: dict = Depends(get_current_admin)) -> UserOut:  # noqa: ARG001
    existing = await get_user_by_email(user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email déjà utilisé")

    now = datetime.utcnow()
    doc = {
        "email": user_in.email.lower(),
        "password_hash": get_password_hash(user_in.password),
        "role": user_in.role,
        "slaughterhouse_id": user_in.slaughterhouse_id,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.users.insert_one(doc)
    doc["_id"] = result.inserted_id
    return mongo_obj_to_user(doc)


class UsersQuery(BaseModel):
    role: Optional[Role] = None
    slaughterhouse_id: Optional[str] = None


@api_router.get("/users", response_model=List[UserOut])
async def list_users(
    role: Optional[Role] = None,
    slaughterhouse_id: Optional[str] = None,
    admin: dict = Depends(get_current_admin),  # noqa: ARG001
) -> List[UserOut]:
    query: dict[str, Any] = {}
    if role:
        query["role"] = role
    if slaughterhouse_id:
        query["slaughterhouse_id"] = slaughterhouse_id

    cursor = db.users.find(query)
    docs = await cursor.to_list(1000)
    return [mongo_obj_to_user(doc) for doc in docs]


@api_router.get("/users/me", response_model=UserOut)
async def get_me(current_user: dict = Depends(get_current_active_user)) -> UserOut:
    return mongo_obj_to_user(current_user)


# ---------------------------------------------------------------------------
# Slaughterhouse routes (admin)
# ---------------------------------------------------------------------------


@api_router.post("/slaughterhouses", response_model=SlaughterhouseOut)
async def create_slaughterhouse(
    sh_in: SlaughterhouseCreate,
    admin: dict = Depends(get_current_admin),  # noqa: ARG001
) -> SlaughterhouseOut:
    now = datetime.utcnow()
    doc = {
        "name": sh_in.name,
        "code": sh_in.code,
        "location": sh_in.location,
        "created_at": now,
    }
    result = await db.slaughterhouses.insert_one(doc)
    doc["_id"] = result.inserted_id
    return mongo_obj_to_slaughterhouse(doc)


@api_router.get("/slaughterhouses", response_model=List[SlaughterhouseOut])
async def list_slaughterhouses(
    admin: dict = Depends(get_current_admin),  # noqa: ARG001
) -> List[SlaughterhouseOut]:
    cursor = db.slaughterhouses.find()
    docs = await cursor.to_list(1000)
    return [mongo_obj_to_slaughterhouse(doc) for doc in docs]


@api_router.get("/slaughterhouses/{sh_id}", response_model=SlaughterhouseOut)
async def get_slaughterhouse(
    sh_id: str,
    admin: dict = Depends(get_current_admin),  # noqa: ARG001
) -> SlaughterhouseOut:
    from bson import ObjectId

    doc = await db.slaughterhouses.find_one({"_id": ObjectId(sh_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Abattoir introuvable")
    return mongo_obj_to_slaughterhouse(doc)


@api_router.put("/slaughterhouses/{sh_id}", response_model=SlaughterhouseOut)
async def update_slaughterhouse(
    sh_id: str,
    sh_update: SlaughterhouseUpdate,
    admin: dict = Depends(get_current_admin),  # noqa: ARG001
) -> SlaughterhouseOut:
    from bson import ObjectId

    update_data = {k: v for k, v in sh_update.model_dump(exclude_unset=True).items()}
    if not update_data:
        raise HTTPException(status_code=400, detail="Aucune donnée à mettre à jour")

    result = await db.slaughterhouses.find_one_and_update(
        {"_id": ObjectId(sh_id)},
        {"$set": update_data},
        return_document=True,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Abattoir introuvable")
    return mongo_obj_to_slaughterhouse(result)


@api_router.delete("/slaughterhouses/{sh_id}", status_code=204)
async def delete_slaughterhouse(
    sh_id: str,
    admin: dict = Depends(get_current_admin),  # noqa: ARG001
) -> None:
    from bson import ObjectId

    seizures_count = await db.seizure_records.count_documents({"slaughterhouse_id": sh_id})
    if seizures_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Impossible de supprimer un abattoir avec des saisies associées",
        )
    result = await db.slaughterhouses.delete_one({"_id": ObjectId(sh_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Abattoir introuvable")


# ---------------------------------------------------------------------------
# Seizure routes
# ---------------------------------------------------------------------------


@api_router.post("/seizures", response_model=SeizureOut)
async def create_seizure(
    seizure_in: SeizureCreate,
    inspector: dict = Depends(get_current_inspector),
) -> SeizureOut:
    if not inspector.get("slaughterhouse_id"):
        raise HTTPException(status_code=400, detail="Inspecteur non assigné à un abattoir")

    now = datetime.utcnow()
    doc = {
        "seizure_datetime": seizure_in.seizure_datetime or datetime.utcnow(),
        "species": seizure_in.species,
        "seized_part": seizure_in.seized_part,
        "seizure_type": seizure_in.seizure_type,
        "reason": seizure_in.reason,
        "quantity": seizure_in.quantity,
        "unit": seizure_in.unit,
        "notes": seizure_in.notes,
        "photos": seizure_in.photos or [],
        "slaughterhouse_id": inspector["slaughterhouse_id"],
        "inspector_id": inspector["_id"],
        "created_at": now,
        "updated_at": now,
    }
    result = await db.seizure_records.insert_one(doc)
    doc["_id"] = result.inserted_id
    return mongo_obj_to_seizure(doc)


@api_router.get("/seizures", response_model=PaginatedSeizures)
async def list_seizures(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    species: Optional[Species] = None,
    reason: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_active_user),
) -> PaginatedSeizures:
    query: dict[str, Any] = {}

    # Scope by role
    if current_user.get("role") == "inspector":
        query["slaughterhouse_id"] = current_user.get("slaughterhouse_id")
    # admin: see all

    if start_date or end_date:
        query["seizure_datetime"] = {}
        if start_date:
            query["seizure_datetime"]["$gte"] = start_date
        if end_date:
            query["seizure_datetime"]["$lte"] = end_date
    if species:
        query["species"] = species
    if reason:
        query["reason"] = reason

    total = await db.seizure_records.count_documents(query)

    skip = (page - 1) * page_size
    cursor = (
        db.seizure_records.find(query)
        .sort("seizure_datetime", -1)
        .skip(skip)
        .limit(page_size)
    )
    docs = await cursor.to_list(page_size)
    items = [mongo_obj_to_seizure(doc) for doc in docs]

    return PaginatedSeizures(items=items, total=total, page=page, page_size=page_size)


@api_router.get("/seizures/{seizure_id}", response_model=SeizureOut)
async def get_seizure(
    seizure_id: str,
    current_user: dict = Depends(get_current_active_user),
) -> SeizureOut:
    from bson import ObjectId

    doc = await db.seizure_records.find_one({"_id": ObjectId(seizure_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Saisie introuvable")

    if current_user.get("role") == "inspector":
        if doc.get("slaughterhouse_id") != current_user.get("slaughterhouse_id"):
            raise HTTPException(status_code=403, detail="Accès refusé à cette saisie")

    return mongo_obj_to_seizure(doc)


@api_router.delete("/seizures/{seizure_id}", status_code=204)
async def delete_seizure(
    seizure_id: str,
    admin: dict = Depends(get_current_admin),  # noqa: ARG001
) -> None:
    from bson import ObjectId

    result = await db.seizure_records.delete_one({"_id": ObjectId(seizure_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Saisie introuvable")


# ---------------------------------------------------------------------------
# Analytics routes (admin)
# ---------------------------------------------------------------------------


@api_router.get("/analytics/summary", response_model=AnalyticsSummary)
async def analytics_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    slaughterhouse_id: Optional[str] = None,
    admin: dict = Depends(get_current_admin),  # noqa: ARG001
) -> AnalyticsSummary:
    # Build base match query
    match: dict[str, Any] = {}
    if start_date or end_date:
        match["datetime"] = {}
        if start_date:
            match["datetime"]["$gte"] = start_date
        if end_date:
            match["datetime"]["$lte"] = end_date
    if slaughterhouse_id:
        match["slaughterhouse_id"] = slaughterhouse_id

    pipeline_base = []
    if match:
        pipeline_base.append({"$match": match})

    # Total cases
    total_cases = await db.seizure_records.count_documents(match or {})

    # By species
    pipeline_species = pipeline_base + [
        {"$group": {"_id": "$species", "count": {"$sum": 1}}},
        {"$project": {"_id": 0, "species": "$_id", "count": 1}},
    ]
    by_species_docs = await db.seizure_records.aggregate(pipeline_species).to_list(None)

    # By reason
    pipeline_reason = pipeline_base + [
        {"$group": {"_id": "$reason", "count": {"$sum": 1}}},
        {"$project": {"_id": 0, "reason": "$_id", "count": 1}},
    ]
    by_reason_docs = await db.seizure_records.aggregate(pipeline_reason).to_list(None)

    # By seizure type
    pipeline_type = pipeline_base + [
        {"$group": {"_id": "$seizure_type", "count": {"$sum": 1}}},
        {"$project": {"_id": 0, "seizure_type": "$_id", "count": 1}},
    ]
    by_type_docs = await db.seizure_records.aggregate(pipeline_type).to_list(None)

    return AnalyticsSummary(
        total_cases=total_cases,
        by_species=by_species_docs,
        by_reason=by_reason_docs,
        by_seizure_type=by_type_docs,
    )


# ---------------------------------------------------------------------------
# App wiring & middleware
# ---------------------------------------------------------------------------

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client() -> None:
    client.close()
