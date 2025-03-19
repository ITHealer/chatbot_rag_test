class LoggerInstance(object):
    def __new__(cls):
        from src.utils.logger.custom_logging import LogHandler
        return LogHandler()

class IncludeAPIRouter(object):
    def __new__(cls):
        from fastapi.routing import APIRouter
        from src.routers.health_check import router as router_health_check
        from src.routers.security import router as router_security
        from src.routers.vectorstore import router as router_collection_management
        from src.routers.documents import router as router_document_management
        from src.routers.retriever import router as router_retriever
        from src.routers.rerank import router as router_rerank
        from src.routers.llm_chat import router as router_chatllm
        
        router = APIRouter(prefix='/api/v1')
        router.include_router(router_health_check, tags=['Health Check'])
        router.include_router(router_security, tags=['Security'])
        router.include_router(router_collection_management, tags=['Collection Management'])
        router.include_router(router_document_management, tags=['Document Management'])
        router.include_router(router_retriever, tags=['Retriever'])
        router.include_router(router_rerank, tags=['Reranking'])
        router.include_router(router_chatllm, tags=['Chat with LLM'])
        
        return router

# Instance creation
logger_instance = LoggerInstance()