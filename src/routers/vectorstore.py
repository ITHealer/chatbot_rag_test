from fastapi.routing import APIRouter
from fastapi import status, Response, Depends, Request, HTTPException
from typing import Dict, Any, List
from src.handlers.vector_store_handler import VectorStoreQdrant
from src.handlers.api_key_auth_handler import APIKeyAuth
from src.schemas.response import BasicResponse

router = APIRouter(prefix="/vectorstore")
api_key_auth = APIKeyAuth()

@router.post('/create_collection',
             response_description='Create collection in Qdrant')
async def create_collection(
    request: Request,
    response: Response,
    collection_name: str,
    api_key_data: Dict[str, Any] = Depends(api_key_auth.author_with_api_key)
):
    try:
        # Lấy thông tin user_id và organization_id từ request state
        user_id = getattr(request.state, "user_id", None)
        organization_id = getattr(request.state, "organization_id", None)
        
        if not user_id:
            response.status_code = status.HTTP_401_UNAUTHORIZED
            return BasicResponse(
                status="Failed",
                message="User authentication required",
                data=None
            )
        
        # Kiểm tra quyền - chỉ admin mới có thể tạo collection
        user_role = getattr(request.state, "role", None)
        if user_role not in ["ADMIN"]:
            response.status_code = status.HTTP_403_FORBIDDEN
            return BasicResponse(
                status="Failed",
                message="Only administrators can create collections",
                data=None
            )
        
        # Tạo user object từ thông tin đã xác thực
        user = {
            "id": user_id,
            "role": user_role
        }
        
        resp = VectorStoreQdrant().create_qdrant_collection(
            collection_name=collection_name, 
            user=user,
            organization_id=organization_id
        )
        
        if resp.data:
            response.status_code = status.HTTP_200_OK
        else:
            response.status_code = status.HTTP_400_BAD_REQUEST
        
        return resp
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return BasicResponse(
            status="Failed",
            message=f"Error creating collection: {str(e)}",
            data=None
        )

@router.post('/delete_collection',
             response_description='Delete collection in Qdrant')
async def delete_collection(
    request: Request,
    response: Response,
    collection_name: str,
    api_key_data: Dict[str, Any] = Depends(api_key_auth.author_with_api_key)
):
    """
    Xóa collection trong Qdrant
    
    Args:
        request: Request object chứa thông tin user từ API key authentication
        response: Response object
        collection_name: Tên collection cần xóa
        api_key_data: Thông tin API key được xác thực
        
    Returns:
        BasicResponse: Kết quả xóa collection
    """
    try:
        # Lấy thông tin user_id và organization_id từ request state
        user_id = getattr(request.state, "user_id", None)
        organization_id = getattr(request.state, "organization_id", None)
        
        if not user_id:
            response.status_code = status.HTTP_401_UNAUTHORIZED
            return BasicResponse(
                status="Failed",
                message="User authentication required",
                data=None
            )
        
        # Kiểm tra quyền - chỉ admin mới có thể xóa collection
        user_role = getattr(request.state, "role", None)
        if user_role not in ["ADMIN"]:
            response.status_code = status.HTTP_403_FORBIDDEN
            return BasicResponse(
                status="Failed",
                message="Only administrators can delete collections",
                data=None
            )
        
        # Tạo user object từ thông tin đã xác thực
        user = {
            "id": user_id,
            "role": user_role
        }
        
        resp = VectorStoreQdrant().delete_qdrant_collection(
            collection_name=collection_name, 
            user=user,
            organization_id=organization_id
        )
        
        if resp.data:
            response.status_code = status.HTTP_200_OK
        else:
            response.status_code = status.HTTP_400_BAD_REQUEST
        
        return resp
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return BasicResponse(
            status="Failed",
            message=f"Error deleting collection: {str(e)}",
            data=None
        )

@router.get('/list_collections',
            response_description='List all collections in Qdrant')
async def list_collections(
    request: Request,
    response: Response,
    api_key_data: Dict[str, Any] = Depends(api_key_auth.author_with_api_key)
):
    """
    Liệt kê tất cả collection trong Qdrant mà người dùng có quyền truy cập
    
    Args:
        request: Request object chứa thông tin user từ API key authentication
        response: Response object
        api_key_data: Thông tin API key được xác thực
        
    Returns:
        Response với danh sách collection
    """
    try:
        # Lấy thông tin user_id và organization_id từ request state
        user_id = getattr(request.state, "user_id", None)
        organization_id = getattr(request.state, "organization_id", None)
        
        if not user_id:
            response.status_code = status.HTTP_401_UNAUTHORIZED
            return {"status": "Failed", "message": "User authentication required", "data": None}
        
        # Tạo user object từ thông tin đã xác thực
        user_role = getattr(request.state, "role", None)
        user = {
            "id": user_id,
            "role": user_role,
            "is_admin": user_role == "ADMIN"
        }
        
        # Lấy danh sách collection với lọc theo organization_id
        try:
            collections = VectorStoreQdrant().list_qdrant_collections(
                user=user, 
                organization_id=organization_id
            )
            response.status_code = status.HTTP_200_OK
            return {"status": "Success", "message": "List collections success", "data": collections}
        except Exception as e:
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {"status": "Failed", "message": str(e), "data": None}
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": "Failed", "message": f"Error listing collections: {str(e)}", "data": None}
