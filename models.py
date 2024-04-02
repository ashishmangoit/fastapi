from sqlalchemy import Boolean, Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, index=True)
    last_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    super_user = Column(Boolean, default=False)

class DatasheetLink(Base):
    __tablename__ = "datasheet_link"

    id = Column(Integer, primary_key=True, index=True)
    datasheet_link = Column(String, index=True)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class MasterDeveloper(Base):
    __tablename__ = "master_developer"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    team_lead = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class MasterProjects(Base):
    __tablename__ = "master_projects"

    id = Column(Integer, primary_key=True, index=True)
    project_name = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class TimeSheetData(Base):
    __tablename__ = "time_sheet_data"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow)
    developer_id = Column(String(255))
    team_lead_id = Column(String(255))
    project_id = Column(String(255))
    hours = Column(Float)