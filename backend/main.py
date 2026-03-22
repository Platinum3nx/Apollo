from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import ALLOWED_ORIGINS
from db.bootstrap import ensure_pricing_db_ready
from routers import analyze, explore


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_pricing_db_ready()
    yield


app = FastAPI(title="Apollo API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router, prefix="/api")
app.include_router(explore.router, prefix="/api")
