import uuid
import psycopg2
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.database.db_connection import db
from src.utils.logger.custom_logging import LoggerMixin


class VectorStoreDAL(LoggerMixin):
    """
    Data Access Layer for vector store collections management in PostgreSQL database.
    Handles CRUD operations for Qdrant collections and their metadata.
    """

    def __init__(self):
        super().__init__()
    
    def create_vector_store_collection(self, user_id: str, collection_name: str) -> str:
        """
        Create a new vector store collection record in the database
        
        Args:
            user_id: The ID of the owner
            collection_name: The name of the collection
            
        Returns:
            str: The ID of the created collection
        """
        # Sử dụng connection_scope để đảm bảo connection được đóng đúng cách
        with db.connection_scope() as connection:
            cursor = connection.cursor()
            try:
                # Check if collection already exists
                check_sql = """
                    SELECT id FROM vector_store_collections 
                    WHERE user_id = %s AND collection_name = %s
                """
                cursor.execute(check_sql, (user_id, collection_name))
                if cursor.fetchone():
                    self.logger.warning(f"Collection {collection_name} already exists for user {user_id}")
                    return None

                # Insert new collection
                sql = """
                    INSERT INTO vector_store_collections (
                        id, user_id, collection_name, created_at, status
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """
                
                collection_id = str(uuid.uuid4())
                created_at = datetime.now()
                status = True  # Active status
                
                cursor.execute(
                    sql, 
                    (collection_id, user_id, collection_name, created_at, status)
                )
                
                connection.commit()
                self.logger.info(f"Created vector store collection {collection_name} for user {user_id}")
                return collection_id
                
            except Exception as e:
                connection.rollback()
                self.logger.error(f"Error creating vector store collection: {str(e)}")
                raise
            finally:
                cursor.close()

    def get_collection_by_name(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """
        Get collection information by name
        """
        with db.connection_scope() as connection:
            cursor = connection.cursor()
            try:
                sql = """
                    SELECT id, user_id, collection_name, created_at, updated_at, status 
                    FROM vector_store_collections
                    WHERE collection_name = %s
                """
                
                cursor.execute(sql, (collection_name,))
                result = cursor.fetchone()
                
                if not result:
                    return None
                    
                return {
                    "id": result[0],
                    "user_id": result[1],
                    "collection_name": result[2],
                    "created_at": result[3],
                    "updated_at": result[4],
                    "status": result[5]
                }
                
            except Exception as e:
                self.logger.error(f"Error getting collection by name {collection_name}: {str(e)}")
                return None
            finally:
                cursor.close()

    def collection_own_by_user(self, user_id: str, collection_name: str) -> bool:
        """
        Check if a collection is owned by a specific user
        """
        with db.connection_scope() as connection:
            cursor = connection.cursor()
            try:
                sql = """
                    SELECT id FROM vector_store_collections 
                    WHERE user_id = %s AND collection_name = %s AND status = TRUE
                """
                
                cursor.execute(sql, (user_id, collection_name))
                result = cursor.fetchone()
                
                return result is not None
                
            except Exception as e:
                self.logger.error(f"Error checking collection ownership: {str(e)}")
                return False
            finally:
                cursor.close()

    def get_user_collections(self, user_id: str) -> List[str]:
        """
        Get all collections belonging to a user
        """
        with db.connection_scope() as connection:
            cursor = connection.cursor()
            try:
                sql = """
                    SELECT collection_name
                    FROM vector_store_collections
                    WHERE user_id = %s AND status = TRUE
                    ORDER BY created_at DESC
                """
                
                cursor.execute(sql, (user_id,))
                results = cursor.fetchall()
                
                # Extract collection names from results
                return [result[0] for result in results]
                
            except Exception as e:
                self.logger.error(f"Error getting collections for user {user_id}: {str(e)}")
                return []
            finally:
                cursor.close()

    def delete_vector_store_collection(self, user_id: str, collection_name: str) -> bool:
        """
        Delete a collection record
        Returns True if successful, False otherwise
        """
        with db.connection_scope() as connection:
            cursor = connection.cursor()
            try:
                # First check if user owns the collection
                check_sql = """
                    SELECT id FROM vector_store_collections 
                    WHERE user_id = %s AND collection_name = %s
                """
                cursor.execute(check_sql, (user_id, collection_name))
                if not cursor.fetchone():
                    self.logger.warning(f"User {user_id} does not own collection {collection_name}")
                    return False
                    
                # Delete the collection
                sql = """
                    DELETE FROM vector_store_collections 
                    WHERE user_id = %s AND collection_name = %s
                """
                
                cursor.execute(sql, (user_id, collection_name))
                connection.commit()
                
                rows_affected = cursor.rowcount
                self.logger.info(f"Deleted collection {collection_name} for user {user_id}")
                return rows_affected > 0
                
            except Exception as e:
                connection.rollback()
                self.logger.error(f"Error deleting collection {collection_name}: {str(e)}")
                return False
            finally:
                cursor.close()
                
    def get_all_collections(self) -> List[Dict[str, Any]]:
        """
        Get all collections in the system
        """
        with db.connection_scope() as connection:
            cursor = connection.cursor()
            try:
                sql = """
                    SELECT c.id, c.user_id, c.collection_name, c.created_at, 
                           c.updated_at, c.status, u.username
                    FROM vector_store_collections c
                    JOIN users u ON c.user_id = u.id
                    ORDER BY c.created_at DESC
                """
                
                cursor.execute(sql)
                results = cursor.fetchall()
                
                collections = []
                for result in results:
                    collections.append({
                        "id": result[0],
                        "user_id": result[1],
                        "collection_name": result[2],
                        "created_at": result[3],
                        "updated_at": result[4],
                        "status": result[5],
                        "owner_username": result[6]
                    })
                    
                return collections
                
            except Exception as e:
                self.logger.error(f"Error getting all collections: {str(e)}")
                return []
            finally:
                cursor.close()

# import uuid
# from datetime import datetime
# from typing import List, Dict, Any, Optional

# from src.database.db_connection import db  # Import singleton instance
# from src.utils.logger.custom_logging import LoggerMixin


# class VectorStoreDAL(LoggerMixin):
#     """
#     Data Access Layer for vector store collections management in PostgreSQL database.
#     Handles CRUD operations for Qdrant collections and their metadata.
#     """

#     def __init__(self):
#         super().__init__()
    
#     def create_vector_store_collection(self, user_id: str, collection_name: str) -> bool:
#         """
#         Create a new vector store collection record in the database
#         Returns True if successful, False otherwise
#         """
#         # Sử dụng connection_scope từ db singleton
#         with db.connection_scope() as connection:
#             cursor = connection.cursor()
#             try:
#                 # Check if collection already exists for this user
#                 check_sql = """
#                     SELECT id FROM vector_store_collections 
#                     WHERE user_id = %s AND collection_name = %s
#                 """
#                 cursor.execute(check_sql, (user_id, collection_name))
#                 if cursor.fetchone():
#                     self.logger.warning(f"Collection {collection_name} already exists for user {user_id}")
#                     return False

#                 # Insert new collection
#                 sql = """
#                     INSERT INTO vector_store_collections (
#                         id, user_id, collection_name, created_at, status
#                     ) VALUES (%s, %s, %s, %s, %s)
#                 """
                
#                 collection_id = str(uuid.uuid4())
#                 created_at = datetime.now()
#                 status = True  # Active status
                
#                 cursor.execute(
#                     sql, 
#                     (collection_id, user_id, collection_name, created_at, status)
#                 )
                
#                 # Connection will be automatically committed when exiting the context manager
#                 self.logger.info(f"Created vector store collection {collection_name} for user {user_id}")
#                 return True
                
#             except Exception as e:
#                 # Connection will be automatically rolled back on exception
#                 self.logger.error(f"Error creating vector store collection: {str(e)}")
#                 return False
#             finally:
#                 cursor.close()
#                 # Connection will be automatically closed by the context manager

#     def get_collection_by_name(self, collection_name: str) -> Optional[Dict[str, Any]]:
#         """
#         Get collection information by name
#         """
#         with db.connection_scope() as connection:
#             cursor = connection.cursor()
#             try:
#                 sql = """
#                     SELECT id, user_id, collection_name, created_at, updated_at, status 
#                     FROM vector_store_collections
#                     WHERE collection_name = %s
#                 """
                
#                 cursor.execute(sql, (collection_name,))
#                 result = cursor.fetchone()
                
#                 if not result:
#                     return None
                    
#                 return {
#                     "id": result[0],
#                     "user_id": result[1],
#                     "collection_name": result[2],
#                     "created_at": result[3],
#                     "updated_at": result[4],
#                     "status": result[5]
#                 }
                
#             except Exception as e:
#                 self.logger.error(f"Error getting collection by name {collection_name}: {str(e)}")
#                 return None
#             finally:
#                 cursor.close()

#     def collection_own_by_user(self, user_id: str, collection_name: str) -> bool:
#         """
#         Check if a collection is owned by a specific user
#         """
#         with db.connection_scope() as connection:
#             cursor = connection.cursor()
#             try:
#                 sql = """
#                     SELECT id FROM vector_store_collections 
#                     WHERE user_id = %s AND collection_name = %s AND status = TRUE
#                 """
                
#                 cursor.execute(sql, (user_id, collection_name))
#                 result = cursor.fetchone()
                
#                 return result is not None
                
#             except Exception as e:
#                 self.logger.error(f"Error checking collection ownership: {str(e)}")
#                 return False
#             finally:
#                 cursor.close()

#     def get_user_collections(self, user_id: str) -> List[str]:
#         """
#         Get all collection names belonging to a user
#         """
#         with db.connection_scope() as connection:
#             cursor = connection.cursor()
#             try:
#                 sql = """
#                     SELECT collection_name
#                     FROM vector_store_collections
#                     WHERE user_id = %s AND status = TRUE
#                     ORDER BY created_at DESC
#                 """
                
#                 cursor.execute(sql, (user_id,))
#                 results = cursor.fetchall()
                
#                 # Extract collection names from results
#                 return [result[0] for result in results]
                
#             except Exception as e:
#                 self.logger.error(f"Error getting collections for user {user_id}: {str(e)}")
#                 return []
#             finally:
#                 cursor.close()

#     def delete_vector_store_collection(self, user_id: str, collection_name: str) -> bool:
#         """
#         Delete a collection record
#         Returns True if successful, False otherwise
#         """
#         with db.connection_scope() as connection:
#             cursor = connection.cursor()
#             try:
#                 # First check if user owns the collection
#                 if not self.collection_own_by_user(user_id, collection_name):
#                     self.logger.warning(f"User {user_id} does not own collection {collection_name}")
#                     return False
                    
#                 # Delete the collection
#                 sql = """
#                     DELETE FROM vector_store_collections 
#                     WHERE user_id = %s AND collection_name = %s
#                 """
                
#                 cursor.execute(sql, (user_id, collection_name))
                
#                 rows_affected = cursor.rowcount
#                 self.logger.info(f"Deleted collection {collection_name} for user {user_id}")
#                 return rows_affected > 0
                
#             except Exception as e:
#                 self.logger.error(f"Error deleting collection {collection_name}: {str(e)}")
#                 return False
#             finally:
#                 cursor.close()