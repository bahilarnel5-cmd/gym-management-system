import uuid
import random
from datetime import datetime, timedelta, date

from faker import Faker
from app.database import SessionLocal
from app.models import GymMember, GymCoach, GymMembershipPlan, GymMembership, GymPayment

fake = Faker()
ORG_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")

db = SessionLocal()

# --- 1. Coaches (need these before members reference them) ---
SPECIALIZATIONS = ["CrossFit & Powerlifting", "Yoga & Rehabilitation", "Bodybuilding & Strength", "HIIT & Conditioning", "Boxing & Cardio"]
SHIFTS = ["Morning Shift (6 AM - 2 PM)", "Afternoon Shift (1 PM - 9 PM)"]

coaches = []
for _ in range(8):
    c = GymCoach(
        id=uuid.uuid4(),
        organization_id=ORG_ID,
        full_name=f"Coach {fake.first_name()} {fake.last_name()}",
        specialization=random.choice(SPECIALIZATIONS),
        hourly_rate=random.choice([650, 700, 750, 800, 850, 900]),
        mobile_contact=f"+63 9{random.randint(10,99)} {random.randint(100,999)} {random.randint(1000,9999)}",
        shift_schedule=random.choice(SHIFTS),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(c)
    coaches.append(c)
db.commit()
print(f"Created {len(coaches)} coaches")

# --- 2. Membership Plans ---
PLAN_DEFS = [
    ("Starter Basic", 1800, "monthly"),
    ("Pro Performance", 3200, "monthly"),
    ("Elite VIP", 6500, "monthly"),
]
plans = []
for name, price, cycle in PLAN_DEFS:
    p = GymMembershipPlan(
        id=uuid.uuid4(),
        organization_id=ORG_ID,
        name=name,
        price=price,
        billing_cycle=cycle,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(p)
    plans.append(p)
db.commit()
print(f"Created {len(plans)} plans")

# --- 3. Members (100 of them) ---
members = []
for i in range(100):
    m = GymMember(
        id=uuid.uuid4(),
        organization_id=ORG_ID,
        member_code=f"AG-{10000 + i}",
        full_name=fake.name(),
        email=fake.email(),
        mobile_phone=f"+63 9{random.randint(10,99)} {random.randint(100,999)} {random.randint(1000,9999)}",
        assigned_coach_id=random.choice(coaches).id if random.random() > 0.2 else None,
        status=random.choices(["active", "inactive"], weights=[0.85, 0.15])[0],
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(m)
    members.append(m)
db.commit()
print(f"Created {len(members)} members")

# --- 4. Memberships (enroll ~80 of the 100 members into random plans) ---
memberships = []
for m in random.sample(members, 80):
    plan = random.choice(plans)
    start = fake.date_between(start_date="-6M", end_date="today")
    end_offset = random.choice([-10, -3, 2, 5, 15, 30, 60, 90])
    end = date.today() + timedelta(days=end_offset)
    gm = GymMembership(
        id=uuid.uuid4(),
        organization_id=ORG_ID,
        member_id=m.id,
        plan_id=plan.id,
        status="active",
        start_date=start,
        end_date=end,
        last_contacted_at=datetime.utcnow() - timedelta(days=random.randint(0, 20)) if random.random() > 0.5 else None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(gm)
    memberships.append((gm, plan))
db.commit()
print(f"Created {len(memberships)} memberships")

# --- 5. Payments (one payment per membership, matching its plan price) ---
METHODS = ["GCash", "Cash", "Credit Card"]
payment_count = 0
for gm, plan in memberships:
    pay = GymPayment(
        id=uuid.uuid4(),
        organization_id=ORG_ID,
        member_id=gm.member_id,
        membership_id=gm.id,
        receipt_no=f"OR-{uuid.uuid4().hex[:6].upper()}",
        item_description=f"{plan.name} ({plan.billing_cycle})",
        amount=plan.price,
        payment_method=random.choice(METHODS),
        reference_no=fake.bothify(text="REF-######"),
        status="paid",
        paid_at=datetime.utcnow() - timedelta(days=random.randint(0, 60)),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(pay)
    payment_count += 1
db.commit()
print(f"Created {payment_count} payments")

db.close()
print("Seeding complete!")