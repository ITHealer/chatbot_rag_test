from fastapi import APIRouter, Response, Query, status, Depends, Body, Request
from typing import Annotated, List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
import uuid
from src.schemas.response import BasicResponse
from src.handlers.rerank_handler import default_reranker
from src.handlers.api_key_auth_handler import APIKeyAuth

router = APIRouter()
api_key_auth = APIKeyAuth()

class Candidate(BaseModel):
    content: str
    doc_id: Optional[str] = None
    organization_id: Optional[str] = None  # Thêm organization_id

    @validator("doc_id", pre=True, always=True)
    def generate_doc_id(cls, value):
        if value is None or value == "":
            return str(uuid.uuid4())
        return value

class RerankRequest(BaseModel):
    candidates: List[Candidate]

@router.post("/rerank", response_description="Rerank")
async def rerank_endpoint(
    request: Request,
    response: Response,
    query: Annotated[str, Query()] = None,
    threshold: Annotated[float, Query()] = 0.3,
    request_body: RerankRequest = Body(...),
    api_key_data: Dict[str, Any] = Depends(api_key_auth.author_with_api_key)
):
    """
    Rerank candidates based on their relevance to the query.
    Uses the singleton reranker instance to avoid reloading models.
    
    Args:
        request: Request object with user authentication info
        query: Query string for reranking
        threshold: Score threshold for filtering results
        request_body: Request body with candidates
        
    Returns:
        BasicResponse: Response with reranked results
    """
    # Lấy organization_id từ request state
    organization_id = getattr(request.state, "organization_id", None)
    
    candidates = request_body.candidates
    
    # Lọc candidates theo organization_id nếu cần
    if organization_id:
        filtered_candidates = []
        for candidate in candidates:
            # Nếu candidate có organization_id, chỉ giữ lại những candidate thuộc tổ chức của người dùng
            if candidate.organization_id is None or candidate.organization_id == organization_id:
                filtered_candidates.append(candidate)
        candidates = filtered_candidates
    
    try:
        # Thêm organization_id vào kết quả rerank
        result = default_reranker.process_candidates(candidates, query, threshold)
        
        # Đảm bảo giữ organization_id trong kết quả
        if organization_id:
            for item in result:
                if "organization_id" not in item:
                    item["organization_id"] = organization_id

        result_response = BasicResponse(
            status="success",
            message="Reranking is successful!",
            data=result
        )
        response.status_code = status.HTTP_200_OK
    except Exception as e:
        # Create a failure response in case of any issues
        result_response = BasicResponse(
            status="fail",
            message=f"Reranking failed: {str(e)}",
            data=[c.dict() for c in candidates]  # Serialize candidates to dict
        )
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    return result_response
