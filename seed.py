"""Idempotent sample records for local development; do not run in production."""
from faker import Faker

from app import create_app
from app.extensions import db
from app.models import Task, User

fake = Faker()
Faker.seed(42)


def seed_database():
    app = create_app()
    with app.app_context():
        demo_accounts = [
            ("demo_julius", "DemoPass123!"),
            ("demo_alex", "DemoPass456!"),
        ]
        for username, password in demo_accounts:
            user = db.session.execute(
                db.select(User).filter_by(username=username)
            ).scalar_one_or_none()
            if user is None:
                user = User(username=username)
                user.password = password
                db.session.add(user)
                db.session.flush()

            # Each user gets starter tasks only if they have none already.
            existing = db.session.execute(
                db.select(Task.id).filter_by(user_id=user.id).limit(1)
            ).first()
            if existing is None:
                for index in range(5):
                    db.session.add(Task(
                        user_id=user.id,
                        title=fake.sentence(nb_words=4).rstrip("."),
                        description=fake.paragraph(nb_sentences=2),
                        is_completed=(index % 2 == 0),
                    ))
        db.session.commit()
        print("Seed complete: two demo users and up to five tasks each.")
        print("Demo accounts use their published development-only passwords.")


if __name__ == "__main__":
    seed_database()
