'''
This file contains the Pydantic models for the User and Module classes used in the app. These models define the structure of the data that is sent and received by the API endpoints.
'''
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