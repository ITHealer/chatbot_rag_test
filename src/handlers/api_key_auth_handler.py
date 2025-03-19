import uuid
import secrets
import string
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader

from src.database.repository.api_key_repository import APIKeyRepository
from src.database.models.schemas import APIKey
from src.utils.logger.custom_logging import LoggerMixin
from src.handlers.user_role_handler import UserRoleService

# Header để lấy API key từ request
ORGANIZATION_ID_HEADER = APIKeyHeader(name="X-Organization-Id", auto_error=False)
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
# api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


class APIKeyAuth(LoggerMixin):
    def __init__(self):
        super().__init__()
        self.api_key_repo = APIKeyRepository()
        self.user_role_service = UserRoleService()

    async def author_with_api_key(
        self, 
        organization_id: str = Depends(ORGANIZATION_ID_HEADER),
        api_key: str = Depends(API_KEY_HEADER),
        request: Request = None,
        require_role: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Xác thực request dựa trên API key
        
        Args:
            api_key: API key từ header
            organization_id: ID tổ chức từ header (tùy chọn)
            request: Request object
            require_role: Vai trò yêu cầu tối thiểu ('USER' hoặc 'ADMIN'), nếu None thì không kiểm tra
            
        Returns:
            Optional[Dict[str, Any]]: Thông tin API key nếu xác thực thành công
            
        Raises:
            HTTPException: Nếu API key không hợp lệ hoặc hết hạn
        """
        if api_key is None:
            self.logger.warning("No API key provided")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
                headers={"WWW-Authenticate": "APIKey"}
            )
            
        # Lấy dữ liệu API key dưới dạng dictionary thay vì đối tượng ORM
        api_key_data = self.api_key_repo.get_api_key_by_value(api_key)
        
        if api_key_data is None:
            self.logger.warning(f"Invalid API key: {api_key[:10]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "APIKey"}
            )
            
        # Kiểm tra trạng thái hoạt động của API key
        if not api_key_data["is_active"]:
            self.logger.warning(f"Inactive API key: {api_key[:10]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is inactive",
                headers={"WWW-Authenticate": "APIKey"}
            )
            
        # Kiểm tra thời hạn của API key
        if api_key_data["expiry_date"]:
            expiry_date = api_key_data["expiry_date"]
            expiry_date_aware = expiry_date.replace(tzinfo=timezone.utc) if expiry_date.tzinfo is None else expiry_date
            if expiry_date_aware < datetime.now(timezone.utc):
                self.logger.warning(f"Expired API key: {api_key[:10]}...")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key has expired",
                    headers={"WWW-Authenticate": "APIKey"}
                )
        
        # Kiểm tra user_id có tồn tại trong hệ thống Frontend không
        user_exists = self.user_role_service.verify_user_exists(api_key_data["user_id"])
        if not user_exists:
            self.logger.warning(f"User {api_key_data['user_id']} not found in frontend system")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found in frontend system",
                headers={"WWW-Authenticate": "APIKey"}
            )
        
        # Sử dụng organization_id từ header nếu có, nếu không thì sử dụng từ API key
        effective_org_id = organization_id if organization_id else api_key_data["organization_id"]
        
        # Kiểm tra và xác thực quyền với tổ chức nếu có
        if effective_org_id:
            # Kiểm tra tổ chức có tồn tại không
            org_exists = self.user_role_service.verify_organization_exists(effective_org_id)
            if not org_exists:
                self.logger.warning(f"Organization {effective_org_id} not found in frontend system")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Organization not found in frontend system",
                    headers={"WWW-Authenticate": "APIKey"}
                )
            
            # Kiểm tra người dùng có quyền với tổ chức không
            has_access = self.user_role_service.verify_access(
                api_key_data["user_id"], 
                effective_org_id,
                require_role or "USER"
            )
            
            if not has_access:
                self.logger.warning(f"User {api_key_data['user_id']} does not have required access to organization {effective_org_id}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"User does not have required access to organization",
                    headers={"WWW-Authenticate": "APIKey"}
                )
        
        # Cập nhật thời gian sử dụng gần nhất và số lần sử dụng
        self.api_key_repo.update_api_key_usage(api_key)
        
        # Gắn thông tin user_id, organization_id và role vào request state để có thể truy cập từ các handler
        if request:
            request.state.user_id = api_key_data["user_id"]
            request.state.organization_id = effective_org_id
            
            # Lấy thông tin vai trò từ MySQL
            if effective_org_id:
                role = self.user_role_service.get_user_role(
                    api_key_data["user_id"], 
                    effective_org_id
                )
                request.state.role = role
                self.logger.debug(f"User {api_key_data['user_id']} has role {role} in organization {effective_org_id}")
            
            # Lấy thông tin chi tiết người dùng từ MySQL
            user_info = self.user_role_service.get_user_info(api_key_data["user_id"])
            if user_info:
                request.state.user_info = user_info
                
        # Thêm organization_id hiệu quả vào kết quả trả về
        api_key_data["effective_organization_id"] = effective_org_id
        
        return api_key_data
    
    async def admin_required(
        self,
        organization_id: str = Depends(ORGANIZATION_ID_HEADER),
        api_key: str = Depends(API_KEY_HEADER),
        request: Request = None
    ) -> Optional[Dict[str, Any]]:
        """
        Xác thực request và kiểm tra quyền Admin
        
        Args:
            api_key: API key từ header
            organization_id: ID tổ chức từ header
            request: Request object
            
        Returns:
            Optional[Dict[str, Any]]: Thông tin API key nếu xác thực thành công và người dùng là Admin
        """
        return await self.author_with_api_key(
            organization_id=organization_id,
            api_key=api_key,
            request=request,
            require_role="ADMIN"
        )

    def generate_api_key(self, length: int = 40) -> str:
        alphabet = string.ascii_letters + string.digits
        api_key = ''.join(secrets.choice(alphabet) for _ in range(length))
        
        return f"hongthai_{api_key}"

    def create_api_key(
        self, 
        user_id: str, 
        organization_id: Optional[str] = None,
        name: Optional[str] = None,
        expires_in_days: int = 365
    ) -> Dict[str, Any]:
        
        user_exists = self.user_role_service.verify_user_exists(user_id)
        self.logger.info(f"Check user id in database: {user_exists}")
        if not user_exists:
            raise ValueError(f"User {user_id} not found in frontend system")
        
        # Verify organization and access if organization_id is provided
        if organization_id:
            org_exists = self.user_role_service.verify_organization_exists(organization_id)
            if not org_exists:
                raise ValueError(f"Organization {organization_id} not found in frontend system")
            
            # Check if user has organization access
            has_access = self.user_role_service.verify_access(user_id, organization_id)
            if not has_access:
                raise ValueError(f"User {user_id} does not have access to organization {organization_id}")
                
        api_key = self.generate_api_key()
        expiry_date = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        
        api_key_id = self.api_key_repo.create_api_key(
            user_id=user_id,
            organization_id=organization_id,
            api_key=api_key,
            name=name,
            expiry_date=expiry_date
        )
        
        self.logger.info(f"Created API key for user {user_id}")
        
        role = None
        if organization_id:
            role = self.user_role_service.get_user_role(user_id, organization_id)
        
        # Get user info from MYSQL
        user_info = self.user_role_service.get_user_info(user_id)
        user_name = user_info.get('full_name') if user_info else None
        
        return {
            "id": api_key_id,
            "api_key": api_key,
            "user_id": user_id,
            "user_name": user_name,
            "organization_id": organization_id,
            "name": name,
            "role": role,
            "expiry_date": expiry_date.isoformat(),
            "is_active": True
        }


    def revoke_api_key(self, api_key_id: str, user_id: str = None) -> bool:
        """
        Thu hồi (hủy kích hoạt) API key
        
        Args:
            api_key_id: ID của API key cần thu hồi
            user_id: ID của người dùng (để kiểm tra quyền sở hữu)
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        if user_id:
            api_key_data = self.api_key_repo.get_api_key_by_id(api_key_id)
            if not api_key_data or api_key_data["user_id"] != user_id:
                self.logger.warning(f"User {user_id} attempted to revoke API key {api_key_id} they don't own")
                return False
                    
        return self.api_key_repo.deactivate_api_key(api_key_id)

    def delete_api_key(self, api_key_id: str, user_id: str = None) -> bool:
        """
        Xóa API key
        
        Args:
            api_key_id: ID của API key cần xóa
            user_id: ID của người dùng (để kiểm tra quyền sở hữu)
            
        Returns:
            bool: True nếu thành công, False nếu thất bại
        """
        if user_id:
            api_key_data = self.api_key_repo.get_api_key_by_id(api_key_id)
            if not api_key_data or api_key_data["user_id"] != user_id:
                self.logger.warning(f"User {user_id} attempted to delete API key {api_key_id} they don't own")
                return False
                    
        return self.api_key_repo.delete_api_key(api_key_id)

    def get_user_api_keys(self, user_id: str) -> list:
        user_exists = self.user_role_service.verify_user_exists(user_id)
        if not user_exists:
            self.logger.warning(f"User {user_id} not found in frontend system")
            return []
        
        # List API key from repository
        keys = self.api_key_repo.get_api_keys_by_user(user_id)
        self.logger.info(f"List APIKEYs: {keys}")
        
        # Get user info from MySQL
        user_info = self.user_role_service.get_user_info(user_id)
        
        for key in keys:
            org_id = key.get("organization_id")
            if org_id:
                role = self.user_role_service.get_user_role(user_id, org_id)
                key["role"] = role
                
                org_exists = self.user_role_service.verify_organization_exists(org_id)
                if org_exists:
                    key["organization_exists"] = True
                else:
                    key["organization_exists"] = False
            
            if user_info:
                key["user_name"] = user_info.get("full_name")
                key["user_email"] = user_info.get("email")
                
        return keys
        
    def get_user_organizations(self, user_id: str) -> List[Dict[str, Any]]:
        user_exists = self.user_role_service.verify_user_exists(user_id)
        if not user_exists:
            self.logger.warning(f"User {user_id} not found in frontend system")
            return []
        
        return self.user_role_service.get_user_organizations(user_id)