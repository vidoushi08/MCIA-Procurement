"""Set or reset the login password for an existing user.

Usage (from the repo root):
    .\\venv\\Scripts\\python.exe scripts\\set_password.py user@example.com
"""
import getpass
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.app.database import SessionLocal  # noqa: E402
from src.app.security import hash_password  # noqa: E402
from src.app.users.models import User  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: set_password.py <email>")
        return 1
    email = sys.argv[1].strip().lower()
    password = getpass.getpass("New password (min 8 characters): ")
    if len(password) < 8:
        print("Password must be at least 8 characters.")
        return 1
    if password != getpass.getpass("Confirm password: "):
        print("Passwords do not match.")
        return 1

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            print(f"No user found with email {email}.")
            return 1
        user.password_hash = hash_password(password)
        db.commit()
        print(f"Password set for {email}.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
