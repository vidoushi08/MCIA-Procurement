from sqlalchemy import Column, Integer, String
from src.app.database import Base

class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String(100), unique=True, index=True, nullable=False)
    department_category = Column(String(100), nullable=False)
    sub_category = Column(String(100), nullable=True)
    quantity_in_stock = Column(Integer, default=0, nullable=False)
