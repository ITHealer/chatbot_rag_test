import uuid
from datetime import datetime
from typing import List, Optional

from src.database.db_connection import db
from src.database.models.schemas import Collection
from src.utils.logger.custom_logging import LoggerMixin


class CollectionManagementService(LoggerMixin):
    """
    Service to manage collections metadata in the database.
    Synchronizes collection information between Qdrant and PostgreSQL.
    """

    def __init__(self):
        super().__init__()

    def create_collection(
        self, 
        collection_name: str, 
        user_id: str,
        organization_id: Optional[str] = None
    ) -> str:
        """
        Create a new collection record in the database
        
        Args:
            collection_name: Name of the collection
            user_id: ID of the user who owns this collection
            organization_id: ID of the organization that owns this collection
            
        Returns:
            str: ID of the created collection record
        """
        try:
            with db.session_scope() as session:
                # Check if collection already exists
                query = session.query(Collection).filter_by(
                    collection_name=collection_name
                )
                
                # Add organization filter if provided
                if organization_id:
                    query = query.filter_by(organization_id=organization_id)
                    
                existing = query.first()
                
                if existing:
                    self.logger.info(f"Collection {collection_name} already exists in database")
                    return str(existing.id)
                
                # Create new collection record
                collection_id = uuid.uuid4()
                new_collection = Collection(
                    id=collection_id,
                    user_id=user_id,
                    collection_name=collection_name,
                    organization_id=organization_id
                )
                
                session.add(new_collection)
                # Session is automatically committed by session_scope
                
                self.logger.info(f"Created collection record for {collection_name} with ID {collection_id}")
                return str(collection_id)
                
        except Exception as e:
            self.logger.error(f"Error creating collection record: {str(e)}")
            raise

    def delete_collection(
        self, 
        collection_name: str,
        organization_id: Optional[str] = None
    ) -> bool:
        """
        Delete a collection record from the database
        
        Args:
            collection_name: Name of the collection to delete
            organization_id: ID of the organization that owns this collection
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            with db.session_scope() as session:
                # Build delete query
                query = session.query(Collection).filter_by(
                    collection_name=collection_name
                )
                
                # Add organization filter if provided
                if organization_id:
                    query = query.filter_by(organization_id=organization_id)
                
                # Delete collection record
                result = query.delete()
                
                # Session is automatically committed by session_scope
                
                if result > 0:
                    self.logger.info(f"Deleted collection record for {collection_name}")
                    return True
                else:
                    self.logger.warning(f"No collection record found for {collection_name}")
                    return False
                
        except Exception as e:
            self.logger.error(f"Error deleting collection record: {str(e)}")
            return False

    def get_user_collections(
        self, 
        user_id: str,
        organization_id: Optional[str] = None
    ) -> List[str]:
        """
        Get all collections belonging to a user, optionally filtered by organization
        
        Args:
            user_id: ID of the user
            organization_id: Optional ID of the organization to filter by
            
        Returns:
            List[str]: List of collection names
        """
        try:
            with db.session_scope() as session:
                # Build query
                query = session.query(Collection.collection_name).filter_by(
                    user_id=user_id
                )
                
                # Add organization filter if provided
                if organization_id:
                    query = query.filter_by(organization_id=organization_id)
                
                collections = query.all()
                
                # Convert from list of tuples to list of strings
                return [c[0] for c in collections]
                
        except Exception as e:
            self.logger.error(f"Error getting user collections: {str(e)}")
            return []

    def is_collection_owner(
        self, 
        user_id: str, 
        collection_name: str,
        organization_id: Optional[str] = None
    ) -> bool:
        """
        Check if a user owns a collection
        
        Args:
            user_id: ID of the user
            collection_name: Name of the collection
            organization_id: Optional ID of the organization that owns this collection
            
        Returns:
            bool: True if user owns the collection, False otherwise
        """
        try:
            with db.session_scope() as session:
                # Build query
                query = session.query(Collection).filter_by(
                    user_id=user_id,
                    collection_name=collection_name
                )
                
                # Add organization filter if provided
                if organization_id:
                    query = query.filter_by(organization_id=organization_id)
                
                collection = query.first()
                
                return collection is not None
                
        except Exception as e:
            self.logger.error(f"Error checking collection ownership: {str(e)}")
            return False

    def get_all_collections(
        self, 
        is_admin: bool = False,
        organization_id: Optional[str] = None
    ) -> List[str]:
        """
        Get all collections in the database, optionally filtered by organization.
        Only admin users can get all collections.
        
        Args:
            is_admin: Whether the requesting user is an admin
            organization_id: Optional ID of the organization to filter by
            
        Returns:
            List[str]: List of all collection names
        """
        if not is_admin:
            return []
            
        try:
            with db.session_scope() as session:
                # Build query
                query = session.query(Collection.collection_name)
                
                # Add organization filter if provided
                if organization_id:
                    query = query.filter_by(organization_id=organization_id)
                
                collections = query.all()
                
                # Convert from list of tuples to list of strings
                return [c[0] for c in collections]
                
        except Exception as e:
            self.logger.error(f"Error getting all collections: {str(e)}")
            return []
    
    def get_organization_collections(self, organization_id: str) -> List[str]:
        """
        Get all collections belonging to an organization
        
        Args:
            organization_id: ID of the organization
            
        Returns:
            List[str]: List of collection names
        """
        try:
            with db.session_scope() as session:
                collections = session.query(Collection.collection_name).filter_by(
                    organization_id=organization_id
                ).all()
                
                # Convert from list of tuples to list of strings
                return [c[0] for c in collections]
                
        except Exception as e:
            self.logger.error(f"Error getting organization collections: {str(e)}")
            return []

