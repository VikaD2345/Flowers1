from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class UserRole(str, Enum):
    user = "user"
    admin = "admin"


class OrderStatus(str, Enum):
    new = "new"
    delivering = "delivering"
    done = "done"
    canceled = "canceled"


class UserModel(Base):
    __tablename__ = "app_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False, default=UserRole.user)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    cart_items: Mapped[list[CartItemModel]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    orders: Mapped[list[OrderModel]] = relationship(back_populates="user")


class FlowerModel(Base):
    __tablename__ = "bouquets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    image_url: Mapped[str] = mapped_column(String(1024), nullable=False)

    cart_items: Mapped[list[CartItemModel]] = relationship(back_populates="flower")
    order_items: Mapped[list[OrderItemModel]] = relationship(back_populates="flower")


class CartItemModel(Base):
    __tablename__ = "app_cart_items"
    __table_args__ = (UniqueConstraint("user_id", "flower_id", name="uq_app_cart_user_flower"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"), index=True, nullable=False)
    flower_id: Mapped[int] = mapped_column(ForeignKey("bouquets.id"), index=True, nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped[UserModel] = relationship(back_populates="cart_items")
    flower: Mapped[FlowerModel] = relationship(back_populates="cart_items")


class OrderModel(Base):
    __tablename__ = "app_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_users.id"), index=True, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(SAEnum(OrderStatus), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped[UserModel] = relationship(back_populates="orders")
    items: Mapped[list[OrderItemModel]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItemModel(Base):
    __tablename__ = "app_order_items"
    __table_args__ = (UniqueConstraint("order_id", "flower_id", name="uq_app_order_flower"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("app_orders.id"), index=True, nullable=False)
    flower_id: Mapped[int] = mapped_column(ForeignKey("bouquets.id"), index=True, nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped[OrderModel] = relationship(back_populates="items")
    flower: Mapped[FlowerModel] = relationship(back_populates="order_items")
