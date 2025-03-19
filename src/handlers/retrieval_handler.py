from typing import List, Optional
import numpy as np
from src.utils.config import settings
from langchain_core.documents import Document
from src.helpers.qdrant_connection_helper import QdrantConnection
from src.utils.logger.custom_logging import LoggerMixin
from src.helpers.model_loader_helper import ModelLoader, flag_reranker

class SearchRetrieval(LoggerMixin):
    """
    Handler for retrieving and reranking documents from the vector database.
    Uses singleton pattern to ensure models are loaded only once.
    """
    
    def __init__(self, model_key: Optional[str] = None):
        """
        Initialize the search retrieval handler.
        
        Args:
            model_key (Optional[str]): Key of reranking model in config.
                                      If None, uses the default model.
        """
        super().__init__()
        self.qdrant_client = QdrantConnection()
        
        if model_key is None:
            # Use singleton instance for better performance
            self.reranker = flag_reranker
            self.model_name = "default"  # Just for logging
        else:
            # Load specific model if requested
            self.reranker = ModelLoader.get_flag_reranker(model_key)
            self.model_name = model_key
            
        self.logger.info(f"Using FlagReranker model: {self.model_name}")
    
    def _query_retrieval_reranking(self, candidates: List[Document], query: str, threshold=0.06) -> List[Document]:
        """
        Rerank the candidate documents based on their relevance to the query.
        
        Args:
            candidates (List[Document]): List of retrieved documents
            query (str): Query string
            threshold (float): Minimum score threshold
            
        Returns:
            List[Document]: Reranked and filtered documents
        """
        if candidates:
            query_docs_pair = []
            for candidate in candidates:
                query_docs_pair.append([query, candidate.page_content.strip()])

            scores = self.reranker.compute_score(query_docs_pair, normalize=True)
            if len(query_docs_pair) == 1:
                scores = np.array([scores])
            else:
                scores = np.array(scores)
            
            # Sorted scores and indices
            sorted_indices = sorted(range(len(scores)), key=lambda x: scores[x], reverse=True)
            sorted_scores = [scores[i] for i in sorted_indices]
            
            filtered_indices = [index for index, score in zip(sorted_indices, sorted_scores) if score >= threshold]
            rerank_content = [query_docs_pair[index][1] for index in filtered_indices]
            
            content_to_results_map = {candidate.page_content.strip(): candidate for candidate in candidates}
            
            final_results = [content_to_results_map[content] for content in rerank_content if content in content_to_results_map]
            
            return final_results
        
        return candidates


    async def qdrant_retrieval(
            self, 
            query: str | dict,
            top_k: int = 5,
            collection_name: str = settings.QDRANT_COLLECTION_NAME
        ) -> Optional[List[Document]]:
        """
        Retrieve documents from Qdrant, rerank them, and return the top results.
        
        Args:
            query (str | dict): Query string or dict with query field
            top_k (int): Number of top results to return
            collection_name (str): Name of the collection to search
            
        Returns:
            Optional[List[Document]]: Retrieved and reranked documents
        """
        if type(query) == dict:
            query = query.get('query')

        try:
            docs = await self.qdrant_client.hybrid_search(query=query, collection_name=collection_name) 
            docs = self._query_retrieval_reranking(docs, query, 0.3)
            extended_docs = await self.qdrant_client.query_headers(docs, collection_name)
            self.logger.debug("############### docs ########### %s", docs)
            self.logger.debug("############### extended_docs ########### %s", extended_docs)
            return extended_docs[:top_k] 
        except Exception as e:
            self.logger.error('event=query-relevant-context-in-database '
                             'message="Failed to retrieve relevant context from database"'
                             f'error={e}')
            return []

# Create a singleton instance for default usage
default_search_retrieval = SearchRetrieval()
