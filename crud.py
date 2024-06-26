from sqlalchemy.orm import Session
import logging
from models import User, MasterDeveloper, MasterProjects, TimeSheetData
from schemas import UserCreate

async def get_user_by_email(db: Session, email: str):
    user = db.query(User).filter(User.email == email).first()
    return user

def create_user(db: Session, user_data: UserCreate):
    db_user = User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        email=user_data.email,
        hashed_password=user_data.password,
        super_user=user_data.super_user
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_master_developer(db: Session, name: str, team_lead: bool):
    developer = MasterDeveloper(name=name, team_lead=team_lead)
    db.add(developer)
    db.commit()
    db.refresh(developer)
    return developer

def get_master_developers_data(db: Session):
    developers = db.query(MasterDeveloper.id, MasterDeveloper.name, MasterDeveloper.team_lead).all()
    developers_json = [{"Id": developer.id, "Name": developer.name, "TL": developer.team_lead} for developer in developers]
    return developers_json

def get_master_projects_data(db: Session):
    projects = db.query(MasterProjects.id, MasterProjects.project_name).all()
    projects_json = [{"Id": project.id, "Project_name": project.project_name} for project in projects]
    return projects_json

def create_master_project(db: Session, project_name: str):
    project = MasterProjects(project_name=project_name)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

def delete_master_developer(db: Session, developer_id: int):
    developer = db.query(MasterDeveloper).filter(MasterDeveloper.id == developer_id).first()
    if developer:
        db.delete(developer)
        db.commit()
        return {"message": "Master Developer deleted successfully"}
    else:
        return {"error": "Master Developer not found"}

def delete_master_project(db: Session, project_id: int):
    project = db.query(MasterProjects).filter(MasterProjects.id == project_id).first()
    if project:
        db.delete(project)
        db.commit()
        return {"message": "Master Project deleted successfully"}
    else:
        return {"error": "Master Project not found"}

def save_timesheet_data(timesheet_data, db: Session):
    try:
        for item in timesheet_data:
            new_timesheet = TimeSheetData(
                developer_id=item.get("developer_id"),
                team_lead_id=item.get("team_lead_id"),
                project_id=item.get("project_id"),
                hours=item.get("hours")
            )
            db.add(new_timesheet)

        db.commit()
        db.refresh(new_timesheet)

        return True
    except Exception as e:
        logging.error(f"Error saving timesheet data: {e}")
        raise

def get_timesheets_data(db: Session):
    timesheets_data = db.query(TimeSheetData).all()
    timesheets_data_json = []
    for data in timesheets_data:
        developer_name = db.query(MasterDeveloper.name).filter(MasterDeveloper.id == data.developer_id).first()[0]
        team_lead_name = db.query(MasterDeveloper.name).filter((MasterDeveloper.id == data.team_lead_id) & (MasterDeveloper.team_lead == True)).first()[0]
        project_name = db.query(MasterProjects.project_name).filter(MasterProjects.id == data.project_id).first()[0]
        timesheets_data_json.append({
            "Id": data.id,
            "Date": data.date,
            "Developer": developer_name,
            "Team Lead": team_lead_name,
            "Project": project_name,
            "Hours": data.hours
        })
    return timesheets_data_json