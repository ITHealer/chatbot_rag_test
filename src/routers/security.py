from fastapi.routing import APIRouter
from fastapi import status, Response, Request, Depends, HTTPException, Body
from typing import Dict, Optional, List, Any  # Thêm import Any từ typing
from pydantic import BaseModel, Field
from datetime import datetime

from src.schemas.response import BasicResponse
from src.handlers.api_key_auth_handler import APIKeyAuth
from src.utils.logger.custom_logging import LoggerMixin

router = APIRouter()

# API key authentication instance
api_key_auth = APIKeyAuth()

class APIKeyCreate(BaseModel):
    user_id: str
    organization_id: Optional[str] = None
    name: Optional[str] = Field(None, description="Descriptive name for API key")
    expires_in_days: int = Field(365, description="Number of days before API key expires")

class OrganizationInfo(BaseModel):
    organization_id: str
    name: str
    role: str

class APIKeyResponse(BaseModel):
    id: str
    api_key: str
    user_id: str
    organization_id: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    expiry_date: datetime
    is_active: bool
    created_at: Optional[datetime] = None

class APIKeyInfo(BaseModel):
    id: str
    name: Optional[str] = None
    user_id: str
    organization_id: Optional[str] = None
    role: Optional[str] = None
    expiry_date: datetime
    is_active: bool
    last_used: Optional[datetime] = None
    created_at: datetime
    usage_count: int


@router.post('/api-keys/create', response_description='Create new API key', response_model=BasicResponse)
async def create_api_key(
    response: Response,
    api_key_data: APIKeyCreate = Body(...),
) -> Dict:
    try:
        api_key_info = api_key_auth.create_api_key(
            user_id=api_key_data.user_id,
            organization_id=api_key_data.organization_id,
            name=api_key_data.name,
            expires_in_days=api_key_data.expires_in_days
        )
        
        resp = BasicResponse(
            status='success',
            message='API key has been created successfully.',
            data=api_key_info
        )
        response.status_code = status.HTTP_201_CREATED
    except ValueError as ve:
        resp = BasicResponse(
            status='failed',
            message=f'Unable to generate API key: {str(ve)}'
        )
        response.status_code = status.HTTP_400_BAD_REQUEST
    except Exception as e:
        resp = BasicResponse(
            status='failed',
            message=f'Unable to generate API key: {str(e)}'
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    return resp


@router.get("/api-keys/{user_id}", response_description="Get API Keys của người dùng")
async def get_user_api_keys(
    user_id: str,
    request: Request,
    current_api_key: Dict[str, Any] = Depends(api_key_auth.author_with_api_key)
):
    # Sử dụng cú pháp dictionary để truy cập thuộc tính
    if current_api_key["user_id"] != user_id:
        # Kiểm tra xem người dùng hiện tại có quyền admin không
        if "role" in current_api_key and current_api_key["role"] == "ADMIN":
            # Admin có thể xem API key của người dùng khác
            pass
        else:
            # Người dùng thường chỉ có thể xem API key của chính họ
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own API keys"
            )
    
    user_api_keys = api_key_auth.get_user_api_keys(user_id)
    
    # Mask API key values for security
    for key in user_api_keys:
        if "api_key" in key:
            key["api_key"] = f"{key['api_key'][:10]}..." if key.get("api_key") else None
    
    return BasicResponse(
        status="success",
        message="User API keys retrieved successfully",
        data=user_api_keys
    )

