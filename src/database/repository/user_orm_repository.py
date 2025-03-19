from typing import Dict, List, Optional, Any, Union
import uuid
from datetime import datetime

from src.database.models.schemas import ChatSessions, APIKey
from src.database.db_connection import db
from src.utils.logger.custom_logging import LoggerMixin
from src.database.mysql_connection import mysql_connection

class UserORMRepository(LoggerMixin):
    """
    Repository for user-related operations that interfaces with:
    1. PostgreSQL for API Key and chat sessions
    2. MySQL for actual user data (via mysql_connection helper)
    """
    
    def __init__(self):
        super().__init__()
    
    def create_connection(self):
        """Create and return a PostgreSQL connection (for backward compatibility)"""
        return db.get_connection()
    
    def is_exist_user(self, user_id: str) -> bool:
        """
        Check if a user exists by querying MySQL
        
        Args:
            user_id: String ID of the user to check
            
        Returns:
            bool: True if user exists, False otherwise
        """
        try:
            user_info = mysql_connection.get_user_by_id(user_id)
            return user_info is not None
        except Exception as e:
            self.logger.error(f"Error checking if user exists: {str(e)}")
            return False
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user information from MySQL by user ID
        
        Args:
            user_id: String ID of the user
            
        Returns:
            Optional[Dict[str, Any]]: User data or None if not found
        """
        try:
            return mysql_connection.get_user_by_id(user_id)
        except Exception as e:
            self.logger.error(f"Error getting user by ID: {str(e)}")
            return None
    
    def get_user_role(self, user_id: str, organization_id: Optional[str] = None) -> Optional[str]:
        """
        Get user role, optionally within a specific organization
        
        Args:
            user_id: String ID of the user
            organization_id: Optional organization ID for context-specific role
            
        Returns:
            Optional[str]: Role string or None if not found
        """
        try:
            if organization_id:
                # Get role in specific organization context
                user_org = mysql_connection.query_user_organization(user_id, organization_id)
                return user_org.get('role') if user_org else None
            else:
                # Get general user info and extract role
                user_info = mysql_connection.get_user_by_id(user_id)
                return user_info.get('role') if user_info else None
        except Exception as e:
            self.logger.error(f"Error getting user role: {str(e)}")
            return None
    
    def get_sessions_from_user(self, user_id: str, limit: int = 10, organization_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get chat sessions for a user from PostgreSQL
        
        Args:
            user_id: String ID of the user
            limit: Maximum number of sessions to return
            organization_id: Optional organization ID to filter by
            
        Returns:
            List[Dict[str, Any]]: List of chat sessions
        """
        try:
            with db.session_scope() as session:
                query = session.query(ChatSessions).filter(ChatSessions.user_id == user_id)
                
                # Filter by organization if provided
                if organization_id:
                    query = query.filter(ChatSessions.organization_id == organization_id)
                    
                # Order by start date and limit results
                query = query.order_by(ChatSessions.start_date.desc()).limit(limit)
                sessions = query.all()
                
                # Convert to dictionary within the session
                return [
                    {
                        "id": str(s.id),
                        "title": s.title,
                        "start_date": s.start_date.isoformat() if s.start_date else None,
                        "organization_id": s.organization_id
                    } 
                    for s in sessions
                ]
        except Exception as e:
            self.logger.error(f"Error getting sessions for user {user_id}: {str(e)}")
            return []
    
    def check_is_admin(self, user_id: str, organization_id: Optional[str] = None) -> bool:
        """
        Check if a user has admin role
        
        Args:
            user_id: String ID of the user
            organization_id: Optional organization context (if None, checks global role)
            
        Returns:
            bool: True if user is admin, False otherwise
        """
        role = self.get_user_role(user_id, organization_id)
        return role == "ADMIN" if role else False
    
    def get_api_keys_by_user(self, user_id: str, organization_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get API keys belonging to a user
        
        Args:
            user_id: String ID of the user
            organization_id: Optional organization ID to filter by
            
        Returns:
            List[Dict[str, Any]]: List of API keys
        """
        try:
            with db.session_scope() as session:
                query = session.query(APIKey).filter(APIKey.user_id == user_id)
                
                # Filter by organization if provided
                if organization_id:
                    query = query.filter(APIKey.organization_id == organization_id)
                
                # Get only active keys
                query = query.filter(APIKey.is_active == True)
                
                # Sort by creation date
                query = query.order_by(APIKey.created_at.desc())
                
                keys = query.all()
                
                # Convert to dictionaries within session scope
                result = []
                for key in keys:
                    result.append({
                        "id": str(key.id),
                        "user_id": key.user_id,
                        "organization_id": key.organization_id,
                        "name": key.name,
                        "api_key": key.api_key[:10] + "...",  # Mask the key for security
                        "expiry_date": key.expiry_date.isoformat() if key.expiry_date else None,
                        "is_active": key.is_active,
                        "created_at": key.created_at.isoformat() if key.created_at else None,
                        "last_used": key.last_used.isoformat() if key.last_used else None,
                        "usage_count": key.usage_count
                    })
                
                return result
        except Exception as e:
            self.logger.error(f"Error getting API keys for user {user_id}: {str(e)}")
            return []



# from typing import Dict, List, Optional, Any, Union
# import uuid
# from datetime import datetime

# from src.database.models.schemas import Users
# from src.database.db_connection import db
# from src.utils.logger.custom_logging import LoggerMixin

# class UserORMRepository(LoggerMixin):
#     """Repository for User operations using SQLAlchemy ORM"""
    
#     def __init__(self):
#         super().__init__()
        
#     def is_exist_user(self, username: str) -> bool:
#         """Check if a user with the given username exists"""
#         with db.session_scope() as session:
#             return session.query(session.query(Users).filter(Users.username == username).exists()).scalar()
    
#     def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
#         """Get user information by username"""
#         with db.session_scope() as session:
#             user = session.query(Users).filter(Users.username == username).first()
#             if not user:
#                 return None
            
#             return {
#                 "id": str(user.id),
#                 "username": user.username,
#                 "full_name": user.full_name,
#                 "first_name": user.first_name,
#                 "last_name": user.last_name,
#                 "role": user.role,
#                 "enabled": user.enabled
#             }
    
#     def get_all(self) -> Dict[str, Dict[str, Any]]:
#         """Get all users as a dictionary indexed by username"""
#         users_dict = {}
        
#         with db.session_scope() as session:
#             all_users = session.query(Users).all()
            
#             # Chuyển đổi đối tượng ORM thành dict trong phạm vi session
#             for user in all_users:
#                 # Truy cập tất cả thuộc tính trong session
#                 users_dict[user.username] = {
#                     "id": str(user.id),
#                     "username": user.username,
#                     "password": user.password,
#                     "full_name": user.full_name,
#                     "first_name": user.first_name,
#                     "last_name": user.last_name,
#                     "role": user.role,
#                     "enabled": user.enabled
#                 }
        
#         # Trả về dict là an toàn vì không phụ thuộc vào session
#         return users_dict
    
#     def create_user(self, username: str, password: str, email: str, 
#                    full_name: str = '', first_name: str = '', 
#                    last_name: str = '', role: str = 'USER') -> str:
#         """Create a new user and return the username"""
#         with db.session_scope() as session:
#             new_user = Users(
#                 id=uuid.uuid4(),
#                 username=username,
#                 password=password,
#                 email=email,
#                 full_name=full_name,
#                 first_name=first_name,
#                 last_name=last_name,
#                 role=role,
#                 enabled=1,
#                 created=datetime.now()
#             )
            
#             session.add(new_user)
#             session.commit()
#             return username
    
#     def get_user_role(self, username: str) -> Optional[str]:
#         """Get the role of a user by username"""
#         with db.session_scope() as session:
#             user = session.query(Users).filter(Users.username == username).first()
#             return user.role if user else None
    
#     def change_password(self, username: str, new_hashed_password: str) -> bool:
#         """Change a user's password"""
#         with db.session_scope() as session:
#             user = session.query(Users).filter(Users.username == username).first()
#             if not user:
#                 return False
                
#             user.password = new_hashed_password
#             session.commit()
#             return True
    
#     def get_sessions_from_user(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
#         """Get chat sessions for a user"""
#         with db.session_scope() as session:
#             user = session.query(Users).filter(Users.id == user_id).first()
#             if not user:
#                 return []
                
#             # Cần eager loading để tránh lỗi detached
#             sessions = user.chat_sessions[:limit]
            
#             # Chuyển đổi thành dict trong phạm vi session
#             return [{"id": str(s.id), "title": s.title} for s in sessions]