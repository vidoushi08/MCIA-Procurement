from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.app.database import engine, Base

from src.app.users import models as user_models, router as user_router
from src.app.inventory import models as inventory_models, router as inventory_router
from src.app.requisitions import models as req_models, router as req_router
from src.app.tenders import models as tender_models, router as tender_router
from src.app.finance import models as finance_models, router as finance_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MCIA Stationery Procurement & Inventory System",
    description="Automated stock deduction, 3-tier signatures, and AI vendor comparison.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router.router)
app.include_router(inventory_router.router)
app.include_router(req_router.router)
app.include_router(tender_router.router)
app.include_router(finance_router.router)

@app.get("/")
def read_root():
    return {"status": "MCIA Procurement Engine Online"}

