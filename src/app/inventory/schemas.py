from pydantic import BaseModel
from typing import Optional

class ItemCreate(BaseModel):
    item_name: str
    department_category: str
    sub_category: Optional[str] = None
    quantity_in_stock: int

class ItemResponse(ItemCreate):
    id: int

    class Config:
        from_attributes = True
