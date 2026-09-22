from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import inspect as sa_inspect, text as sql_text
from .core.config import get_settings
from .core.database import engine, Base, SessionLocal
from .models import User, Laptop, Intern, Allocation
from .models.allocation import uq_allocations_active_laptop
from .routes import laptops, interns, allocations, auth, dashboard, excel_io
from .models.seed import seed_all

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger("laptop_allocation")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info(
        "Database backend=%s url=%s",
        settings.database_dialect,
        settings.DATABASE_URL,
    )
    inspector = sa_inspect(engine)
    if (
        uq_allocations_active_laptop is not None
        and not inspector.has_index("allocations", "uq_allocations_active_laptop")
    ):
        try:
            uq_allocations_active_laptop.create(bind=engine)
        except Exception:
            logger.warning(
                "Could not create unique active-allocation index "
                "(possible duplicate ACTIVE allocations in existing data). "
                "Application-level double-allocation checks remain active."
            )
    laptop_columns = {c["name"] for c in inspector.get_columns("laptops")}
    for col in ("processor", "ram", "storage", "operating_system"):
        if col not in laptop_columns:
            with engine.begin() as conn:
                conn.execute(
                    sql_text(
                        f"ALTER TABLE laptops ADD COLUMN {col} VARCHAR(100)"
                    )
                )
            logger.info("Added missing column 'laptops.%s'", col)
    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(laptops.router, prefix=settings.API_V1_PREFIX)
app.include_router(interns.router, prefix=settings.API_V1_PREFIX)
app.include_router(allocations.router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard.router, prefix=settings.API_V1_PREFIX)
app.include_router(excel_io.router, prefix=settings.API_V1_PREFIX)
app.include_router(excel_io.export_router, prefix=settings.API_V1_PREFIX)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled exception on %s %s: %s",
        request.method,
        request.url.path,
        exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


@app.get("/")
def root():
    return {"message": "Laptop Allocation Management System API", "version": settings.VERSION}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
