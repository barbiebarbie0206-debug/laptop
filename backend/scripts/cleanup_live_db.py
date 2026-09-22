import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import or_

from app.core.database import SessionLocal
from app.models.allocation import Allocation
from app.models.intern import Intern
from app.models.laptop import Laptop
from app.models.seed import _LAPTOP_DEMO_DATA, _INTERN_DEMO_DATA

seed_numbers = {d["laptop_number"] for d in _LAPTOP_DEMO_DATA}
seed_intern_ids = {d["intern_id"] for d in _INTERN_DEMO_DATA}

db = SessionLocal()
try:
    laptop_ids = [
        lid for (lid,) in db.query(Laptop.id).filter(Laptop.laptop_number.in_(seed_numbers)).all()
    ]
    intern_ids = [
        iid for (iid,) in db.query(Intern.id).filter(Intern.intern_id.in_(seed_intern_ids)).all()
    ]

    allocation_q = db.query(Allocation)
    if laptop_ids or intern_ids:
        allocation_q = allocation_q.filter(
            or_(Allocation.laptop_id.in_(laptop_ids), Allocation.intern_id.in_(intern_ids))
        )
    n_alloc = allocation_q.delete(synchronize_session=False)

    n_lap = db.query(Laptop).filter(Laptop.laptop_number.in_(seed_numbers)).delete(synchronize_session=False)
    n_int = db.query(Intern).filter(Intern.intern_id.in_(seed_intern_ids)).delete(synchronize_session=False)

    n_unk = db.query(Laptop).filter(Laptop.brand == "Unknown", Laptop.model == "Unknown").update(
        {"brand": "", "model": ""}, synchronize_session=False
    )

    db.commit()
    print(f"Removed {n_alloc} allocation(s), {n_lap} seed laptop(s), {n_int} seed intern(s)")
    print(f"Cleared {n_unk} records with invented brand/model 'Unknown'")
    print(f"Remaining laptops: {db.query(Laptop).count()}")
    print(f"Remaining interns: {db.query(Intern).count()}")
    print(f"Remaining allocations: {db.query(Allocation).count()}")
finally:
    db.close()