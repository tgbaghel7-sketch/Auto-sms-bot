from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, Boolean,
    DateTime, JSON, ForeignKey, create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, attributes
from config import DATABASE_URL, SQLITE_PATH

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(128), nullable=True)
    first_name = Column(String(128), nullable=True)

    # Currently selected Firebase & Channel (FK ids)
    active_firebase_id = Column(Integer, nullable=True)
    active_channel_id = Column(Integer, nullable=True)

    # Devices to monitor (list of device ID strings) – for the active Firebase
    selected_devices = Column(JSON, default=list)

    # Filters
    filters = Column(JSON, default=dict)

    is_monitoring = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    firebases = relationship("FirebaseAccount", back_populates="user", cascade="all, delete-orphan")
    channels = relationship("Channel", back_populates="user", cascade="all, delete-orphan")


class FirebaseAccount(Base):
    __tablename__ = "firebase_accounts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(128), nullable=False)          # user-friendly label
    fb_type = Column(String(32), nullable=False)        # public | private_sa | private_secret
    database_url = Column(Text, nullable=False)
    # For private_sa: full service-account JSON string
    # For private_secret: the database secret
    credentials = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="firebases")


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(128), nullable=True)           # optional label
    channel_id = Column(BigInteger, nullable=False)     # Telegram chat id
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="channels")


def get_engine():
    if DATABASE_URL:
        return create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=5, max_overflow=10)
    return create_engine(
        f"sqlite:///{SQLITE_PATH}",
        connect_args={"check_same_thread": False},
    )


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_user(session, telegram_id: int) -> User | None:
    return session.query(User).filter(User.telegram_id == telegram_id).first()


def get_or_create_user(session, telegram_id: int, username: str = None, first_name: str = None) -> User:
    user = get_user(session, telegram_id)
    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            selected_devices=[],
            filters={"keywords": [], "regex": [], "whitelist": [], "blacklist": []},
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    else:
        changed = False
        if username and user.username != username:
            user.username = username
            changed = True
        if first_name and user.first_name != first_name:
            user.first_name = first_name
            changed = True
        if changed:
            session.commit()
    return user


def mark_json_dirty(obj, field: str):
    attributes.flag_modified(obj, field)
