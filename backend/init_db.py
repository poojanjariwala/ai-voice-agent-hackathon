import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

# Windows consoles often use cp1252 which cannot print emoji output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.models import Base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./business_voice_agents.db")

print(f"📦 Initializing database: {DATABASE_URL}")

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)

print("📝 Creating tables...")
Base.metadata.create_all(bind=engine)

print("✅ Database initialized successfully!")
print("📊 Tables created:")
print("   ├─ businesses")
print("   ├─ calls")
print("   ├─ conversations")
print("   └─ analytics")
