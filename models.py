from sqlmodel import Field, SQLModel, create_engine
from typing import Optional

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password: str
    email: str

class Employee(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    owner_id: int = Field(foreign_key="user.id") 

class Shift(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    shift_name: str
    start_time: str 
    end_time: str   
    owner_id: int = Field(foreign_key="user.id")