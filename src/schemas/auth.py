from typing import Annotated, Union
from pydantic import BaseModel


class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Union[str, None] = None

class User(BaseModel):
    id: str
    username: str
    email: Union[str, None] = None
    full_name: Union[str, None] = None
    first_name: Union[str, None] = None
    last_name: Union[str, None] = None
    role: Union[str, None] = 'USER'
    enabled: int = 1

# class UserCreate(BaseModel):
#     username: str
#     email: Union[str, None] = None
#     full_name: Union[str, None] = None
#     first_name: Union[str, None] = None
#     last_name: Union[str, None] = None
#     password: Union[str, None]

class UserCreate(BaseModel):
    username: str
    email: Union[str, None] = None
    full_name: Union[str, None] = None
    first_name: Union[str, None] = None
    last_name: Union[str, None] = None
    password: Union[str, None]
    role: Union[str, None] = "USER"

class UserInDB(User):
    password: str

class PasswordChange(BaseModel):
    username:str
    old_password:str
    new_password:str