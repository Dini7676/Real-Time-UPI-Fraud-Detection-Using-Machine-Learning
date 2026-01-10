import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime

DEFAULT_SQLITE = f"sqlite:///{os.path.join(os.path.dirname(__file__), '..', 'dataset', 'upiguard.db')}"
DB_URL = os.getenv("DB_URL", DEFAULT_SQLITE)
engine = create_engine(DB_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    email = Column(String(120), unique=True)
    mobile = Column(String(20))
    dob = Column(String(20))
    age = Column(Integer)
    address = Column(String(255))
    state = Column(String(100))
    zip = Column(String(20))
    role = Column(String(20))  # 'user' or 'admin' or 'merchant'
    upi = Column(String(100))
    merchants = relationship("Merchant", back_populates="owner")

class Merchant(Base):
    __tablename__ = 'merchants'
    merchant_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    category = Column(String(100))
    qr_code = Column(String(255))  # path to generated QR image
    owner = relationship("User", back_populates="merchants")

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True, index=True)
    sender = Column(String(100))
    receiver = Column(String(100))
    amount = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    prediction = Column(String(20))  # 'safe' or 'fraud'

class RiskStat(Base):
    __tablename__ = 'risk_stats'
    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String(120))  # mobile or upi
    id_type = Column(String(20))      # 'mobile' or 'upi'
    total_txn = Column(Integer, default=0)
    fraud_txn = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint('identifier', 'id_type', name='uq_identifier_type'),)


def init_db():
    try:
        # Attempt to connect; if MySQL is configured but not running, fallback to SQLite
        with engine.connect() as conn:
            pass
    except Exception:
        # Fallback to SQLite
        fallback_engine = create_engine(DEFAULT_SQLITE, echo=False, future=True)
        globals()['engine'] = fallback_engine
        globals()['SessionLocal'] = sessionmaker(bind=fallback_engine)
    Base.metadata.create_all(engine)

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
