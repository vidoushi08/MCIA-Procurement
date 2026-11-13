from fastapi import FastAPI
from src.app.database import engine, Base

from src.app.users import models as user_models
from src.app.inventory import models as inventory_models
from src.app.requisitions import models as req_models
from src.app.tenders import models as tender_models
from src.app.finance import models as finance_models

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="MCIA Stationery Procurement & Inventory System",
    description="Automated stock deduction, 3-tier signatures, and AI vendor comparison.",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"status": "MCIA Procurement Engine Online"}
