from fastapi import APIRouter, Response, Query, status, Depends, Request
from typing import Annotated, Dict, Any

from src.handlers.llm_chat_handler import ChatHandler, ChatMessageHistory
from src.handlers.api_key_auth_handler import APIKeyAuth
from src.utils.config import settings

# Sử dụng API key authentication
api_key_auth = APIKeyAuth()
router = APIRouter()

@router.post("/llm_chat", response_description="Chat with LLM system")
async def chat_with_llm(
    request: Request,
    response: Response,
    session_id: Annotated[str, Query()],
    question_input: Annotated[str, Query()],
    model_name: Annotated[str, Query()] = 'llama3.1:8b-instruct-q4_K_M',
    collection_name: Annotated[str, Query()] = settings.QDRANT_COLLECTION_NAME,
    api_key_data: Dict[str, Any] = Depends(api_key_auth.author_with_api_key)
):
    """
    Send a message to the LLM system and get a response
    
    Args:
        request: Request object with user authentication info
        session_id: The ID of the chat session
        question_input: The user's message
        model_name: The LLM model to use (default: llama3.1:8b-instruct-q4_K_M)
        collection_name: The vector store collection to query (default: from settings)
        
    Returns:
        JSON response with the LLM's answer
    """
    # Lấy thông tin user_id và organization_id từ request state
    user_id = getattr(request.state, "user_id", None)
    organization_id = getattr(request.state, "organization_id", None)
    
    # Điều chỉnh tên collection nếu có organization_id
    effective_collection_name = collection_name
    if organization_id:
        effective_collection_name = f"{collection_name}_{organization_id}"
    
    # Xử lý yêu cầu chat với thông tin tổ chức
    resp = await ChatHandler().handle_request_chat(
        session_id=session_id,
        question_input=question_input,
        model_name=model_name,
        collection_name=effective_collection_name,
        user_id=user_id,
        organization_id=organization_id
    )
                                               
    if resp.data:
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return resp

@router.post("/{user_id}/create_session", response_description="Create session")
async def create_session(
    request: Request,
    response: Response,
    user_id: str,
    api_key_data: Dict[str, Any] = Depends(api_key_auth.author_with_api_key)
):
    """
    Create a new chat session for a user
    
    Args:
        request: Request object with user authentication info
        user_id: The ID of the user
        
    Returns:
        JSON response with the session ID
    """
    # Lấy organization_id từ request state
    organization_id = getattr(request.state, "organization_id", None)
    
    # Kiểm tra quyền truy cập
    request_user_id = getattr(request.state, "user_id", None)
    if request_user_id != user_id:
        user_role = getattr(request.state, "role", None)
        if user_role != "ADMIN":
            response.status_code = status.HTTP_403_FORBIDDEN
            return BasicResponse(
                status="Failed",
                message="You can only create sessions for yourself",
                data=None
            )
    
    # Tạo session với thông tin tổ chức
    resp = ChatHandler().create_session_id(
        user_id=user_id,
        organization_id=organization_id
    )
    
    if resp.data:
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return resp

@router.post("/{session_id}/delete_history", response_description="Delete history of session id")
async def delete_chat_history(
    request: Request,
    response: Response,
    session_id: str,
    api_key_data: Dict[str, Any] = Depends(api_key_auth.author_with_api_key)
):
    """
    Delete the chat history for a session
    
    Args:
        request: Request object with user authentication info
        session_id: The ID of the chat session
        
    Returns:
        JSON response indicating success or failure
    """
    # Lấy thông tin user_id và organization_id từ request state
    user_id = getattr(request.state, "user_id", None)
    organization_id = getattr(request.state, "organization_id", None)
    
    # Kiểm tra quyền xóa session
    session_info = ChatMessageHistory().get_session_info(session_id)
    if session_info:
        if session_info.get("user_id") != user_id:
            user_role = getattr(request.state, "role", None)
            if user_role != "ADMIN":
                response.status_code = status.HTTP_403_FORBIDDEN
                return BasicResponse(
                    status="Failed",
                    message="You can only delete your own chat history",
                    data=None
                )
    
    # Xóa lịch sử với kiểm tra tổ chức
    resp = ChatMessageHistory().delete_message_history(
        session_id=session_id,
        user_id=user_id,
        organization_id=organization_id
    )
    
    if resp.status == "Success":
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return resp

