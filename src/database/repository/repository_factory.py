from typing import Optional, Dict, Type, Any
from src.utils.config import settings
from src.utils.logger.custom_logging import LoggerMixin

# Import all repository implementations
# from src.database.repository.user_repository import UserRepository
from src.database.repository.user_orm_repository import UserORMRepository

class RepositoryFactory(LoggerMixin):
    """
    Factory pattern để tạo ra các repository instances.
    Cho phép chuyển đổi dễ dàng giữa các cài đặt repository khác nhau.
    """
    
    # Map các tên repository với implementation classes
    _legacy_repositories: Dict[str, Type] = {
        "user": UserORMRepository,
        # Thêm các repository legacy khác
    }
    
    _orm_repositories: Dict[str, Type] = {
        "user": UserORMRepository,
        # Thêm các repository ORM khác khi được chuyển đổi
    }
    
    @classmethod
    def get_repository(cls, repo_name: str, use_orm: Optional[bool] = None) -> Any:
        """
        Trả về một instance của repository.
        
        Args:
            repo_name: Tên repository ('user', 'chat', etc.)
            use_orm: True để dùng ORM, False để dùng legacy, None để dùng giá trị mặc định
            
        Returns:
            Repository instance
        """
        # Xác định có dùng ORM hay không
        if use_orm is None:
            # Đọc từ config, mặc định là False
            use_orm = getattr(settings, "USE_ORM_REPOSITORIES", False)
        
        # Chọn repository map phù hợp
        repo_map = cls._orm_repositories if use_orm else cls._legacy_repositories
        
        # Kiểm tra xem repository có tồn tại không
        if repo_name not in repo_map:
            cls().logger.error(f"Repository {repo_name} not found")
            raise ValueError(f"Repository {repo_name} not found")
        
        # Tạo và trả về instance
        return repo_map[repo_name]()