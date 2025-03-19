from langchain_community.chat_models import ChatOllama
from src.utils.logger.custom_logging import LoggerMixin
from src.utils.config import settings

class LLMGenerator(LoggerMixin):
    def __init__(self):
        super().__init__()

    async def get_llm(self, model: str, base_url: str = settings.OLLAMA_ENDPOINT):
        try:
            llm = ChatOllama(base_url=base_url,
                            model=model,
                            temperature=0,
                            top_k=10,
                            top_p=0.5,
                            # num_ctx=8000, 
                            streaming=True)
     
        except Exception as e:
            self.logger.error(f"Error: {str(e)}")
        return llm


