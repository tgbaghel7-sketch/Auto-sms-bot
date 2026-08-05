from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    BigInteger,
    String,
    Text,
    Boolean,
    DateTime,
    JSON,
    create_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker, attributes
from config import DATABASE_URL, SQLITE_PATH

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(128), nullable=True)
    first_name = Column(String(128), nullable=True)

    # Firebase credentials
    firebase_type = Column(String(32), nullable=True)  # "service_account" (preferred)
    firebase_url = Column(Text, nullable=True)  
    firebase_secret = Column(Text, nullable=True)  # legacy, unused
    firebase_service_account = Column(Text, nullable=True)  

    # Destination
    channel_id = Column(BigInteger, nullable=True)

    # Selected devices (list of device IDs)
    selected_devices = Column(JSON, default=list)

    # Filters
    filters = Column(
        JSON, default=dict
    )  # {"keywords": [], "regex": [], "whitelist": [], "blacklist": []}

    is_monitoring = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


def get_engine():
    if DATABASE_URL:
        # Railway / Postgres – pool_pre_ping keeps connections alive
        return create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
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


def get_or_create_user(
    session, telegram_id: int, username: str = None, first_name: str = None
) -> User:
    user = get_user(session, telegram_id)
    if not user:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            selected_devices=[],
            filters={
                "keywords": [],
                "regex": [],
                "whitelist": [],
                "blacklist": [],
            },
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


def mark_json_dirty(user: User, field: str):
    """Call after mutating a JSON column in-place so SQLAlchemy detects the change."""
    attributes.flag_modified(user, field)
