from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app import crud, schemas

router = APIRouter(
    prefix="/gym/members",
    tags=["Gym Members"]
)


# Database Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# GET ALL MEMBERS
@router.get("/", response_model=list[schemas.GymMemberResponse])
def get_members(db: Session = Depends(get_db)):
    return crud.get_members(db)


# GET ONE MEMBER
@router.get("/{member_id}", response_model=schemas.GymMemberResponse)
def get_member(member_id: UUID, db: Session = Depends(get_db)):
    member = crud.get_member(db, member_id)

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    return member


# CREATE MEMBER
@router.post("/", response_model=schemas.GymMemberResponse)
def create_member(member: schemas.GymMemberCreate, db: Session = Depends(get_db)):
    return crud.create_member(db, member)


# UPDATE MEMBER
@router.put("/{member_id}", response_model=schemas.GymMemberResponse)
def update_member(member_id: UUID,
                  member: schemas.GymMemberUpdate,
                  db: Session = Depends(get_db)):

    updated = crud.update_member(db, member_id, member)

    if not updated:
        raise HTTPException(status_code=404, detail="Member not found")

    return updated


# DELETE MEMBER
@router.delete("/{member_id}")
def delete_member(member_id: UUID, db: Session = Depends(get_db)):

    deleted = crud.delete_member(db, member_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Member not found")

    return {"message": "Member deleted successfully"}