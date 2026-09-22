import logging
from sqlalchemy.orm import Session
from .laptop import Laptop, LaptopStatus
from .intern import Intern, Batch, Domain
from .user import User, UserRole
from ..core.security import get_password_hash

logger = logging.getLogger("laptop_allocation.seed")


def seed_all(db: Session):
    # Startup seeding creates ONLY the default admin account. No laptops,
    # interns or allocations are auto-created: the admin-imported Excel data
    # is the single source of truth for the inventory.
    admin_exists = db.query(User).filter(User.role == UserRole.ADMIN).first() is not None
    username_taken = db.query(User).filter(User.username == "admin").first() is not None
    if not admin_exists and not username_taken:
        db.add(User(
            username="admin",
            email="admin@laptopallocation.com",
            hashed_password=get_password_hash("admin123"),
            full_name="System Administrator",
            role=UserRole.ADMIN,
            is_active=1,
        ))
        logger.info("Seeded default admin user (username=admin)")
    elif not admin_exists:
        logger.warning(
            "No ADMIN role user exists but username 'admin' is taken; "
            "default admin user was NOT created automatically."
        )

    db.commit()


def seed_demo_data(db: Session):
    # DEMO records for automated tests ONLY. Never called by the application.
    for data in _LAPTOP_DEMO_DATA:
        db.add(Laptop(**data))

    for data in _INTERN_DEMO_DATA:
        db.add(Intern(**data))

    db.commit()


_LAPTOP_DEMO_DATA = [
    {"laptop_number": "LP-001", "brand": "Dell", "model": "Latitude 5520", "serial_number": "DL-5520-001", "status": LaptopStatus.FREE},
    {"laptop_number": "LP-002", "brand": "Dell", "model": "Latitude 5520", "serial_number": "DL-5520-002", "status": LaptopStatus.FREE},
    {"laptop_number": "LP-003", "brand": "HP", "model": "EliteBook 840 G8", "serial_number": "HP-840G8-001", "status": LaptopStatus.FREE},
    {"laptop_number": "LP-004", "brand": "HP", "model": "EliteBook 840 G8", "serial_number": "HP-840G8-002", "status": LaptopStatus.FREE},
    {"laptop_number": "LP-005", "brand": "Lenovo", "model": "ThinkPad T14", "serial_number": "LN-T14-001", "status": LaptopStatus.FREE},
    {"laptop_number": "LP-006", "brand": "Lenovo", "model": "ThinkPad T14", "serial_number": "LN-T14-002", "status": LaptopStatus.FREE},
    {"laptop_number": "LP-007", "brand": "Dell", "model": "Inspiron 15", "serial_number": "DL-IN15-001", "status": LaptopStatus.FREE},
    {"laptop_number": "LP-008", "brand": "HP", "model": "Pavilion 15", "serial_number": "HP-PAV15-001", "status": LaptopStatus.FREE},
    {"laptop_number": "LP-009", "brand": "Lenovo", "model": "IdeaPad Slim 5", "serial_number": "LN-IS5-001", "status": LaptopStatus.FREE},
    {"laptop_number": "LP-010", "brand": "Acer", "model": "Aspire 5", "serial_number": "AC-A5-001", "status": LaptopStatus.FREE},
    {"laptop_number": "LP-011", "brand": "Dell", "model": "Latitude 5520", "serial_number": "DL-5520-003", "status": LaptopStatus.FREE},
    {"laptop_number": "LP-012", "brand": "HP", "model": "EliteBook 840 G8", "serial_number": "HP-840G8-003", "status": LaptopStatus.FREE},
    {"laptop_number": "LP-013", "brand": "Lenovo", "model": "ThinkPad T14", "serial_number": "LN-T14-003", "status": LaptopStatus.FREE},
    {"laptop_number": "LP-014", "brand": "Acer", "model": "Aspire 5", "serial_number": "AC-A5-002", "status": LaptopStatus.FREE},
    {"laptop_number": "LP-015", "brand": "Dell", "model": "Inspiron 15", "serial_number": "DL-IN15-002", "status": LaptopStatus.FREE},
    {"laptop_number": "LP-016", "brand": "HP", "model": "Pavilion 15", "serial_number": "HP-PAV15-002", "status": LaptopStatus.FREE},
    {"laptop_number": "LP-017", "brand": "Lenovo", "model": "IdeaPad Slim 5", "serial_number": "LN-IS5-002", "status": LaptopStatus.FREE},
    {"laptop_number": "LP-018", "brand": "Dell", "model": "Latitude 5520", "serial_number": "DL-5520-004", "status": LaptopStatus.FREE},
    {"laptop_number": "LP-019", "brand": "HP", "model": "EliteBook 840 G8", "serial_number": "HP-840G8-004", "status": LaptopStatus.MAINTENANCE},
    {"laptop_number": "LP-020", "brand": "Lenovo", "model": "ThinkPad T14", "serial_number": "LN-T14-004", "status": LaptopStatus.FREE},
]

_INTERN_DEMO_DATA = [
    {"intern_id": "INT-001", "name": "Aarav Sharma", "email": "aarav.sharma@interns.com", "phone": "9876543201", "batch": Batch.MORNING, "domain": Domain.FULL_STACK},
    {"intern_id": "INT-002", "name": "Priya Patel", "email": "priya.patel@interns.com", "phone": "9876543202", "batch": Batch.MORNING, "domain": Domain.DATA_ANALYTICS},
    {"intern_id": "INT-003", "name": "Rohan Gupta", "email": "rohan.gupta@interns.com", "phone": "9876543203", "batch": Batch.AFTERNOON, "domain": Domain.CLOUD},
    {"intern_id": "INT-004", "name": "Sneha Reddy", "email": "sneha.reddy@interns.com", "phone": "9876543204", "batch": Batch.MORNING, "domain": Domain.AI_ML},
    {"intern_id": "INT-005", "name": "Vikram Singh", "email": "vikram.singh@interns.com", "phone": "9876543205", "batch": Batch.AFTERNOON, "domain": Domain.UI_UX},
    {"intern_id": "INT-006", "name": "Ananya Nair", "email": "ananya.nair@interns.com", "phone": "9876543206", "batch": Batch.MORNING, "domain": Domain.DIGITAL_MARKETING},
    {"intern_id": "INT-007", "name": "Karthik Iyer", "email": "karthik.iyer@interns.com", "phone": "9876543207", "batch": Batch.AFTERNOON, "domain": Domain.FULL_STACK},
    {"intern_id": "INT-008", "name": "Meera Joshi", "email": "meera.joshi@interns.com", "phone": "9876543208", "batch": Batch.MORNING, "domain": Domain.DATA_ANALYTICS},
    {"intern_id": "INT-009", "name": "Aditya Verma", "email": "aditya.verma@interns.com", "phone": "9876543209", "batch": Batch.AFTERNOON, "domain": Domain.AI_ML},
    {"intern_id": "INT-010", "name": "Nisha Das", "email": "nisha.das@interns.com", "phone": "9876543210", "batch": Batch.MORNING, "domain": Domain.UI_UX},
]