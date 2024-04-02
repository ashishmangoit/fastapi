from fastapi import FastAPI, Depends, HTTPException, status, Form
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session
import uvicorn
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import logging
from typing import List
from datetime import date
import auth
from models import DatasheetLink, TimeSheetData
from database import SessionLocal
import crud

app = FastAPI()

# Configure logging
logging.basicConfig(filename='app.log', level=logging.INFO)

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# User registration endpoint
@app.post("/register")
async def register_user(first_name: str = Form(...), last_name: str = Form(...), email: str = Form(...), password: str = Form(...), super_user: bool = Form(False), db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, email)
    if user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = auth.get_password_hash(password)
    db_user = crud.create_user(db=db, first_name=first_name, last_name=last_name, email=email, hashed_password=hashed_password, super_user=super_user)
    return {"message": "User created successfully"}

# User login endpoint
@app.post("/login")
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.create_access_token(data={"sub": user.email})
    response = {"access_token": access_token, "token_type": "bearer"}
    return response

# Endpoint to enter values for MasterDeveloper
@app.post("/create-master-developer")
async def create_master_developer(name: str = Form(...), team_lead: bool = Form(False), db: Session = Depends(get_db)):
    new_developer = crud.create_master_developer(db=db, name=name, team_lead=team_lead)
    return {"message": "Master Developer created successfully", "new_developer": new_developer.id}

# Endpoint to get all MasterDevelopers
@app.get("/get-master-developer")
async def get_master_developer(db: Session = Depends(get_db)):
    developers_json = crud.get_master_developers_data(db)
    return {"master_developer": developers_json}

# Endpoint to delete a MasterDeveloper
@app.delete("/delete-master-developer/{developer_id}")
async def delete_master_developer(developer_id: int, db: Session = Depends(get_db)):
    return crud.delete_master_developer(db, developer_id)

# Endpoint to enter values for MasterProjects
@app.post("/create-master-project")
async def create_master_project(project_name: str = Form(...), db: Session = Depends(get_db)):
    new_project = crud.create_master_project(db=db, project_name=project_name)
    return {"message": "Master Project created successfully", "project_id": new_project.id}

# Endpoint to get all MasterProjects
@app.get("/get-master-projects")
async def get_master_projects(db: Session = Depends(get_db)):
    projects_json = crud.get_master_projects_data(db)
    return {"master_projects": projects_json}

# Endpoint to delete a MasterProject
@app.delete("/delete-master-project/{project_id}")
async def delete_master_project(project_id: int, db: Session = Depends(get_db)):
    return crud.delete_master_project(db, project_id)

@app.post("/read-spreadsheet-data")
async def read_spreadsheet_data(sheet_link: str, db: Session = Depends(get_db)):
    # Google Sheets API authentication
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(credentials)

    # Open the specified Google Sheet and get data from sheet1
    sheet = client.open_by_url(sheet_link).sheet1
    data = sheet.get_all_values()
    
    headers = data[0]
    excel_data = []
    for row in data[1:]:
        if not all(cell == '' for cell in row):
            row_dict = {}
            for i in range(len(headers)):
                row_dict[headers[i]] = row[i]
            excel_data.append(row_dict)

    if not excel_data:
        raise HTTPException(status_code=404, detail="No data found in the spreadsheet")

    return {"excel_data": excel_data}

@app.post("/save-timesheet-data")
def save_timesheet_data_endpoint(timesheet_data: List[dict], db: Session = Depends(get_db)):
    try:
        saved_timesheets = crud.save_timesheet_data(timesheet_data, db)
        if saved_timesheets:
            return {"message": "TimeSheetData saved successfully"}
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error saving timesheet data")
    except Exception as e:
        logging.error(f"Error saving timesheet data: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error saving timesheet data")

@app.get("/get-timesheets-data")
async def get_timesheets_data(db: Session = Depends(get_db)):
    timesheets_data_json = crud.get_timesheets_data(db)
    return timesheets_data_json

@app.delete("/delete-today-timesheet-data")
async def delete_today_timesheet_data(db: Session = Depends(get_db)):
    today_date = date.today()
    print("Today's date:", today_date)

    # Get today's timesheet data based on the date part only
    timesheet_data = db.query(TimeSheetData).filter(
        func.date(TimeSheetData.date) == today_date
    ).all()

    if not timesheet_data:
        return {"message": "No timesheet data found for today"}

    print("Timesheet data to delete:", timesheet_data)

    # Delete today's timesheet data
    for data in timesheet_data:
        db.delete(data)

    db.commit()
    return {"message": "Today's timesheet data deleted successfully"}

# Endpoint to enter datasheet link
@app.post("/save-datasheet-link")
async def save_datasheet_link(datasheet_link: str = Form(...), db: Session = Depends(get_db)):
    existing_datasheets = db.query(DatasheetLink).all()

    for datasheet in existing_datasheets:
        datasheet.is_enabled = False

    new_datasheet = DatasheetLink(datasheet_link=datasheet_link, is_enabled=True)
    db.add(new_datasheet)
    db.commit()
    db.refresh(new_datasheet)

    return {"message": "Datasheet Link saved successfully", "datasheet_link": new_datasheet.datasheet_link, "is_enabled": new_datasheet.is_enabled}

@app.get("/")
def read_root():
    return {"Hello": "World"}