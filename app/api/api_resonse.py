from pydantic import BaseModel
from typing import Any, Optional
from fastapi.responses import JSONResponse

class BaseResponse(BaseModel):
    success: bool = True
    data: Optional[Any] = None
    message: Optional[str] = None

#Uitility functions
def success_response(data: Any, message: str = "Success"):
    return JSONResponse(status_code=200, 
                        content=BaseResponse(success=True, data=data, message=message).dict())


def error_response(message: str, status_code: int = 400):
    return JSONResponse(status_code=status_code, 
                        content=BaseResponse(success=False, message=message).dict())

