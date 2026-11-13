from src.app.database import SessionLocal, engine, Base
from src.app.users.models import User
from src.app.inventory.models import InventoryItem

# Ensure tables exist before inserting data
Base.metadata.create_all(bind=engine)

def seed_database():
    db = SessionLocal()
    try:
        # 1. Seed Standard MCIA Users (if not already present)
        if db.query(User).count() == 0:
            sample_users = [
                User(full_name="Mr. Ishwar", email="ishwar.admin@mcia.mu", department="Procurement", role="ADMIN"),
                User(full_name="Mrs. Devi", email="devi.head@mcia.mu", department="Finance", role="DEPT_HEAD"),
                User(full_name="Vidoushi Soobug", email="vidoushi.staff@mcia.mu", department="Finance", role="STAFF"),
                User(full_name="Rohan Beeharry", email="rohan.staff@mcia.mu", department="IT", role="STAFF")
            ]
            db.add_all(sample_users)
            db.commit()
            print("Sample MCIA users added.")
        else:
            print("Users already exist. Skipping user seed.")

        # 2. Seed Department-Categorized Office Stationery
        if db.query(InventoryItem).count() == 0:
            sample_stationery = [
                InventoryItem(item_name="A4 Printing Paper (500 Sheets)", department_category="Finance", sub_category="Paper Products", quantity_in_stock=50),
                InventoryItem(item_name="Blue Ballpoint Pens (Box of 12)", department_category="Finance", sub_category="Writing Instruments", quantity_in_stock=30),
                InventoryItem(item_name="Heavy Duty Lever Arch Files", department_category="Finance", sub_category="Filing Supplies", quantity_in_stock=0),
                InventoryItem(item_name="USB Flash Drives 32GB", department_category="IT", sub_category="IT Accessories", quantity_in_stock=15),
                InventoryItem(item_name="Whiteboard Markers (Pack of 4)", department_category="IT", sub_category="Writing Instruments", quantity_in_stock=0),
                InventoryItem(item_name="Stapler & Staple Pins Set", department_category="Procurement", sub_category="Desk Accessories", quantity_in_stock=25)
            ]
            db.add_all(sample_stationery)
            db.commit()
            print("Sample MCIA stationery catalog added.")
        else:
            print("Inventory already exists. Skipping stationery seed.")

    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
