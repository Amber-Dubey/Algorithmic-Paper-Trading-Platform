from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime

try:
    from database.settings import DATABASE_URL
except ImportError:
    DATABASE_URL = "sqlite:///paper_trading.db"

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    balance = Column(Float, default=100000.0)
    
    # Add lazy="selectin" here so they load immediately before the session closes
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan", lazy="selectin")

class Portfolio(Base):
    __tablename__ = 'portfolio'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    ticker = Column(String(20), nullable=False)
    asset_type = Column(String(20), nullable=False)
    shares = Column(Float, nullable=False)
    avg_cost = Column(Float, nullable=False)
    
    user = relationship("User", back_populates="portfolios")

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    ticker = Column(String(20), nullable=False)
    action = Column(String(10), nullable=False)
    shares = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="transactions")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)