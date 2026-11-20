import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.app.database import engine, Base, add_missing_columns, backfill_legacy_procurement_lines

from src.app import audit as audit_models
from src.app.auth import router as auth_router
from src.app.users import models as user_models, router as user_router
from src.app.inventory import models as inventory_models, router as inventory_router
from src.app.requisitions import models as req_models, router as req_router
from src.app.tenders import models as tender_models, router as tender_router
from src.app.finance import models as finance_models, router as finance_router
from src.app.finance import scheduler as sla_scheduler
from src.app.remarks import models as remark_models, router as remark_router

Base.metadata.create_all(bind=engine)
add_missing_columns()
backfill_legacy_procurement_lines()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    sla_task = None
    if os.getenv("SLA_CHECK_ENABLED", "true").lower() == "true":
        sla_task = asyncio.create_task(sla_scheduler.sla_check_loop(sla_scheduler.interval_seconds_from_env()))
    try:
        yield
    finally:
        if sla_task:
            sla_task.cancel()


app = FastAPI(
    title="MCIA Stationery Procurement & Inventory System",
    description="Automated stock deduction, 3-tier signatures, and AI vendor comparison.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(user_router.router)
app.include_router(inventory_router.router)
app.include_router(req_router.router)
app.include_router(tender_router.router)
app.include_router(finance_router.router)
app.include_router(remark_router.router)

@app.get("/")
def read_root():
    return {"status": "MCIA Procurement Engine Online"}

