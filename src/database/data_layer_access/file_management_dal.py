import uuid
import psycopg2
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from src.database.db_connection import get_connection
from src.utils.logger.custom_logging import LoggerMixin


class FileManagementDAL(LoggerMixin):
    """
    Data Access Layer for file management in PostgreSQL database.
    Handles CRUD operations for document files and their metadata.
    """

    def __init__(self):
        super().__init__()
        self.connection = get_connection()

    def _get_cursor(self):
        """Get a cursor from the connection pool"""
        return self.connection.cursor()

    def create_file_record(
        self,
        file_name: str,
        extension: str,
        file_url: str,
        uploaded_by: str,
        size: int,
        sha256: str,
        collection_name: str,
        source: str = '',
    ) -> str:
        """
        Create a new file record in the database
        Returns the ID of the created record
        """
        cursor = self._get_cursor()
        try:
            sql = """
                INSERT INTO documents (
                    id, created_at, extension, file_name, miniourl, 
                    rooturl, size, status, created_by, sha256, collection_name
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            
            document_id = str(uuid.uuid4())
            created_at = datetime.now()
            status = True  # Active status
            
            cursor.execute(
                sql, 
                (
                    document_id, created_at, extension, file_name, 
                    file_url, source, size, status, uploaded_by, sha256, collection_name
                )
            )
            
            self.connection.commit()
            self.logger.info(f"Created file record for {file_name} with ID {document_id}")
            return document_id
            
        except Exception as e:
            self.connection.rollback()
            self.logger.error(f"Error creating file record: {str(e)}")
            raise
        finally:
            cursor.close()

    def get_file_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get file information by ID
        """
        cursor = self._get_cursor()
        try:
            sql = """
                SELECT id, file_name, extension, miniourl, rooturl, size, 
                       created_at, created_by, sha256, collection_name, status
                FROM documents
                WHERE id = %s
            """
            
            cursor.execute(sql, (document_id,))
            result = cursor.fetchone()
            
            if not result:
                return None
                
            return {
                "id": result[0],
                "file_name": result[1],
                "extension": result[2],
                "miniourl": result[3],
                "rooturl": result[4],
                "size": result[5],
                "created_at": result[6],
                "created_by": result[7],
                "sha256": result[8],
                "collection_name": result[9],
                "status": result[10]
            }
            
        except Exception as e:
            self.logger.error(f"Error getting file by ID {document_id}: {str(e)}")
            raise
        finally:
            cursor.close()

    def get_files_by_collection(self, collection_name: str) -> List[Dict[str, Any]]:
        """
        Get all files belonging to a collection
        """
        cursor = self._get_cursor()
        try:
            sql = """
                SELECT id, file_name, extension, miniourl, size, created_at, created_by
                FROM documents
                WHERE collection_name = %s AND status = TRUE
                ORDER BY created_at DESC
            """
            
            cursor.execute(sql, (collection_name,))
            results = cursor.fetchall()
            
            files = []
            for result in results:
                files.append({
                    "id": result[0],
                    "file_name": result[1],
                    "extension": result[2],
                    "miniourl": result[3],
                    "size": result[4],
                    "created_at": result[5],
                    "created_by": result[6]
                })
                
            return files
            
        except Exception as e:
            self.logger.error(f"Error getting files for collection {collection_name}: {str(e)}")
            raise
        finally:
            cursor.close()

    def update_file_record(self, document_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing file record
        Returns True if successful, False otherwise
        """
        if not updates:
            return False
            
        cursor = self._get_cursor()
        try:
            set_clause = ", ".join([f"{key} = %s" for key in updates.keys()])
            values = list(updates.values())
            
            sql = f"""
                UPDATE documents
                SET {set_clause}, updated_at = %s
                WHERE id = %s
            """
            
            values.append(datetime.now())  # updated_at
            values.append(document_id)
            
            cursor.execute(sql, values)
            self.connection.commit()
            
            rows_affected = cursor.rowcount
            return rows_affected > 0
            
        except Exception as e:
            self.connection.rollback()
            self.logger.error(f"Error updating file record {document_id}: {str(e)}")
            raise
        finally:
            cursor.close()

    def delete_file_record(self, document_id: str) -> bool:
        """
        Delete a file record by ID
        Returns True if successful, False otherwise
        """
        cursor = self._get_cursor()
        try:
            sql = "DELETE FROM documents WHERE id = %s"
            cursor.execute(sql, (document_id,))
            self.connection.commit()
            
            rows_affected = cursor.rowcount
            return rows_affected > 0
            
        except Exception as e:
            self.connection.rollback()
            self.logger.error(f"Error deleting file record {document_id}: {str(e)}")
            raise
        finally:
            cursor.close()

    def delete_record_by_collection(self, collection_name: str) -> int:
        """
        Delete all file records belonging to a collection
        Returns the number of records deleted
        """
        cursor = self._get_cursor()
        try:
            sql = "DELETE FROM documents WHERE collection_name = %s"
            cursor.execute(sql, (collection_name,))
            self.connection.commit()
            
            rows_affected = cursor.rowcount
            self.logger.info(f"Deleted {rows_affected} file records from collection {collection_name}")
            return rows_affected
            
        except Exception as e:
            self.connection.rollback()
            self.logger.error(f"Error deleting records for collection {collection_name}: {str(e)}")
            raise
        finally:
            cursor.close()

    def get_file_count_by_collection(self, collection_name: str) -> int:
        """
        Get the number of files in a collection
        """
        cursor = self._get_cursor()
        try:
            sql = "SELECT COUNT(*) FROM documents WHERE collection_name = %s AND status = TRUE"
            cursor.execute(sql, (collection_name,))
            result = cursor.fetchone()
            
            return result[0] if result else 0
            
        except Exception as e:
            self.logger.error(f"Error getting file count for collection {collection_name}: {str(e)}")
            raise
        finally:
            cursor.close()

    def check_file_exists(self, file_name: str, sha256: str) -> bool:
        """
        Check if a file with the given name and hash exists
        """
        cursor = self._get_cursor()
        try:
            sql = "SELECT id FROM documents WHERE file_name = %s AND sha256 = %s LIMIT 1"
            cursor.execute(sql, (file_name, sha256))
            result = cursor.fetchone()
            
            return result is not None
            
        except Exception as e:
            self.logger.error(f"Error checking if file exists {file_name}: {str(e)}")
            raise
        finally:
            cursor.close()

    def get_file_metadata(self, document_id: str) -> Tuple[str, str, str]:
        """
        Get file metadata (name, root URL, MinIO URL) by ID
        """
        cursor = self._get_cursor()
        try:
            sql = "SELECT file_name, rooturl, miniourl FROM documents WHERE id = %s LIMIT 1"
            cursor.execute(sql, (document_id,))
            result = cursor.fetchone()
            
            if not result:
                return None, None, None
                
            return result[0], result[1], result[2]
            
        except Exception as e:
            self.logger.error(f"Error getting file metadata for ID {document_id}: {str(e)}")
            raise
        finally:
            cursor.close()
            
    def search_files(
        self, 
        keyword: Optional[str] = None,
        extension: Optional[str] = None,
        collection_name: Optional[str] = None,
        created_by: Optional[str] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        limit: int = 10,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Search for files based on various criteria
        """
        cursor = self._get_cursor()
        try:
            conditions = ["status = TRUE"]
            params = []
            
            if keyword:
                conditions.append("LOWER(file_name) LIKE %s")
                params.append(f"%{keyword.lower()}%")
                
            if extension:
                conditions.append("extension = %s")
                params.append(extension)
                
            if collection_name:
                conditions.append("collection_name = %s")
                params.append(collection_name)
                
            if created_by:
                conditions.append("created_by = %s")
                params.append(created_by)
                
            if created_after:
                conditions.append("created_at >= %s")
                params.append(created_after)
                
            if created_before:
                conditions.append("created_at <= %s")
                params.append(created_before)
                
            where_clause = " AND ".join(conditions)
            
            # Count query
            count_sql = f"SELECT COUNT(*) FROM documents WHERE {where_clause}"
            cursor.execute(count_sql, params)
            total_count = cursor.fetchone()[0]
            
            # Data query
            data_sql = f"""
                SELECT id, file_name, extension, miniourl, size, created_at, created_by, collection_name
                FROM documents 
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            
            cursor.execute(data_sql, params + [limit, offset])
            results = cursor.fetchall()
            
            files = []
            for result in results:
                files.append({
                    "id": result[0],
                    "file_name": result[1],
                    "extension": result[2],
                    "miniourl": result[3],
                    "size": result[4],
                    "created_at": result[5],
                    "created_by": result[6],
                    "collection_name": result[7]
                })
                
            return {
                "total_count": total_count,
                "files": files
            }
            
        except Exception as e:
            self.logger.error(f"Error searching files: {str(e)}")
            raise
        finally:
            cursor.close()