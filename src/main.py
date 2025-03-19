import os
import logging
import uvicorn
import secrets
from typing import Any
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from src.utils.config import settings
from src.utils.constants import HONGTHAI_LLM
from src.app import IncludeAPIRouter, logger_instance
from src.utils.config_loader import ConfigReaderInstance


logger = logger_instance.get_logger(__name__)

# Read configuration from YAML file
api_config = ConfigReaderInstance.yaml.read_config_from_file(settings.API_CONFIG_FILENAME)
logging_config = ConfigReaderInstance.yaml.read_config_from_file(settings.LOG_CONFIG_FILENAME)

# Generate a security key (used to encrypt the session).
secret_key = secrets.token_urlsafe(32)

# lifespan (app lifecycle management, default is None).
def get_application(lifespan: Any = None):
    _app = FastAPI(lifespan=lifespan,
                   title=api_config.get('API_NAME'),
                   description=api_config.get('API_DESCRIPTION'),
                   version=api_config.get('API_VERSION'),
                   debug=api_config.get('API_DEBUG_MODE')
                   )
    
    _app.include_router(IncludeAPIRouter())

    _app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    _app.add_middleware(SessionMiddleware, secret_key=secret_key)

    return _app

# Manage the lifecycle of asynchronous applications.
# Perform actions when the application starts and shuts down
@asynccontextmanager
async def app_lifespan(app: FastAPI):
    logger.info(HONGTHAI_LLM)
    logger.info(f'event=app-startup')
    yield
    # Code to execute when app is shutting down
    logger.info(f'event=app-shutdown message="All connections are closed."')


# Create FastAPI application object
app = get_application(lifespan=app_lifespan)

@app.get('/')
async def docs_redirect():
    return RedirectResponse(url='/docs')

# Filter logs for endpoint /health
class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find('/health') == -1


if __name__ == '__main__':
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config['formatters']['access']['fmt'] = logging_config.get('UVICORN_FORMATTER')
    log_config['formatters']['default']['fmt'] = logging_config.get('UVICORN_FORMATTER')
    log_config['formatters']['access']['datefmt'] = logging_config.get('DATE_FORMATTER')
    log_config['formatters']['default']['datefmt'] = logging_config.get('DATE_FORMATTER')
    
    uvicorn.run('src.main:app',
                host=settings.HOST,
                port=settings.PORT,
                log_level=settings.LOG_LEVEL.lower(),
                log_config=log_config,
                workers=settings.UVICORN_WORKERS
               )
