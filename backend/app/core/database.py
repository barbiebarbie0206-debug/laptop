from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import get_settings

settings = get_settings()

dialect = settings.database_dialect

connect_args = {}
if dialect == "sqlite":
    connect_args = {"check_same_thread": False}
elif dialect == "mysql":
    connect_args = {"charset": "utf8mb4"}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True if dialect in ("postgresql", "mysql") else False,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
