from typing import TypeVar, Generic, Type, List, Optional, Dict, Any, Union
from sqlalchemy.orm import Session
from pydantic import BaseModel
from uuid import UUID

from src.database.db_connection import db
from src.utils.logger.custom_logging import LoggerMixin

# Generic type for database models
T = TypeVar('T')
# Generic type for schemas
S = TypeVar('S')

class BaseORMRepository(Generic[T, S], LoggerMixin):
    """
    Base repository pattern for SQLAlchemy ORM.
    
    Generic parameters:
    - T: The SQLAlchemy model
    - S: The Pydantic schema for data validation
    """
    
    def __init__(self, model: Type[T]):
        super().__init__()
        self.model = model
    
    def get_by_id(self, id: Union[str, UUID]) -> Optional[T]:
        """Get an entity by ID"""
        with db.session_scope() as session:
            return session.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self) -> List[T]:
        """Get all entities"""
        with db.session_scope() as session:
            return session.query(self.model).all()
    
    def find_by(self, **kwargs) -> List[T]:
        """Find entities by attribute values"""
        with db.session_scope() as session:
            query = session.query(self.model)
            for key, value in kwargs.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)
            return query.all()
            
    def find_one_by(self, **kwargs) -> Optional[T]:
        """Find one entity by attribute values"""
        with db.session_scope() as session:
            query = session.query(self.model)
            for key, value in kwargs.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)
            return query.first()
    
    def create(self, obj_in: Union[S, Dict[str, Any]]) -> T:
        """Create a new entity"""
        # Convert to dict if it's a Pydantic model
        obj_data = obj_in if isinstance(obj_in, dict) else obj_in.dict(exclude_unset=True)
        
        # Create model instance
        db_obj = self.model(**obj_data)
        
        with db.session_scope() as session:
            session.add(db_obj)
            session.commit()
            session.refresh(db_obj)
            return db_obj
    
    def update(self, id: Union[str, UUID], obj_in: Union[S, Dict[str, Any]]) -> Optional[T]:
        """Update an existing entity"""
        with db.session_scope() as session:
            db_obj = session.query(self.model).filter(self.model.id == id).first()
            if db_obj is None:
                return None
                
            # Convert to dict if it's a Pydantic model
            update_data = obj_in if isinstance(obj_in, dict) else obj_in.dict(exclude_unset=True)
            
            # Update model attributes
            for field in update_data:
                if hasattr(db_obj, field):
                    setattr(db_obj, field, update_data[field])
            
            session.add(db_obj)
            session.commit()
            session.refresh(db_obj)
            return db_obj
    
    def delete(self, id: Union[str, UUID]) -> bool:
        """Delete an entity by ID"""
        with db.session_scope() as session:
            db_obj = session.query(self.model).filter(self.model.id == id).first()
            if db_obj is None:
                return False
            
            session.delete(db_obj)
            session.commit()
            return True
    
    def exists(self, **kwargs) -> bool:
        """Check if entity exists with given attributes"""
        with db.session_scope() as session:
            query = session.query(self.model)
            for key, value in kwargs.items():
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)
            return session.query(query.exists()).scalar()