from typing import Annotated
from jose import JWTError, jwt
from typing import Optional, Dict
from datetime import datetime, timedelta
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status, Request

from src.utils.config import settings
from src.utils.config_loader import ConfigReaderInstance
from src.database.repository.repository_factory import RepositoryFactory
from src.schemas.auth import User, UserCreate, UserInDB, TokenData

# Read configuration from YAML file
file_config = ConfigReaderInstance.yaml.read_config_from_file(settings.AUTH_CONFIG_FILENAME)

# Get config
auth_config = file_config.get('AUTH', {})

# Get access token to calculate expire time
ACCESS_TOKEN_EXPIRE_MINUTES = timedelta(minutes=auth_config.get("ACCESS_TOKEN_EXPIRE_MINUTES"))

# Init object management Users - sử dụng factory pattern
user_repo = RepositoryFactory.get_repository("user")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/token")
token_dependencies = [Depends(oauth2_scheme)]


class Authentication:
    @staticmethod
    async def get_current_user(
        request: Request,
        token: Annotated[str, Depends(oauth2_scheme)]) -> User:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, auth_config.get("SECRET_KEY"), algorithms=[auth_config.get("ALGORITHM")])
            username: str = payload.get("sub")
            if username is None:
                raise credentials_exception
            token_data = TokenData(username=username)
        except JWTError:
            raise credentials_exception
        user = Authentication.get_user(user_repo.get_all(), username=token_data.username)
        request.state.username = user.username
        if user is None:
            raise credentials_exception
        return user

    @staticmethod
    async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        user = await current_user
        if user.enabled == 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        return user
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def get_user(db: Dict[str, dict], username: str) -> Optional[User]:
        if username in db:
            user_dict = db[username]
            return UserInDB(**user_dict)

    @staticmethod
    def authenticate_user(username: str, password: str) -> Optional[User | bool]:
        user = Authentication.get_user(user_repo.get_all(), username)
        if not user:
            return False
        if not Authentication.verify_password(password, user.password):
            return False
        return user

    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = ACCESS_TOKEN_EXPIRE_MINUTES) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now() + expires_delta
        else:
            expire = datetime.now() + timedelta(minutes=15)
        to_encode.update({"expired_time": expire.isoformat()})
        encoded_jwt = jwt.encode(to_encode, auth_config.get("SECRET_KEY"), algorithm=auth_config.get("ALGORITHM"))
        return encoded_jwt

    @staticmethod
    def register_user(user: UserCreate) -> User:
        existing_user = user_repo.is_exist_user(user.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already registered")

        encrypted_password = Authentication.get_password_hash(user.password)
        new_user = user.model_copy()
        new_user.password = encrypted_password
        username = user_repo.create_user(**new_user.__dict__)
        return User(**user_repo.get_user_by_username(username))
    
    @staticmethod
    def is_admin(username: str) -> bool:
        role = user_repo.get_user_role(username)
        return role == 'ADMIN'

    @staticmethod
    def change_password(active_user, username, old_password, new_password) -> bool:
        if username != active_user.username:
            raise HTTPException(status_code=400, detail="Wrong username")
        if Authentication.authenticate_user(username, old_password):
            hashed_password = Authentication.get_password_hash(new_password)
            user_repo.change_password(username, hashed_password)
            return True
        else:
            raise HTTPException(status_code=400, detail="Wrong password")
