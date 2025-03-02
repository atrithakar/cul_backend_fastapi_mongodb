# filepath: /D:/projects/project_cul/fastapi backend/app/models.py
from pydantic import BaseModel, Field
from typing import Optional

class User(BaseModel):
    email: str = Field(..., alias="_id")
    password: str
    first_name: str
    last_name: Optional[str]
    username: str

class Module(BaseModel):
    module_id: int
    module_name: str
    module_url: str
    associated_user: str