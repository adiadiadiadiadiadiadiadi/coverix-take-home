from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.db.database import engine, Base
from sqlalchemy import text

from app.routers.chat import router as chat_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    
    try:
        with engine.begin() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_enum 
                    WHERE enumlabel = 'vin_or_year_make_body' 
                    AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'vehiclestep')
                );
            """))
            exists = result.scalar()
            
            if not exists:
                conn.execute(text("ALTER TYPE vehiclestep ADD VALUE 'vin_or_year_make_body'"))
    except Exception:
        pass
    
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3003"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)