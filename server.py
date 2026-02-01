# create_or_update_admin.py
import os
from datetime import datetime
from pymongo import MongoClient
from passlib.context import CryptContext
from dotenv import load_dotenv

load_dotenv()

# ====== إعداداتك ======
EMAIL = "admin@meatsafe.com"
PASSWORD = "Admin123"   # بدّل كلمة السر هنا
ROLE = "admin"
SLAUGHTERHOUSE_ID = None  # اتركها None للـ admin العام

# ====== ENV ======
MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "meatsafe_db")

if not MONGO_URL:
    raise RuntimeError("MONGO_URL غير موجود. ضعه في Environment أو ملف .env")

# bcrypt limit (72 bytes)
if len(PASSWORD.encode("utf-8")) > 72:
    raise ValueError("Password too long for bcrypt (must be <= 72 bytes)")

# ====== Hash ======
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
password_hash = pwd_context.hash(PASSWORD)

# ====== DB اتصال ======
client = MongoClient(MONGO_URL)
db = client[DB_NAME]
users_col = db.users

now = datetime.utcnow()

# ====== Upsert (إنشاء أو تحديث) ======
result = users_col.update_one(
    {"email": EMAIL.lower()},
    {
        "$set": {
            "email": EMAIL.lower(),
            "password_hash": password_hash,
            "role": ROLE,
            "slaughterhouse_id": SLAUGHTERHOUSE_ID,
            "updated_at": now,
        },
        "$setOnInsert": {
            "created_at": now,
        },
    },
    upsert=True,
)

print("✅ Done")
print("Email:", EMAIL.lower())
print("Password:", PASSWORD)
print("Hash:", password_hash)
print("Matched:", result.matched_count, "| Modified:", result.modified_count, "| UpsertedId:", result.upserted_id)
