
from sqlalchemy.orm import Session

from app.database import engine
from app.models.models import User
from app.auth.security import hash_password


ADMIN_NAME = "System Admin"
ADMIN_EMAIL = "admin26@example.com"
ADMIN_PASSWORD = "AdminTest@2610"
ADMIN_PHONE = "9876543211"


def create_admin():
    with Session(engine) as db:
        existing_user = (
            db.query(User)
            .filter(User.email == ADMIN_EMAIL)
            .first()
        )

        if existing_user:
            if existing_user.role == "Admin":
                print("Admin account already exists.")
                print(f"Email: {ADMIN_EMAIL}")
            else:
                print(
                    "This email already belongs to a non-admin user. "
                    "Please choose another admin email."
                )
            return

        admin = User(
            name=ADMIN_NAME,
            email=ADMIN_EMAIL,
            phone=ADMIN_PHONE,
            password_hash=hash_password(ADMIN_PASSWORD),
            role="Admin",
            is_active=True,
            is_approved=True,
        )

        db.add(admin)
        db.commit()

        print("Admin account created successfully!")
        print(f"Email: {ADMIN_EMAIL}")
        print(f"Password: {ADMIN_PASSWORD}")


if __name__ == "__main__":
    create_admin()
