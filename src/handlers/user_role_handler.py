from typing import Optional, Dict, List, Any
from src.utils.logger.custom_logging import LoggerMixin
from src.database.mysql_connection import mysql_connection


class UserRoleService(LoggerMixin):
    def __init__(self):
        super().__init__()
        self.db = mysql_connection
    
    def get_user_role(self, user_id: str, organization_id: str) -> Optional[str]:
        try:
            query = """
                SELECT Role 
                FROM OrganizationUser 
                WHERE UserId = %s AND OrganizationId = %s AND Status = 10
            """
            
            result = self.db.execute_query(query, (user_id, organization_id))
            
            if not result:
                self.logger.warning(f"No role found for user {user_id} in organization {organization_id}")
                return None
                
            # 1 = ADMIN, 2 = USER (ADMIN: 10)
            role_id = result[0]['Role']
            
            if role_id == 10:
                return "ADMIN"
            elif role_id == 2:
                return "USER"
            else:
                return f"ROLE_{role_id}"
                
        except Exception as e:
            self.logger.error(f"Error getting user role: {str(e)}")
            return None
    
    def get_user_organizations(self, user_id: str) -> List[Dict[str, Any]]:
        try:
            query = """
                SELECT 
                    ou.OrganizationId, 
                    o.Name as organization_name, 
                    o.Code as organization_code,
                    ou.Role as role_id
                FROM 
                    OrganizationUser ou
                JOIN 
                    Organization o ON ou.OrganizationId = o.Id
                WHERE 
                    ou.UserId = %s AND ou.Status = 10 AND o.Status = 10
            """
            
            results = self.db.execute_query(query, (user_id,))
            
            organizations = []
            for row in results:
                role_id = row['role_id']
                role = "ADMIN" if role_id == 10 else "USER" if role_id == 2 else f"ROLE_{role_id}"
                
                organizations.append({
                    "organization_id": str(row['OrganizationId']),
                    "name": row['organization_name'],
                    "code": row['organization_code'],
                    "role": role
                })
                
            return organizations
                
        except Exception as e:
            self.logger.error(f"Error getting user organizations: {str(e)}")
            return []
    
    def verify_access(self, user_id: str, organization_id: str, required_role: str = "USER") -> bool:
        role = self.get_user_role(user_id, organization_id)
        
        if role is None:
            return False
            
        if required_role == "ADMIN":
            return role == "ADMIN"
        else:
            return role in ["USER", "ADMIN"]
            
    def is_admin(self, user_id: str, organization_id: str) -> bool:
        return self.verify_access(user_id, organization_id, "ADMIN")
    
    def verify_user_exists(self, user_id: str) -> bool:
        try:
            query = "SELECT COUNT(*) as count FROM User WHERE Id = %s AND Status = 10"
            result = self.db.execute_query(query, (user_id,))
            
            return result[0]['count'] > 0
                
        except Exception as e:
            self.logger.error(f"Error verifying user exists: {str(e)}")
            return False
    
    def verify_organization_exists(self, organization_id: str) -> bool:
        try:
            query = "SELECT COUNT(*) as count FROM Organization WHERE Id = %s AND Status = 10"
            result = self.db.execute_query(query, (organization_id,))
            
            return result[0]['count'] > 0
                
        except Exception as e:
            self.logger.error(f"Error verifying organization exists: {str(e)}")
            return False
    
    def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        try:
            query = """
                SELECT 
                    Id, Code, Email, Firstname, Lastname, 
                    Phone, Gender, Avatar, DefaultOrganizationId, Type
                FROM 
                    User 
                WHERE 
                    Id = %s AND Status = 10
            """
            
            result = self.db.execute_query(query, (user_id,))
            
            if not result:
                return None
                
            user_info = result[0]
            
            return {
                "user_id": str(user_info['Id']),
                "code": user_info['Code'],
                "email": user_info['Email'],
                "first_name": user_info['Firstname'],
                "last_name": user_info['Lastname'],
                "full_name": f"{user_info['Firstname']} {user_info['Lastname']}".strip(),
                "phone": user_info['Phone'],
                "gender": user_info['Gender'],
                "avatar": user_info['Avatar'],
                "default_organization_id": str(user_info['DefaultOrganizationId']) if user_info['DefaultOrganizationId'] else None,
                "type": user_info['Type']
            }
                
        except Exception as e:
            self.logger.error(f"Error getting user info: {str(e)}")
            return None