@router.post("/{session_id}/get_chat_history", response_description="Chat history of session id")
async def chat_history_by_session_id(
    request: Request,
    response: Response,
    session_id: str,
    limit: int = 10,
    api_key_data: Dict[str, Any] = Depends(api_key_auth.author_with_api_key)
):
    """
    Get the chat history for a session
    
    Args:
        request: Request object with user authentication info
        session_id: The ID of the chat session
        limit: Maximum number of messages to retrieve (default: 10)
        
    Returns:
        JSON response with the chat history
    """
    # Lấy thông tin user_id và organization_id từ request state
    user_id = getattr(request.state, "user_id", None)
    organization_id = getattr(request.state, "organization_id", None)
    
    # Kiểm tra quyền truy cập lịch sử
    session_info = ChatMessageHistory().get_session_info(session_id)
    if session_info:
        if session_info.get("user_id") != user_id and session_info.get("organization_id") != organization_id:
            user_role = getattr(request.state, "role", None)
            if user_role != "ADMIN":
                response.status_code = status.HTTP_403_FORBIDDEN
                return BasicResponse(
                    status="Failed",
                    message="You can only view your own chat history",
                    data=None
                )
    
    # Lấy lịch sử với kiểm tra tổ chức
    resp = ChatMessageHistory().get_list_message_history(
        session_id=session_id,
        limit=limit,
        user_id=user_id,
        organization_id=organization_id
    )
    
    if resp.data:
        response.status_code = status.HTTP_200_OK
    else:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    return resp


# from fastapi import APIRouter, Response, Query, status, Depends
# from typing import Annotated

# from src.handlers.llm_chat_handler import ChatHandler, ChatMessageHistory
# from src.handlers.auth_handler import Authentication
# from src.utils.config import settings

# # Initialize authentication handler
# auth = Authentication()
# router = APIRouter(dependencies=[Depends(auth.get_current_user)])

# @router.post("/llm_chat", response_description="Chat with LLM system")
# async def chat_with_llm(
#     response: Response,
#     session_id: Annotated[str, Query()],
#     question_input: Annotated[str, Query()],
#     model_name: Annotated[str, Query()] = 'llama3.1:8b-instruct-q4_K_M',
#     collection_name: Annotated[str, Query()] = settings.QDRANT_COLLECTION_NAME,
# ):
#     """
#     Send a message to the LLM system and get a response
    
#     Args:
#         session_id: The ID of the chat session
#         question_input: The user's message
#         model_name: The LLM model to use (default: llama3.1:8b-instruct-q4_K_M)
#         collection_name: The vector store collection to query (default: from settings)
        
#     Returns:
#         JSON response with the LLM's answer
#     """
#     resp = await ChatHandler().handle_request_chat(
#         session_id=session_id,
#         question_input=question_input,
#         model_name=model_name,
#         collection_name=collection_name
#     )
                                               
#     if resp.data:
#         response.status_code = status.HTTP_200_OK
#     else:
#         response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
#     return resp

# @router.post("/{user_id}/create_session", response_description="Create session")
# async def create_session(
#     response: Response,
#     user_id: str
# ):
#     """
#     Create a new chat session for a user
    
#     Args:
#         user_id: The ID of the user
        
#     Returns:
#         JSON response with the session ID
#     """
#     resp = ChatHandler().create_session_id(user_id)
#     if resp.data:
#         response.status_code = status.HTTP_200_OK
#     else:
#         response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
#     return resp

# @router.post("/{session_id}/delete_history", response_description="Delete history of session id")
# async def delete_chat_history(
#     response: Response,
#     session_id: str
# ):
#     """
#     Delete the chat history for a session
    
#     Args:
#         session_id: The ID of the chat session
        
#     Returns:
#         JSON response indicating success or failure
#     """
#     resp = ChatMessageHistory().delete_message_history(session_id=session_id)
#     if resp.status == "Success":
#         response.status_code = status.HTTP_200_OK
#     else:
#         response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
#     return resp

# @router.post("/{session_id}/get_chat_history", response_description="Chat history of session id")
# async def chat_history_by_session_id(
#     response: Response,
#     session_id: str,
#     limit: int = 10
# ):
#     """
#     Get the chat history for a session
    
#     Args:
#         session_id: The ID of the chat session
#         limit: Maximum number of messages to retrieve (default: 10)
        
#     Returns:
#         JSON response with the chat history
#     """
#     resp = ChatMessageHistory().get_list_message_history(session_id=session_id, limit=limit)
#     if resp.data:
#         response.status_code = status.HTTP_200_OK
#     else:
#         response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
#     return resp