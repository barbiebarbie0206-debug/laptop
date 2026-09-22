import enum
from sqlalchemy import Column, Integer, String, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..core.database import Base


class Batch(str, enum.Enum):
    MORNING = "Morning"
    AFTERNOON = "Afternoon"
    FULL_DAY = "Full Day"


class Domain(str, enum.Enum):
    CLOUD = "Cloud"
    DATA_ANALYTICS = "Data Analytics"
    FULL_STACK = "Full Stack"
    AI_ML = "AI & ML"
    DIGITAL_MARKETING = "Digital Marketing"
    UI_UX = "UI/UX"


class Intern(Base):
    __tablename__ = "interns"

    id = Column(Integer, primary_key=True, index=True)
    intern_id = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    batch = Column(Enum(Batch), nullable=False)
    domain = Column(Enum(Domain), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    allocations = relationship("Allocation", back_populates="intern")
