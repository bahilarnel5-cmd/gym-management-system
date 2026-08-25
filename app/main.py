import uuid
from datetime import datetime, date
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pydantic import EmailStr
from app.auth import hash_password, verify_password, create_access_token, decode_token, require_role
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import engine, SessionLocal
from app.models import GymMember, GymCoach, GymMembershipPlan, GymMembership, GymPayment, GymSettings, GymUser, GymPtSession, GymRenewalRequest
from sqlalchemy.dialects.postgresql import UUID
app = FastAPI(title="Gym Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def read_root():
    return {"message": "Gym Management API is running"}


@app.get("/health/db")
def check_db():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"database": "connected"}
    except Exception as e:
        return {"database": "error", "detail": str(e)}


# ---------- MEMBERS ----------

class MemberIn(BaseModel):
    organization_id: uuid.UUID
    member_code: str
    full_name: str
    email: Optional[str] = None
    mobile_phone: str
    status: str = "active"


class MemberUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    mobile_phone: Optional[str] = None
    status: Optional[str] = None


@app.get("/gym_members/")
def list_members(payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        members = db.query(GymMember).all()
        return [
            {
                "id": str(m.id),
                "member_code": m.member_code,
                "full_name": m.full_name,
                "email": m.email,
                "mobile_phone": m.mobile_phone,
                "status": m.status,
            }
            for m in members
        ]
    finally:
        db.close()

@app.get("/auth/me")
def get_me(payload: dict = Depends(decode_token)):
    return payload


@app.get("/gym_members/unclaimed/")
def list_unclaimed_members():
    db = SessionLocal()
    try:
        claimed_ids = db.query(GymUser.member_id).filter(GymUser.member_id.isnot(None)).subquery()
        members = db.query(GymMember).filter(GymMember.id.notin_(claimed_ids)).all()
        return [
            {"id": str(m.id), "full_name": m.full_name, "member_code": m.member_code}
            for m in members
        ]
    finally:
        db.close()

@app.post("/gym_members/")
def create_member(member: MemberIn, payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        new_member = GymMember(
            id=uuid.uuid4(),
            organization_id=member.organization_id,
            member_code=member.member_code,
            full_name=member.full_name,
            email=member.email,
            mobile_phone=member.mobile_phone,
            status=member.status,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(new_member)
        db.commit()
        db.refresh(new_member)
        return {"id": str(new_member.id), "full_name": new_member.full_name}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@app.get("/gym_members/{member_id}")
def get_member(member_id: uuid.UUID, payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        m = db.query(GymMember).filter(GymMember.id == member_id).first()
        if not m:
            raise HTTPException(status_code=404, detail="Member not found")
        return {
            "id": str(m.id),
            "member_code": m.member_code,
            "full_name": m.full_name,
            "email": m.email,
            "mobile_phone": m.mobile_phone,
            "status": m.status,
        }
    finally:
        db.close()


@app.put("/gym_members/{member_id}")
def update_member(member_id: uuid.UUID, update: MemberUpdate):
    db = SessionLocal()
    try:
        m = db.query(GymMember).filter(GymMember.id == member_id).first()
        if not m:
            raise HTTPException(status_code=404, detail="Member not found")
        for field, value in update.dict(exclude_unset=True).items():
            setattr(m, field, value)
        m.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(m)
        return {"id": str(m.id), "full_name": m.full_name}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@app.delete("/gym_members/{member_id}")
def delete_member(member_id: uuid.UUID, payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        m = db.query(GymMember).filter(GymMember.id == member_id).first()
        if not m:
            raise HTTPException(status_code=404, detail="Member not found")
        db.delete(m)
        db.commit()
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


# ---------- COACHES ----------

class CoachIn(BaseModel):
    organization_id: uuid.UUID
    full_name: str
    specialization: str
    hourly_rate: float
    mobile_contact: str
    shift_schedule: Optional[str] = None


class CoachUpdate(BaseModel):
    full_name: Optional[str] = None
    specialization: Optional[str] = None
    hourly_rate: Optional[float] = None
    mobile_contact: Optional[str] = None
    shift_schedule: Optional[str] = None


@app.get("/gym_coaches/")
def list_coaches():  
    db = SessionLocal()
    try:
        coaches = db.query(GymCoach).all()
        return [
            {
                "id": str(c.id),
                "full_name": c.full_name,
                "specialization": c.specialization,
                "hourly_rate": float(c.hourly_rate),
                "mobile_contact": c.mobile_contact,
                "shift_schedule": c.shift_schedule,
            }
            for c in coaches
        ]
    finally:
        db.close()


@app.post("/gym_coaches/")
def create_coach(coach: CoachIn, payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        new_coach = GymCoach(
            id=uuid.uuid4(),
            organization_id=coach.organization_id,
            full_name=coach.full_name,
            specialization=coach.specialization,
            hourly_rate=coach.hourly_rate,
            mobile_contact=coach.mobile_contact,
            shift_schedule=coach.shift_schedule,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(new_coach)
        db.commit()
        db.refresh(new_coach)
        return {"id": str(new_coach.id), "full_name": new_coach.full_name}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@app.get("/gym_coaches/{coach_id}")
def get_coach(coach_id: uuid.UUID, payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        c = db.query(GymCoach).filter(GymCoach.id == coach_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Coach not found")
        return {
            "id": str(c.id),
            "full_name": c.full_name,
            "specialization": c.specialization,
            "hourly_rate": float(c.hourly_rate),
            "mobile_contact": c.mobile_contact,
            "shift_schedule": c.shift_schedule,
        }
    finally:
        db.close()


@app.put("/gym_coaches/{coach_id}")
def update_coach(coach_id: uuid.UUID, update: CoachUpdate, payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        c = db.query(GymCoach).filter(GymCoach.id == coach_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Coach not found")
        for field, value in update.dict(exclude_unset=True).items():
            setattr(c, field, value)
        c.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(c)
        return {"id": str(c.id), "full_name": c.full_name}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@app.delete("/gym_coaches/{coach_id}")
def delete_coach(coach_id: uuid.UUID, payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        c = db.query(GymCoach).filter(GymCoach.id == coach_id).first()
        if not c:
            raise HTTPException(status_code=404, detail="Coach not found")
        db.delete(c)
        db.commit()
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


# ---------- MEMBERSHIP PLANS ----------

class PlanIn(BaseModel):
    organization_id: uuid.UUID
    name: str
    price: float
    billing_cycle: str = "monthly"
    features: Optional[str] = None
    is_active: bool = True


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    billing_cycle: Optional[str] = None
    features: Optional[str] = None
    is_active: Optional[bool] = None


@app.get("/gym_membership_plans/")
def list_plans():
    db = SessionLocal()
    try:
        plans = db.query(GymMembershipPlan).all()
        return [
            {
                "id": str(p.id),
                "name": p.name,
                "price": float(p.price),
                "billing_cycle": p.billing_cycle,
                "features": p.features,
                "is_active": p.is_active,
            }
            for p in plans
        ]
    finally:
        db.close()


@app.post("/gym_membership_plans/")
def create_plan(plan: PlanIn, payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        new_plan = GymMembershipPlan(
            id=uuid.uuid4(),
            organization_id=plan.organization_id,
            name=plan.name,
            price=plan.price,
            billing_cycle=plan.billing_cycle,
            features=plan.features,
            is_active=plan.is_active,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(new_plan)
        db.commit()
        db.refresh(new_plan)
        return {"id": str(new_plan.id), "name": new_plan.name}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@app.get("/gym_membership_plans/{plan_id}")
def get_plan(plan_id: uuid.UUID, payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        p = db.query(GymMembershipPlan).filter(GymMembershipPlan.id == plan_id).first()
        if not p:
            raise HTTPException(status_code=404, detail="Plan not found")
        return {
            "id": str(p.id),
            "name": p.name,
            "price": float(p.price),
            "billing_cycle": p.billing_cycle,
            "features": p.features,
            "is_active": p.is_active,
        }
    finally:
        db.close()


@app.put("/gym_membership_plans/{plan_id}")
def update_plan(plan_id: uuid.UUID, update: PlanUpdate, payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        p = db.query(GymMembershipPlan).filter(GymMembershipPlan.id == plan_id).first()
        if not p:
            raise HTTPException(status_code=404, detail="Plan not found")
        for field, value in update.dict(exclude_unset=True).items():
            setattr(p, field, value)
        p.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(p)
        return {"id": str(p.id), "name": p.name}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@app.delete("/gym_membership_plans/{plan_id}")
def delete_plan(plan_id: uuid.UUID, payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        p = db.query(GymMembershipPlan).filter(GymMembershipPlan.id == plan_id).first()
        if not p:
            raise HTTPException(status_code=404, detail="Plan not found")
        db.delete(p)
        db.commit()
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


# ---------- PAYMENTS ----------

class PaymentIn(BaseModel):
    organization_id: uuid.UUID
    member_id: uuid.UUID
    item_description: str
    amount: float
    payment_method: str
    reference_no: Optional[str] = None


@app.get("/gym_payments/")
def list_payments(payload: dict = Depends(require_role("admin"))):  
    db = SessionLocal()
    try:
        rows = (
            db.query(GymPayment, GymMember)
            .join(GymMember, GymPayment.member_id == GymMember.id)
            .order_by(GymPayment.paid_at.desc())
            .all()
        )
        return [
            {
                "id": str(p.id),
                "receipt_no": p.receipt_no,
                "member_name": m.full_name,
                "item_description": p.item_description,
                "amount": float(p.amount),
                "payment_method": p.payment_method,
                "reference_no": p.reference_no,
                "status": p.status,
                "paid_at": p.paid_at.isoformat(),
            }
            for p, m in rows
        ]
    finally:
        db.close()


@app.post("/gym_payments/")
def create_payment(payment: PaymentIn, payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        receipt_no = f"OR-{uuid.uuid4().hex[:6].upper()}"
        new_payment = GymPayment(
            id=uuid.uuid4(),
            organization_id=payment.organization_id,
            member_id=payment.member_id,
            receipt_no=receipt_no,
            item_description=payment.item_description,
            amount=payment.amount,
            payment_method=payment.payment_method,
            reference_no=payment.reference_no,
            status="paid",
            paid_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(new_payment)
        db.commit()
        db.refresh(new_payment)
        return {"id": str(new_payment.id), "receipt_no": new_payment.receipt_no}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@app.delete("/gym_payments/{payment_id}")
def void_payment(payment_id: uuid.UUID, payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        p = db.query(GymPayment).filter(GymPayment.id == payment_id).first()
        if not p:
            raise HTTPException(status_code=404, detail="Payment not found")
        p.status = "voided"
        p.updated_at = datetime.utcnow()
        db.commit()
        return {"voided": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


# ---------- MEMBERSHIPS / RENEWALS ----------

class MembershipIn(BaseModel):
    organization_id: uuid.UUID
    member_id: uuid.UUID
    plan_id: uuid.UUID
    start_date: datetime
    end_date: datetime
    status: str = "active"


class MembershipUpdate(BaseModel):
    plan_id: Optional[uuid.UUID] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    last_contacted_at: Optional[datetime] = None


@app.get("/gym_memberships/")
def list_memberships(payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        rows = (
            db.query(GymMembership, GymMember, GymMembershipPlan)
            .join(GymMember, GymMembership.member_id == GymMember.id)
            .join(GymMembershipPlan, GymMembership.plan_id == GymMembershipPlan.id)
            .order_by(GymMembership.end_date.asc())
            .all()
        )
        return [
            {
                "id": str(gm.id),
                "member_name": m.full_name,
                "member_phone": m.mobile_phone,
                "plan_name": plan.name,
                "status": gm.status,
                "start_date": gm.start_date.isoformat(),
                "end_date": gm.end_date.isoformat(),
                "last_contacted_at": gm.last_contacted_at.isoformat() if gm.last_contacted_at else None,
            }
            for gm, m, plan in rows
        ]
    finally:
        db.close()


@app.post("/gym_memberships/")
def create_membership(membership: MembershipIn, payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        new_membership = GymMembership(
            id=uuid.uuid4(),
            organization_id=membership.organization_id,
            member_id=membership.member_id,
            plan_id=membership.plan_id,
            status=membership.status,
            start_date=membership.start_date,
            end_date=membership.end_date,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(new_membership)
        db.commit()
        db.refresh(new_membership)
        return {"id": str(new_membership.id)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@app.put("/gym_memberships/{membership_id}")
def update_membership(membership_id: uuid.UUID, update: MembershipUpdate, payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        gm = db.query(GymMembership).filter(GymMembership.id == membership_id).first()
        if not gm:
            raise HTTPException(status_code=404, detail="Membership not found")
        for field, value in update.dict(exclude_unset=True).items():
            setattr(gm, field, value)
        gm.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(gm)
        return {"id": str(gm.id)}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@app.delete("/gym_memberships/{membership_id}")
def delete_membership(membership_id: uuid.UUID, payload: dict = Depends(require_role("admin"))):    
    db = SessionLocal()
    try:
        gm = db.query(GymMembership).filter(GymMembership.id == membership_id).first()
        if not gm:
            raise HTTPException(status_code=404, detail="Membership not found")
        db.delete(gm)
        db.commit()
        return {"deleted": True}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


# ---------- SETTINGS ----------

class SettingsIn(BaseModel):
    organization_id: uuid.UUID
    business_name: str
    bir_tin_number: Optional[str] = None
    official_email: Optional[str] = None
    physical_address: Optional[str] = None
    checkin_timeout_minutes: int = 15
    alert_desk_on_expired_checkin: bool = True
    require_signature_first_guest: bool = True
    sms_gateway_service: Optional[str] = None
    auto_sms_reminder_days: int = 3


@app.get("/gym_settings/{organization_id}")
def get_settings(organization_id: uuid.UUID, payload: dict = Depends(require_role("admin"))):   
    db = SessionLocal()
    try:
        s = db.query(GymSettings).filter(GymSettings.organization_id == organization_id).first()
        if not s:
            return None
        return {
            "id": str(s.id),
            "business_name": s.business_name,
            "bir_tin_number": s.bir_tin_number,
            "official_email": s.official_email,
            "physical_address": s.physical_address,
            "checkin_timeout_minutes": s.checkin_timeout_minutes,
            "alert_desk_on_expired_checkin": s.alert_desk_on_expired_checkin,
            "require_signature_first_guest": s.require_signature_first_guest,
            "sms_gateway_service": s.sms_gateway_service,
            "auto_sms_reminder_days": s.auto_sms_reminder_days,
        }
    finally:
        db.close()


@app.put("/gym_settings/")
def upsert_settings(settings: SettingsIn, payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        existing = db.query(GymSettings).filter(GymSettings.organization_id == settings.organization_id).first()
        if existing:
            for field, value in settings.dict(exclude={"organization_id"}).items():
                setattr(existing, field, value)
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return {"id": str(existing.id), "business_name": existing.business_name}
        else:
            new_settings = GymSettings(
                id=uuid.uuid4(),
                organization_id=settings.organization_id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                **settings.dict(exclude={"organization_id"}),
            )
            db.add(new_settings)
            db.commit()
            db.refresh(new_settings)
            return {"id": str(new_settings.id), "business_name": new_settings.business_name}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()

# ---------- MEMBER PORTAL ----------

class MemberStatusOut(BaseModel):
    pass  # not used, response built inline below


@app.get("/member/status/{member_id}")
def member_status(member_id: uuid.UUID, payload: dict = Depends(require_role("admin", "member"))):
    db = SessionLocal()
    try:
        member = db.query(GymMember).filter(GymMember.id == member_id).first()
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        membership = (
            db.query(GymMembership, GymMembershipPlan)
            .join(GymMembershipPlan, GymMembership.plan_id == GymMembershipPlan.id)
            .filter(GymMembership.member_id == member_id)
            .order_by(GymMembership.end_date.desc())
            .first()
        )

        upcoming_sessions = (
            db.query(GymPtSession, GymCoach)
            .join(GymCoach, GymPtSession.coach_id == GymCoach.id)
            .filter(GymPtSession.member_id == member_id, GymPtSession.status.in_(["requested", "scheduled"]))
            .order_by(GymPtSession.session_date.asc())
            .all()
        )

        renewal_requests = (
            db.query(GymRenewalRequest)
            .filter(GymRenewalRequest.member_id == member_id, GymRenewalRequest.status == "pending")
            .order_by(GymRenewalRequest.requested_date.asc())
            .all()
        )

        return {
            "member": {
                "id": str(member.id),
                "full_name": member.full_name,
                "member_code": member.member_code,
                "status": member.status,
            },
            "membership": (
                {
                    "id": str(membership[0].id),
                    "plan_name": membership[1].name,
                    "status": membership[0].status,
                    "start_date": membership[0].start_date.isoformat(),
                    "end_date": membership[0].end_date.isoformat(),
                }
                if membership else None
            ),
            "upcoming_sessions": [
                {
                    "id": str(s.id),
                    "coach_name": c.full_name,
                    "session_date": s.session_date.isoformat(),
                    "status": s.status,
                    "payment_type": s.payment_type,
                    "amount": float(s.amount),
                    "amount_paid": float(s.amount_paid),
                }
                for s, c in upcoming_sessions
            ],
            "pending_renewals": [
                {
                    "id": str(r.id),
                    "requested_date": r.requested_date.isoformat(),
                    "payment_type": r.payment_type,
                    "amount": float(r.amount),
                    "status": r.status,
                }
                for r in renewal_requests
            ],
        }
    finally:
        db.close()


# ---- Coach session scheduling (member-initiated) ----

class PtSessionRequestIn(BaseModel):
    organization_id: uuid.UUID
    member_id: uuid.UUID
    coach_id: uuid.UUID
    session_date: datetime
    payment_type: str = "full"
    amount: float


@app.post("/gym_pt_sessions/")
def create_pt_session(payload_in: PtSessionRequestIn, payload: dict = Depends(require_role("admin", "member"))):
    db = SessionLocal()
    try:
        new_session = GymPtSession(
            id=uuid.uuid4(),
            organization_id=payload_in.organization_id,
            coach_id=payload_in.coach_id,
            member_id=payload_in.member_id,
            session_date=payload_in.session_date,
            status="requested",
            payment_type=payload_in.payment_type,
            amount=payload_in.amount,
            amount_paid=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return {"id": str(new_session.id)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@app.get("/gym_pt_sessions/")
def list_pt_sessions(payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        rows = (
            db.query(GymPtSession, GymMember, GymCoach)
            .join(GymMember, GymPtSession.member_id == GymMember.id)
            .join(GymCoach, GymPtSession.coach_id == GymCoach.id)
            .order_by(GymPtSession.session_date.asc())
            .all()
        )
        return [
            {
                "id": str(s.id),
                "member_name": m.full_name,
                "coach_name": c.full_name,
                "session_date": s.session_date.isoformat(),
                "status": s.status,
                "payment_type": s.payment_type,
                "amount": float(s.amount),
                "amount_paid": float(s.amount_paid),
            }
            for s, m, c in rows
        ]
    finally:
        db.close()


class PtSessionUpdate(BaseModel):
    status: Optional[str] = None
    amount_paid: Optional[float] = None


@app.put("/gym_pt_sessions/{session_id}")
def update_pt_session(session_id: uuid.UUID, update: PtSessionUpdate, payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        s = db.query(GymPtSession).filter(GymPtSession.id == session_id).first()
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")
        for field, value in update.dict(exclude_unset=True).items():
            setattr(s, field, value)
        s.updated_at = datetime.utcnow()
        db.commit()
        return {"id": str(s.id)}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


# ---- Membership plan avail (member-initiated) ----

class AvailPlanIn(BaseModel):
    organization_id: uuid.UUID
    member_id: uuid.UUID
    plan_id: uuid.UUID
    payment_type: str = "full"
    amount_due: float


@app.post("/gym_memberships/avail")
def avail_plan(payload_in: AvailPlanIn, payload: dict = Depends(require_role("admin", "member"))):
    db = SessionLocal()
    try:
        from datetime import timedelta
        start = datetime.utcnow()
        end = start + timedelta(days=30)

        new_membership = GymMembership(
            id=uuid.uuid4(),
            organization_id=payload_in.organization_id,
            member_id=payload_in.member_id,
            plan_id=payload_in.plan_id,
            status="pending_payment",
            start_date=start,
            end_date=end,
            payment_type=payload_in.payment_type,
            amount_due=payload_in.amount_due,
            amount_paid=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(new_membership)
        db.commit()
        db.refresh(new_membership)
        return {"id": str(new_membership.id)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()

# ---- Renewal scheduling (member-initiated) ----

class RenewalRequestIn(BaseModel):
    organization_id: uuid.UUID
    member_id: uuid.UUID
    membership_id: uuid.UUID
    requested_date: datetime
    payment_type: str = "full"
    amount: float


@app.post("/gym_renewal_requests/")
def create_renewal_request(payload_in: RenewalRequestIn, payload: dict = Depends(require_role("admin", "member"))):
    db = SessionLocal()
    try:
        new_request = GymRenewalRequest(
            id=uuid.uuid4(),
            organization_id=payload_in.organization_id,
            member_id=payload_in.member_id,
            membership_id=payload_in.membership_id,
            requested_date=payload_in.requested_date,
            payment_type=payload_in.payment_type,
            amount=payload_in.amount,
            status="pending",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(new_request)
        db.commit()
        db.refresh(new_request)
        return {"id": str(new_request.id)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()

@app.get("/gym_renewal_requests/")
def list_renewal_requests(payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        rows = (
            db.query(GymRenewalRequest, GymMember)
            .join(GymMember, GymRenewalRequest.member_id == GymMember.id)
            .order_by(GymRenewalRequest.requested_date.asc())
            .all()
        )
        return [
            {
                "id": str(r.id),
                "member_name": m.full_name,
                "membership_id": str(r.membership_id),
                "requested_date": r.requested_date.isoformat(),
                "payment_type": r.payment_type,
                "amount": float(r.amount),
                "status": r.status,
            }
            for r, m in rows
        ]
    finally:
        db.close()


class RenewalCompleteIn(BaseModel):
    extend_days: int = 30


@app.put("/gym_renewal_requests/{request_id}/complete")
def complete_renewal(request_id: uuid.UUID, payload_in: RenewalCompleteIn, payload: dict = Depends(require_role("admin"))):
    db = SessionLocal()
    try:
        req = db.query(GymRenewalRequest).filter(GymRenewalRequest.id == request_id).first()
        if not req:
            raise HTTPException(status_code=404, detail="Renewal request not found")

        membership = db.query(GymMembership).filter(GymMembership.id == req.membership_id).first()
        if not membership:
            raise HTTPException(status_code=404, detail="Membership not found")

        from datetime import timedelta
        membership.end_date = membership.end_date + timedelta(days=payload_in.extend_days)
        membership.status = "active"
        membership.updated_at = datetime.utcnow()

        receipt_no = f"OR-{uuid.uuid4().hex[:6].upper()}"
        new_payment = GymPayment(
            id=uuid.uuid4(),
            organization_id=req.organization_id,
            member_id=req.member_id,
            membership_id=req.membership_id,
            receipt_no=receipt_no,
            item_description=f"Membership renewal ({req.payment_type})",
            amount=req.amount,
            payment_method="cash",
            status="paid",
            paid_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(new_payment)

        req.status = "completed"
        req.updated_at = datetime.utcnow()

        db.commit()
        return {"completed": True, "new_end_date": membership.end_date.isoformat()}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()

        # ---------- AUTH ----------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    member_id: uuid.UUID  # existing gym_members.id they're claiming


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@app.post("/auth/register")
def register(payload: RegisterRequest):
    db = SessionLocal()
    try:
        existing = db.query(GymUser).filter(GymUser.email == payload.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        member = db.query(GymMember).filter(GymMember.id == payload.member_id).first()
        if not member:
            raise HTTPException(status_code=404, detail="Member record not found")

        new_user = GymUser(
            id=uuid.uuid4(),
            organization_id=member.organization_id,
            email=payload.email,
            hashed_password=hash_password(payload.password),
            role="member",
            member_id=member.id,
            created_at=datetime.utcnow(),
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"id": str(new_user.id), "email": new_user.email, "role": new_user.role}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@app.post("/auth/login")
def login(payload: LoginRequest):
    db = SessionLocal()
    try:
        user = db.query(GymUser).filter(GymUser.email == payload.email).first()
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Incorrect email or password")

        token = create_access_token({
            "sub": str(user.id),
            "role": user.role,
            "organization_id": str(user.organization_id),
            "member_id": str(user.member_id) if user.member_id else None,
        })
        return {"access_token": token, "token_type": "bearer", "role": user.role}
    except HTTPException:
        raise
    finally:
        db.close()


