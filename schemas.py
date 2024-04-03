from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    super_user: bool = False

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class CreateMasterDeveloper(BaseModel):
    name: str
    team_lead: bool = False

class CreateMasterProject(BaseModel):
    project_name: str

class SetDatasheetLink(BaseModel):
    datasheet_link: str