import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import CreditChange
from app.services import user_service


def test_sqlite_connections_enforce_foreign_keys(app):
    assert db.session.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_history_cannot_point_to_a_missing_credit(app):
    db.session.add(CreditChange(credit_id=999, action="created", changes={}))

    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_removing_a_user_keeps_their_history_without_an_author(client, create_credit):
    credit = create_credit()
    author = user_service.find_user("admin")
    # Removed directly in the database, as there is no command to delete accounts
    db.session.execute(text("DELETE FROM users WHERE id = :id"), {"id": author.id})
    db.session.commit()
    db.session.expire_all()

    change = db.session.scalar(db.select(CreditChange).where(CreditChange.credit_id == credit["id"]))
    assert change.user_id is None
