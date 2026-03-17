import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from database import Base, engine, get_db
from models import (
    CartItemModel,
    FlowerModel,
    OrderItemModel,
    OrderModel,
    OrderStatus,
    UserModel,
    UserRole,
)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

BOOTSTRAP_ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
BOOTSTRAP_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")

# bcrypt currently has compatibility issues on some Python builds (e.g. 3.14 on Windows),
# so we use a widely supported scheme that doesn't require the bcrypt wheel.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
security = HTTPBearer(auto_error=False)


@app.on_event("startup")
def on_startup() -> None:
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured")
    Base.metadata.create_all(bind=engine)

    # Ensure at least one admin exists (dev-friendly bootstrap).
    from database import SessionLocal

    if SessionLocal is None:
        return
    db = SessionLocal()
    try:
        admin = db.query(UserModel).filter(UserModel.username == BOOTSTRAP_ADMIN_USERNAME).one_or_none()
        if admin is None:
            db.add(
                UserModel(
                    username=BOOTSTRAP_ADMIN_USERNAME,
                    password_hash=pwd_context.hash(BOOTSTRAP_ADMIN_PASSWORD),
                    role=UserRole.admin,
                )
            )
            db.commit()
    finally:
        db.close()


def _create_access_token(*, sub: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> UserModel:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = creds.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.query(UserModel).filter(UserModel.username == username).one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_admin(user: UserModel = Depends(get_current_user)) -> UserModel:
    if user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


class FlowerBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    price: float = Field(gt=0)
    image_url: str = Field(min_length=1, max_length=1024)


class FlowerCreate(FlowerBase):
    pass


class FlowerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    price: float | None = Field(default=None, gt=0)
    image_url: str | None = Field(default=None, min_length=1, max_length=1024)


class FlowerOut(FlowerBase):
    id: int


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    role: UserRole


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CartItemAdd(BaseModel):
    flower_id: int
    qty: int = Field(gt=0)


class CartItemUpdate(BaseModel):
    qty: int = Field(gt=0)


class CartItemOut(BaseModel):
    id: int
    flower: FlowerOut
    qty: int


class OrderItemOut(BaseModel):
    flower: FlowerOut
    qty: int
    unit_price: float


class OrderOut(BaseModel):
    id: int
    status: OrderStatus
    created_at: datetime
    items: list[OrderItemOut]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/auth/register", response_model=UserOut)
def register(payload: UserRegister, db: Session = Depends(get_db)) -> UserOut:
    exists = db.query(UserModel).filter(UserModel.username == payload.username).one_or_none()
    if exists is not None:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = UserModel(
        username=payload.username,
        password_hash=pwd_context.hash(payload.password),
        role=UserRole.user,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut(id=user.id, username=user.username, role=user.role)


@app.post("/auth/login", response_model=TokenOut)
def login(payload: UserLogin, db: Session = Depends(get_db)) -> TokenOut:
    user = db.query(UserModel).filter(UserModel.username == payload.username).one_or_none()
    if user is None or not pwd_context.verify(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect username or password")

    token = _create_access_token(sub=user.username, role=user.role.value)
    return TokenOut(access_token=token)


@app.get("/me", response_model=UserOut)
def me(current_user: UserModel = Depends(get_current_user)) -> UserOut:
    return UserOut(id=current_user.id, username=current_user.username, role=current_user.role)


@app.get("/flowers", response_model=list[FlowerOut])
def list_flowers(db: Session = Depends(get_db)) -> list[FlowerOut]:
    rows = db.query(FlowerModel).order_by(FlowerModel.id.asc()).all()
    return [FlowerOut(id=r.id, name=r.name, price=float(r.price), image_url=r.image_url) for r in rows]


@app.get("/flowers/{flower_id}", response_model=FlowerOut)
def get_flower(flower_id: int, db: Session = Depends(get_db)) -> FlowerOut:
    row = db.query(FlowerModel).filter(FlowerModel.id == flower_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Flower not found")
    return FlowerOut(id=row.id, name=row.name, price=float(row.price), image_url=row.image_url)


@app.post("/admin/flowers", response_model=FlowerOut)
def admin_create_flower(
    payload: FlowerCreate,
    db: Session = Depends(get_db),
    _: UserModel = Depends(require_admin),
) -> FlowerOut:
    row = FlowerModel(name=payload.name, price=payload.price, image_url=str(payload.image_url))
    db.add(row)
    db.commit()
    db.refresh(row)
    return FlowerOut(id=row.id, name=row.name, price=float(row.price), image_url=row.image_url)


@app.patch("/admin/flowers/{flower_id}", response_model=FlowerOut)
def admin_update_flower(
    flower_id: int,
    payload: FlowerUpdate,
    db: Session = Depends(get_db),
    _: UserModel = Depends(require_admin),
) -> FlowerOut:
    row = db.query(FlowerModel).filter(FlowerModel.id == flower_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Flower not found")

    if payload.name is not None:
        row.name = payload.name
    if payload.price is not None:
        row.price = payload.price
    if payload.image_url is not None:
        row.image_url = payload.image_url

    db.commit()
    db.refresh(row)
    return FlowerOut(id=row.id, name=row.name, price=float(row.price), image_url=row.image_url)


@app.delete("/admin/flowers/{flower_id}")
def admin_delete_flower(
    flower_id: int,
    db: Session = Depends(get_db),
    _: UserModel = Depends(require_admin),
) -> dict:
    row = db.query(FlowerModel).filter(FlowerModel.id == flower_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Flower not found")
    db.delete(row)
    db.commit()
    return {"deleted": True}


@app.get("/cart", response_model=list[CartItemOut])
def get_cart(current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)) -> list[CartItemOut]:
    items = (
        db.query(CartItemModel)
        .options(joinedload(CartItemModel.flower))
        .filter(CartItemModel.user_id == current_user.id)
        .order_by(CartItemModel.id.asc())
        .all()
    )
    return [
        CartItemOut(
            id=i.id,
            qty=i.qty,
            flower=FlowerOut(
                id=i.flower.id,
                name=i.flower.name,
                price=float(i.flower.price),
                image_url=i.flower.image_url,
            ),
        )
        for i in items
    ]


@app.post("/cart/items", response_model=CartItemOut)
def add_to_cart(
    payload: CartItemAdd,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CartItemOut:
    flower = db.query(FlowerModel).filter(FlowerModel.id == payload.flower_id).one_or_none()
    if flower is None:
        raise HTTPException(status_code=404, detail="Flower not found")

    item = (
        db.query(CartItemModel)
        .options(joinedload(CartItemModel.flower))
        .filter(CartItemModel.user_id == current_user.id, CartItemModel.flower_id == payload.flower_id)
        .one_or_none()
    )
    if item is None:
        item = CartItemModel(user_id=current_user.id, flower_id=payload.flower_id, qty=payload.qty)
        db.add(item)
    else:
        item.qty += payload.qty

    db.commit()
    db.refresh(item)
    item = (
        db.query(CartItemModel)
        .options(joinedload(CartItemModel.flower))
        .filter(CartItemModel.id == item.id)
        .one()
    )
    return CartItemOut(
        id=item.id,
        qty=item.qty,
        flower=FlowerOut(id=item.flower.id, name=item.flower.name, price=float(item.flower.price), image_url=item.flower.image_url),
    )


@app.patch("/cart/items/{item_id}", response_model=CartItemOut)
def update_cart_item(
    item_id: int,
    payload: CartItemUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CartItemOut:
    item = (
        db.query(CartItemModel)
        .options(joinedload(CartItemModel.flower))
        .filter(CartItemModel.id == item_id, CartItemModel.user_id == current_user.id)
        .one_or_none()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")

    item.qty = payload.qty
    db.commit()
    db.refresh(item)
    return CartItemOut(
        id=item.id,
        qty=item.qty,
        flower=FlowerOut(id=item.flower.id, name=item.flower.name, price=float(item.flower.price), image_url=item.flower.image_url),
    )


@app.delete("/cart/items/{item_id}")
def delete_cart_item(
    item_id: int,
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    item = db.query(CartItemModel).filter(CartItemModel.id == item_id, CartItemModel.user_id == current_user.id).one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")
    db.delete(item)
    db.commit()
    return {"deleted": True}


@app.post("/orders/from-cart", response_model=OrderOut)
def create_order_from_cart(
    current_user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OrderOut:
    cart_items = (
        db.query(CartItemModel)
        .options(joinedload(CartItemModel.flower))
        .filter(CartItemModel.user_id == current_user.id)
        .all()
    )
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    order = OrderModel(user_id=current_user.id, status=OrderStatus.new)
    db.add(order)
    db.flush()  # assigns order.id

    for ci in cart_items:
        db.add(
            OrderItemModel(
                order_id=order.id,
                flower_id=ci.flower_id,
                qty=ci.qty,
                unit_price=float(ci.flower.price),
            )
        )
        db.delete(ci)

    db.commit()
    order = (
        db.query(OrderModel)
        .options(joinedload(OrderModel.items).joinedload(OrderItemModel.flower))
        .filter(OrderModel.id == order.id)
        .one()
    )

    return OrderOut(
        id=order.id,
        status=order.status,
        created_at=order.created_at,
        items=[
            OrderItemOut(
                flower=FlowerOut(
                    id=it.flower.id,
                    name=it.flower.name,
                    price=float(it.flower.price),
                    image_url=it.flower.image_url,
                ),
                qty=it.qty,
                unit_price=float(it.unit_price),
            )
            for it in order.items
        ],
    )


@app.get("/me/orders", response_model=list[OrderOut])
def my_orders(current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)) -> list[OrderOut]:
    orders = (
        db.query(OrderModel)
        .options(joinedload(OrderModel.items).joinedload(OrderItemModel.flower))
        .filter(OrderModel.user_id == current_user.id)
        .order_by(OrderModel.id.desc())
        .all()
    )
    return [
        OrderOut(
            id=o.id,
            status=o.status,
            created_at=o.created_at,
            items=[
                OrderItemOut(
                    flower=FlowerOut(
                        id=it.flower.id,
                        name=it.flower.name,
                        price=float(it.flower.price),
                        image_url=it.flower.image_url,
                    ),
                    qty=it.qty,
                    unit_price=float(it.unit_price),
                )
                for it in o.items
            ],
        )
        for o in orders
    ]


@app.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, current_user: UserModel = Depends(get_current_user), db: Session = Depends(get_db)) -> OrderOut:
    order = (
        db.query(OrderModel)
        .options(joinedload(OrderModel.items).joinedload(OrderItemModel.flower))
        .filter(OrderModel.id == order_id)
        .one_or_none()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.user_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Forbidden")

    return OrderOut(
        id=order.id,
        status=order.status,
        created_at=order.created_at,
        items=[
            OrderItemOut(
                flower=FlowerOut(
                    id=it.flower.id,
                    name=it.flower.name,
                    price=float(it.flower.price),
                    image_url=it.flower.image_url,
                ),
                qty=it.qty,
                unit_price=float(it.unit_price),
            )
            for it in order.items
        ],
    )


@app.get("/admin/orders", response_model=list[OrderOut])
def admin_list_orders(_: UserModel = Depends(require_admin), db: Session = Depends(get_db)) -> list[OrderOut]:
    orders = (
        db.query(OrderModel)
        .options(joinedload(OrderModel.items).joinedload(OrderItemModel.flower))
        .order_by(OrderModel.id.desc())
        .all()
    )
    return [
        OrderOut(
            id=o.id,
            status=o.status,
            created_at=o.created_at,
            items=[
                OrderItemOut(
                    flower=FlowerOut(
                        id=it.flower.id,
                        name=it.flower.name,
                        price=float(it.flower.price),
                        image_url=it.flower.image_url,
                    ),
                    qty=it.qty,
                    unit_price=float(it.unit_price),
                )
                for it in o.items
            ],
        )
        for o in orders
    ]


@app.patch("/admin/orders/{order_id}/status", response_model=OrderOut)
def admin_update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    _: UserModel = Depends(require_admin),
    db: Session = Depends(get_db),
) -> OrderOut:
    order = (
        db.query(OrderModel)
        .options(joinedload(OrderModel.items).joinedload(OrderItemModel.flower))
        .filter(OrderModel.id == order_id)
        .one_or_none()
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    order.status = payload.status
    db.commit()
    db.refresh(order)

    return OrderOut(
        id=order.id,
        status=order.status,
        created_at=order.created_at,
        items=[
            OrderItemOut(
                flower=FlowerOut(
                    id=it.flower.id,
                    name=it.flower.name,
                    price=float(it.flower.price),
                    image_url=it.flower.image_url,
                ),
                qty=it.qty,
                unit_price=float(it.unit_price),
            )
            for it in order.items
        ],
    )


@app.get("/admin/users/{user_id}", response_model=UserOut)
def admin_get_user(user_id: int, _: UserModel = Depends(require_admin), db: Session = Depends(get_db)) -> UserOut:
    user = db.query(UserModel).filter(UserModel.id == user_id).one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut(id=user.id, username=user.username, role=user.role)
