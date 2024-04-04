from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session
from oauth2client.service_account import ServiceAccountCredentials
from typing import List
from datetime import datetime
import gspread
import logging
from schemas import UserCreate, CreateMasterDeveloper, CreateMasterProject, SetDatasheetLink
from models import DatasheetLink, TimeSheetData
from database import SessionLocal
import auth
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
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    # Check email format
    if not auth.email_is_valid(user_data.email):
        raise HTTPException(status_code=400, detail="Invalid email format")

    # Check password complexity
    if not auth.is_password_complex(user_data.password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter, one lowercase letter, one digit, and one special character")

    # Check if the email is already registered
    user = crud.get_user_by_email(db, user_data.email)

    if user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash the password
    hashed_password = auth.get_password_hash(user_data.password)

    # Create user data using Pydantic model
    user_create_data = UserCreate(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        email=user_data.email,
        password=hashed_password,
        super_user=user_data.super_user
    )

    # Create the user in the database
    db_user = crud.create_user(db=db, user_data=user_create_data)

    return {"message": "User created successfully"}

# User login endpoint
@app.post("/login/", response_model=dict)
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Check email format
    if not auth.email_is_valid(form_data.username):
        raise HTTPException(status_code=400, detail="Invalid email format")

    user = await auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = auth.create_access_token(data={"sub": user.email})
    refresh_token = auth.create_refresh_token(data={"sub": user.email})
    
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

# User logout endpoint
@app.post("/logout/")
async def logout_user(current_user: str = Depends(auth.get_current_user)):
    # Your logout logic here, for example, invalidating the token
    return {"message": "Logout successful"}

@app.post("/refresh-token/")
async def refresh_token(refresh_token: str):
    get_refresh_token_data = await auth.get_refresh_token(refresh_token)
    return get_refresh_token_data

# Endpoint to enter values for MasterDeveloper
@app.post("/create-master-developer")
async def create_master_developer(developer_data: CreateMasterDeveloper, db: Session = Depends(get_db)):
    new_developer = crud.create_master_developer(db=db, name=developer_data.name, team_lead=developer_data.team_lead)
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
async def create_master_project(project_data: CreateMasterProject, db: Session = Depends(get_db)):
    new_project = crud.create_master_project(db=db, project_name=project_data.project_name)
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
async def read_spreadsheet_data(db: Session = Depends(get_db)):
    sheet_link = (db.query(DatasheetLink).filter(DatasheetLink.is_enabled == True).first()).datasheet_link
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
        if not timesheet_data or not timesheet_data[0]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid timesheet data received")
        
        # Validate the structure of each timesheet entry
        for entry in timesheet_data:
            if not isinstance(entry, dict) or "developer_id" not in entry or "team_lead_id" not in entry or "project_id" not in entry or "hours" not in entry:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid timesheet data format")

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

# Endpoint to delete timesheet data for a specific date
@app.delete("/delete-timesheet-data/{date_to_delete}")
async def delete_timesheet_data(date_to_delete: str, db: Session = Depends(get_db)):
    try:
        date_obj = datetime.strptime(date_to_delete, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    timesheet_data = db.query(TimeSheetData).filter(func.date(TimeSheetData.date) == date_obj).all()

    if not timesheet_data:
        return {"message": "No timesheet data found for the specified date"}

    for data in timesheet_data:
        db.delete(data)

    db.commit()
    return {"message": f"Timesheet data for {date_to_delete} deleted successfully"}

# Endpoint to enter datasheet link
@app.post("/save-datasheet-link")
async def save_datasheet_link(set_datasheet_link: SetDatasheetLink, db: Session = Depends(get_db)):
    existing_datasheets = db.query(DatasheetLink).all()
    for datasheet in existing_datasheets:
        datasheet.is_enabled = False

    existing_datasheet = db.query(DatasheetLink).filter(DatasheetLink.datasheet_link == set_datasheet_link.datasheet_link).first()
    if existing_datasheet:
        existing_datasheet.is_enabled = True
        db.commit()
        db.refresh(existing_datasheet)
        return {"message": "Datasheet Link updated successfully", "datasheet_link": existing_datasheet.datasheet_link, "is_enabled": existing_datasheet.is_enabled}
    else:
        new_datasheet = DatasheetLink(datasheet_link=set_datasheet_link.datasheet_link, is_enabled=True)
        db.add(new_datasheet)
        db.commit()
        db.refresh(new_datasheet)
        return {"message": "Datasheet Link saved successfully", "datasheet_link": new_datasheet.datasheet_link, "is_enabled": new_datasheet.is_enabled}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)