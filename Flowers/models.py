from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    full_name = Column(String(255))
    email = Column(String(255), unique=True)
    phone = Column(String(20))
    password_hash = Column(String(255))
    role = Column(String(50), default="customer")
    created_at = Column(DateTime, default=datetime.utcnow)

class Bouquet(Base):
    __tablename__ = "bouquets"
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    description = Column(Text)
    price = Column(Float)
    image_url = Column(String(500))
    stock = Column(Integer, default=0)
    is_popular = Column(Boolean, default=False)


class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String(50), default="new")
    total_amount = Column(Float)
    payment_method = Column(String(50))
    delivery_address = Column(Text)
    delivery_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    bouquet_id = Column(Integer, ForeignKey("bouquets.id"))
    quantity = Column(Integer)
    unit_price = Column(Float)
    subtotal = Column(Float)

class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    bouquet_id = Column(Integer, ForeignKey("bouquets.id"))
    quantity = Column(Integer, default=1)
