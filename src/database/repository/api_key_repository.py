import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from src.database.models.schemas import APIKey
from src.database.db_connection import db
from src.utils.logger.custom_logging import LoggerMixin


class APIKeyRepository(LoggerMixin):
    def __init__(self):
        super().__init__()
        
    def create_api_key(
        self,
        user_id: str,
        api_key: str,
        expiry_date: datetime,
        organization_id: Optional[str] = None,
        name: Optional[str] = None
    ) -> str:
        try:
            with db.session_scope() as session:
                api_key_id = uuid.uuid4()
                new_api_key = APIKey(
                    id=api_key_id,
                    user_id=user_id,
                    organization_id=organization_id,
                    api_key=api_key,
                    name=name,
                    expiry_date=expiry_date,
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                    usage_count=0
                )
                
                session.add(new_api_key)
                
            self.logger.info(f"Created API key for user {user_id}")
            return str(api_key_id)
            
        except Exception as e:
            self.logger.error(f"Error creating API key: {str(e)}")
            raise
            
    # def get_api_key_by_value(self, api_key: str) -> Optional[APIKey]:
    #     try:
    #         with db.session_scope() as session:
    #             return session.query(APIKey).filter(APIKey.api_key == api_key).first()
                
    #     except Exception as e:
    #         self.logger.error(f"Error getting API key: {str(e)}")
    #         return None

    # def get_api_key_by_value(self, api_key: str) -> Optional[APIKey]:
    #     try:
    #         with db.session_scope() as session:
    #             api_key_obj = session.query(APIKey).filter(APIKey.api_key == api_key).first()
    #             if api_key_obj:
    #                 # Nếu cần, truy cập thuộc tính để đảm bảo chúng được load (nếu có lazy load)
    #                 _ = api_key_obj.is_active  
    #                 # Sau đó tách đối tượng khỏi session để tránh DetachedInstanceError
    #                 session.expunge(api_key_obj)
    #             return api_key_obj
    #     except Exception as e:
    #         self.logger.error(f"Error getting API key: {str(e)}")
    #         return None
    def get_api_key_by_value(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Lấy API key theo giá trị và chuyển đổi thành dict để tránh DetachedInstanceError
        
        Args:
            api_key: Giá trị API key cần tìm
            
        Returns:
            Optional[Dict[str, Any]]: Dữ liệu API key dưới dạng dictionary hoặc None nếu không tìm thấy
        """
        try:
            with db.session_scope() as session:
                api_key_obj = session.query(APIKey).filter(APIKey.api_key == api_key).first()
                
                if api_key_obj is None:
                    return None
                    
                # Chuyển đổi đối tượng APIKey thành một dictionary để tránh vấn đề lazy loading
                # và DetachedInstanceError khi session đóng
                api_key_dict = {
                    "id": str(api_key_obj.id),
                    "user_id": api_key_obj.user_id,
                    "organization_id": api_key_obj.organization_id,
                    "api_key": api_key_obj.api_key,
                    "name": api_key_obj.name,
                    "expiry_date": api_key_obj.expiry_date,
                    "is_active": api_key_obj.is_active,
                    "last_used": api_key_obj.last_used,
                    "created_at": api_key_obj.created_at,
                    "rate_limit": getattr(api_key_obj, 'rate_limit', 100),  # Mặc định nếu không có
                    "usage_count": api_key_obj.usage_count
                }
                
                return api_key_dict
                    
        except Exception as e:
            self.logger.error(f"Error getting API key: {str(e)}")
            return None

            
    # def get_api_key_by_id(self, api_key_id: str) -> Optional[APIKey]:
    #     try:
    #         with db.session_scope() as session:
    #             return session.query(APIKey).filter(APIKey.id == api_key_id).first()
                
    #     except Exception as e:
    #         self.logger.error(f"Error getting API key by ID: {str(e)}")
    #         return None
    def get_api_key_by_id(self, api_key_id: str) -> Optional[Dict[str, Any]]:
        """
        Lấy API key theo ID và chuyển đổi thành dict để tránh DetachedInstanceError
        
        Args:
            api_key_id: ID của API key cần tìm
            
        Returns:
            Optional[Dict[str, Any]]: Dữ liệu API key dưới dạng dictionary hoặc None nếu không tìm thấy
        """
        try:
            with db.session_scope() as session:
                api_key_obj = session.query(APIKey).filter(APIKey.id == api_key_id).first()
                
                if api_key_obj is None:
                    return None
                    
                # Chuyển đổi đối tượng APIKey thành một dictionary
                api_key_dict = {
                    "id": str(api_key_obj.id),
                    "user_id": api_key_obj.user_id,
                    "organization_id": api_key_obj.organization_id,
                    "api_key": api_key_obj.api_key,
                    "name": api_key_obj.name,
                    "expiry_date": api_key_obj.expiry_date,
                    "is_active": api_key_obj.is_active,
                    "last_used": api_key_obj.last_used,
                    "created_at": api_key_obj.created_at,
                    "rate_limit": getattr(api_key_obj, 'rate_limit', 100),  # Mặc định nếu không có
                    "usage_count": api_key_obj.usage_count
                }
                
                return api_key_dict
                    
        except Exception as e:
            self.logger.error(f"Error getting API key by ID: {str(e)}")
            return None
            
    def get_api_keys_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            with db.session_scope() as session:
                api_keys = session.query(APIKey).filter(APIKey.user_id == user_id).all()
                
                result = []
                for key in api_keys:
                    result.append({
                        "id": str(key.id),
                        "name": key.name,
                        "user_id": key.user_id,
                        "organization_id": key.organization_id,
                        "expiry_date": key.expiry_date,
                        "is_active": key.is_active,
                        "last_used": key.last_used,
                        "created_at": key.created_at,
                        "usage_count": key.usage_count
                    })
                
                return result
                
        except Exception as e:
            self.logger.error(f"Error getting API keys for user {user_id}: {str(e)}")
            return []
            
    def update_api_key_usage(self, api_key: str) -> bool:
        try:
            with db.session_scope() as session:
                key = session.query(APIKey).filter(APIKey.api_key == api_key).first()
                
                if key:
                    key.last_used = datetime.now(timezone.utc)
                    key.usage_count += 1
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(f"Error updating API key usage: {str(e)}")
            return False
            
    def deactivate_api_key(self, api_key_id: str) -> bool:
        try:
            with db.session_scope() as session:
                key = session.query(APIKey).filter(APIKey.id == api_key_id).first()
                
                if key:
                    key.is_active = False
                    self.logger.info(f"Deactivated API key {api_key_id}")
                    return True
                
                return False
                
        except Exception as e:
            self.logger.error(f"Error deactivating API key: {str(e)}")
            return False
            
    def delete_api_key(self, api_key_id: str) -> bool:
        try:
            with db.session_scope() as session:
                result = session.query(APIKey).filter(APIKey.id == api_key_id).delete()
                
                self.logger.info(f"Deleted API key {api_key_id}")
                return result > 0
                
        except Exception as e:
            self.logger.error(f"Error deleting API key: {str(e)}")
            return False