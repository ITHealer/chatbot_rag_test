from typing import Optional
from pydantic import BaseModel


class BasicResponse(BaseModel):
    status: str
    message: str
    data: Optional[dict | list | str] = None
