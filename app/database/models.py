
from datetime import date, time, datetime, timezone

from sqlalchemy import (
    String, Integer, Boolean, Date, Time, DateTime, JSON,
    ForeignKey, ForeignKeyConstraint, UniqueConstraint,
    CheckConstraint
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base

#Company Table Description
class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


#Employee Table Description 
class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(150))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="EMPLOYEE")

    __table_args__ = (
        UniqueConstraint("company_id", "id"),
        UniqueConstraint("company_id", "email"),
        CheckConstraint(
            "role IN ('EMPLOYEE', 'MANAGER')"
        ),
    )


#Company Policy Table
class CompanyPolicy(Base):
    __tablename__ = "company_policies"

    id: Mapped[int] = mapped_column(primary_key=True)

    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"),
        unique=True,
        nullable=False
    )

    policy_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False
    )

    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )


#Cab Table
class Cab(Base):
    __tablename__ = "cabs"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"), nullable=False
    )
    cab_code: Mapped[str] = mapped_column(String(30))
    capacity: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("company_id", "id"),
        UniqueConstraint("company_id", "cab_code"),
        CheckConstraint("capacity > 0"),
    )


#Slot Table
class Slot(Base):
    __tablename__ = "slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer)
    cab_id: Mapped[int] = mapped_column(Integer)

    service_date: Mapped[date] = mapped_column(Date)
    scheduled_time: Mapped[time] = mapped_column(Time)

    status: Mapped[str] = mapped_column(
        String(20), default="OPEN"
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "cab_id"],
            ["cabs.company_id", "cabs.id"]
        ),
        UniqueConstraint("company_id", "id"),
        CheckConstraint("status IN ('OPEN', 'CANCELLED')"),
    )


#Roster Entry Table
class RosterEntry(Base):
    __tablename__ = "roster_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(Integer)
    employee_id: Mapped[int] = mapped_column(Integer)
    slot_id: Mapped[int] = mapped_column(Integer)

    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "employee_id"],
            ["employees.company_id", "employees.id"]
        ),
        ForeignKeyConstraint(
            ["company_id", "slot_id"],
            ["slots.company_id", "slots.id"]
        ),
        UniqueConstraint("company_id", "id"),
    )


#Request Table
class ShiftChangeRequest(Base):
    __tablename__ = "shift_change_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id"), nullable=False
    )
    employee_id: Mapped[int] = mapped_column(Integer)

    roster_entry_id: Mapped[int] = mapped_column(Integer)
    requested_slot_id: Mapped[int] = mapped_column(Integer)

    requested_date: Mapped[date] = mapped_column(
        Date,
        nullable=False
    )

    requested_time: Mapped[time] = mapped_column(
        Time,
        nullable=False
    )

    reason: Mapped[str | None] = mapped_column(String(500))

    status: Mapped[str] = mapped_column(
        String(30), default="PENDING"
    )

    approval_given: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "employee_id"],
            ["employees.company_id", "employees.id"]
        ),
        ForeignKeyConstraint(
            ["company_id", "roster_entry_id"],
            ["roster_entries.company_id", "roster_entries.id"]
        ),
        ForeignKeyConstraint(
            ["company_id", "requested_slot_id"],
            ["slots.company_id", "slots.id"]
        ),
        CheckConstraint(
            "status IN ('PENDING', 'APPROVAL_REQUIRED', "
            "'APPROVED', 'REJECTED', 'APPLIED', 'FAILED')"
        ),
    )
