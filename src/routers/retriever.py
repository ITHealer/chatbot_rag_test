from fastapi import APIRouter, Response, Query, status, Request, Depends
from typing import Annotated, Dict, Any
from src.handlers.retrieval_handler import default_search_retrieval
from src.utils.config import settings
from src.schemas.response import BasicResponse
from src.handlers.api_key_auth_handler import APIKeyAuth

api_key_auth = APIKeyAuth()
router = APIRouter(dependencies=[Depends(api_key_auth.author_with_api_key)])


@router.post("/retriever", response_description="Retriever")
async def retriever(
    request: Request,
    response: Response,
    query: Annotated[str, Query()],
    top_k: Annotated[int, Query()] = 5,
    collection_name: Annotated[str, Query()] = settings.QDRANT_COLLECTION_NAME,
    api_key_data: Dict[str, Any] = Annotated[Dict[str, Any], Depends(api_key_auth.author_with_api_key)]
):
    """
    Retrieve and rerank documents from the vector database.
    Uses singleton instance to avoid reloading models.
    
    Args:
        request: The request object with state info from API key auth
        query: Query string for retrieval
        top_k: Number of top results to return
        collection_name: Name of the collection to search
        
    Returns:
        BasicResponse: Response with retrieved documents
    """
    # Lấy organization_id từ request state
    organization_id = getattr(request.state, "organization_id", None)
    
    # Nếu có organization_id, điều chỉnh tên collection
    effective_collection_name = collection_name
    if organization_id:
        effective_collection_name = f"{collection_name}_{organization_id}"
    
    # Use the singleton instance instead of creating a new one
    resp = await default_search_retrieval.qdrant_retrieval(
        query=query, 
        top_k=top_k, 
        collection_name=effective_collection_name,
        organization_id=organization_id
    )
    
    if resp:
        response.status_code = status.HTTP_200_OK
        data = [docs.json() for docs in resp]
        
        # Lọc metadata organization_id trước khi trả về client
        for item in data:
            if isinstance(item, dict) and "metadata" in item:
                if "organization_id" in item["metadata"]:
                    # Giữ thông tin organization_id để client biết document thuộc về tổ chức nào
                    pass
                    
        return BasicResponse(
            status="Success",
            message="Success retriever data from vector database",
            data=data
        )
    else:
        return BasicResponse(
            status="Failed",
            message="Failed retriever data from vector database",
            data=resp
        )

# from fastapi import APIRouter, Response, Query, status
# from typing import Annotated
# from src.handlers.retrieval_handler import default_search_retrieval
# from src.utils.config import settings
# from src.schemas.response import BasicResponse

# router = APIRouter()

# @router.post("/retriever", response_description="Retriever")
# async def retriever(response: Response,
#                     query: Annotated[str, Query()],
#                     top_k: Annotated[int, Query()] = 5,
#                     collection_name: Annotated[str, Query()] = settings.QDRANT_COLLECTION_NAME
#                 ):
#     """
#     Retrieve and rerank documents from the vector database.
#     Uses singleton instance to avoid reloading models.
    
#     Args:
#         query (str): Query string for retrieval
#         top_k (int): Number of top results to return
#         collection_name (str): Name of the collection to search
        
#     Returns:
#         BasicResponse: Response with retrieved documents
#     """
#     # Use the singleton instance instead of creating a new one
#     resp = await default_search_retrieval.qdrant_retrieval(query, top_k, collection_name)
    
#     if resp:
#         response.status_code = status.HTTP_200_OK
#         data= [docs.json() for docs in resp]
#         return BasicResponse(status="Success",
#                          message="Success retriever data from qdrant",
#                          data=data)
#     else:
#         return BasicResponse(status="Failed",
#                          message="Failed retriever data from qdrant",
#                          data=resp)

# # from fastapi import APIRouter, Response, Query, status, Depends
# # from typing import Annotated
# # from src.handlers.retrieval_handler import SearchRetrieval
# # from src.utils.config import settings
# # from src.schemas.response import BasicResponse

# # router = APIRouter()

# # @router.post("/retriever", response_description="Retriever")
# # async def retriever(response: Response,
# #                     query: Annotated[str, Query()],
# #                     top_k: Annotated[int, Query()] = 5,
# #                     collection_name: Annotated[str, Query()] = settings.QDRANT_COLLECTION_NAME
# #                 ):
    
# #     resp = await SearchRetrieval().qdrant_retrieval(query, top_k, collection_name)
# #     if resp:
# #         response.status_code = status.HTTP_200_OK
# #         data= [docs.json() for docs in resp]
# #         return BasicResponse(status="Success",
# #                          message="Success retriever data from qdrant",
# #                          data=data)
# #     else:
# #         return BasicResponse(status="Failed",
# #                          message="Failed retriever data from qdrant",
# #                          data=resp)