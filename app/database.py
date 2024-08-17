from sqlalchemy import create_engine, Column, Integer, String, Date, Time, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

DATABASE_URL = "sqlite:///vacation_manager.db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    vacation_days = Column(Integer, default=0)
    role = Column(String)
    monthly_vacation_days = Column(Integer, default=2)
    vacations = relationship("Vacation", back_populates="user")


class Vacation(Base):
    __tablename__ = 'vacations'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    start_date = Column(Date)
    end_date = Column(Date)
    status = Column(String)
    note = Column(String, nullable=True)
    
    # Neue Felder hinzufügen
    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)

    user_id = Column(Integer, ForeignKey('users.id'))
    user = relationship("User", back_populates="vacations")

class Settings(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    dreher_limit = Column(Integer, default=2)
    fraeser_limit = Column(Integer, default=2)
    schweisser_limit = Column(Integer, default=2)

def init_db():
    Base.metadata.create_all(bind=engine)

session = SessionLocal()
