from sqlalchemy.orm import Session
from app.models import GymMember
from app.schemas import GymMemberCreate, GymMemberUpdate


def get_members(db: Session):
    return db.query(GymMember).all()


def get_member(db: Session, member_id):
    return db.query(GymMember).filter(GymMember.id == member_id).first()


def create_member(db: Session, member: GymMemberCreate):
    db_member = GymMember(**member.model_dump())
    db.add(db_member)
    db.commit()
    db.refresh(db_member)
    return db_member


def update_member(db: Session, member_id, member: GymMemberUpdate):
    db_member = get_member(db, member_id)

    if not db_member:
        return None

    updates = member.model_dump(exclude_unset=True)

    for key, value in updates.items():
        setattr(db_member, key, value)

    db.commit()
    db.refresh(db_member)

    return db_member


def delete_member(db: Session, member_id):
    db_member = get_member(db, member_id)

    if not db_member:
        return None

    db.delete(db_member)
    db.commit()

    return db_member