@router.post('/api-keys/{api_key_id}/revoke', response_description='Revoke API key', response_model=BasicResponse)
async def revoke_api_key(
    response: Response,
    api_key_id: str,
    current_api_key: Dict[str, Any] = Depends(api_key_auth.author_with_api_key)  # Sửa kiểu
) -> Dict:
    """
    Revoke API key (disable but not delete)

    Args:
        api_key_id: ID of API key to revoke (Note: fill api_key_id not api_key)
        current_api_key: API key in use (from authentication)

    Returns:
        BasicResponse: Result of revocation
    """
    try:
        # Sử dụng cú pháp dictionary để truy cập thuộc tính
        success = api_key_auth.revoke_api_key(api_key_id, current_api_key["user_id"])
        
        if success:
            resp = BasicResponse(
                status='success',
                message='API key has been successfully revoked'
            )
            response.status_code = status.HTTP_200_OK
        else:
            resp = BasicResponse(
                status='failed',
                message='API key not found or no revocation permission'
            )
            response.status_code = status.HTTP_404_NOT_FOUND
    except Exception as e:
        resp = BasicResponse(
            status='failed',
            message=f'Unable to revoke API key: {str(e)}'
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    return resp


@router.delete('/api-keys/{api_key_id}', response_description='Delete API key', response_model=BasicResponse)
async def delete_api_key(
    response: Response,
    api_key_id: str,
    current_api_key: Dict[str, Any] = Depends(api_key_auth.author_with_api_key)  # Sửa kiểu
) -> Dict:
    """
    Delete the API key completely from the system

    Args:
        api_key_id: ID of the API key to delete
        current_api_key: API key currently in use (from authentication)

    Returns:
        BasicResponse: Result of deletion
    """
    try:
        # Sử dụng cú pháp dictionary để truy cập thuộc tính
        success = api_key_auth.delete_api_key(api_key_id, current_api_key["user_id"])
        
        if success:
            resp = BasicResponse(
                status='success',
                message='API key đã được xóa thành công'
            )
            response.status_code = status.HTTP_200_OK
        else:
            resp = BasicResponse(
                status='failed',
                message='Không tìm thấy API key hoặc không có quyền xóa'
            )
            response.status_code = status.HTTP_404_NOT_FOUND
    except Exception as e:
        resp = BasicResponse(
            status='failed',
            message=f'Không thể xóa API key: {str(e)}'
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    return resp


@router.get('/api-keys/validate', response_description='Kiểm tra API key hiện tại', response_model=BasicResponse)
async def validate_api_key(
    response: Response,
    api_key_data: Dict[str, Any] = Depends(api_key_auth.author_with_api_key)  # Sửa kiểu
) -> Dict:
    """
    Xác thực và cung cấp thông tin về API key hiện tại
    
    Args:
        api_key_data: API key đang sử dụng (từ xác thực)
    
    Returns:
        BasicResponse: Thông tin về API key
    """
    if api_key_data:
        # Lấy vai trò nếu có organization_id
        role = None
        if api_key_data["organization_id"]:  # Sử dụng cú pháp dictionary
            role = api_key_auth.user_role_service.get_user_role(
                api_key_data["user_id"],  # Sử dụng cú pháp dictionary
                api_key_data["organization_id"]  # Sử dụng cú pháp dictionary
            )
        
        data = {
            "user_id": api_key_data["user_id"],  # Sử dụng cú pháp dictionary
            "organization_id": api_key_data["organization_id"],  # Sử dụng cú pháp dictionary
            "role": role,
            "id": str(api_key_data["id"]),  # Sử dụng cú pháp dictionary
            "expiry_date": api_key_data["expiry_date"],  # Sử dụng cú pháp dictionary
            "is_active": api_key_data["is_active"]  # Sử dụng cú pháp dictionary
        }
        
        resp = BasicResponse(
            status='success',
            message='API key hợp lệ',
            data=data
        )
        response.status_code = status.HTTP_200_OK
    else:
        resp = BasicResponse(
            status='failed',
            message='API key không hợp lệ'
        )
        response.status_code = status.HTTP_401_UNAUTHORIZED
    
    return resp


@router.get('/user/{user_id}/organizations', response_description='Lấy danh sách tổ chức của người dùng', response_model=BasicResponse)
async def get_user_organizations(
    response: Response,
    user_id: str,
    current_api_key: Dict[str, Any] = Depends(api_key_auth.author_with_api_key)  # Sửa kiểu
) -> Dict:
    """
    Lấy danh sách tổ chức và vai trò của người dùng
    
    Args:
        user_id: ID của người dùng
        current_api_key: API key đang sử dụng (từ xác thực)
    
    Returns:
        BasicResponse: Danh sách tổ chức và vai trò
    """
    # Kiểm tra xem người dùng có quyền truy cập không
    # Sử dụng cú pháp dictionary để truy cập thuộc tính
    if current_api_key["user_id"] != user_id:
        resp = BasicResponse(
            status='failed',
            message='Không có quyền truy cập thông tin tổ chức của người dùng khác'
        )
        response.status_code = status.HTTP_403_FORBIDDEN
        return resp
    
    try:
        organizations = api_key_auth.get_user_organizations(user_id)
        
        resp = BasicResponse(
            status='success',
            message=f'Đã tìm thấy {len(organizations)} tổ chức',
            data=organizations
        )
        response.status_code = status.HTTP_200_OK
    except Exception as e:
        resp = BasicResponse(
            status='failed',
            message=f'Không thể lấy danh sách tổ chức: {str(e)}'
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    
    return resp
