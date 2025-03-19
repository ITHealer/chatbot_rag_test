from src.utils.logger.custom_logging import LoggerMixin
from src.handlers.retrieval_handler import SearchRetrieval
from src.helpers.llm_helper import LLMGenerator
from src.helpers.prompt_template_helper import ContextualizeQuestionHistoryTemplate, QuestionAnswerTemplate
from src.schemas.response import BasicResponse
from src.helpers.chat_management_helper import ChatService

from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from operator import itemgetter
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage

import datetime 
import time
from typing import List, Tuple

# Initialize the chat service
chat_service = ChatService()

class ChatHandler(LoggerMixin):
    def __init__(self) -> None:
        super().__init__()
        self.search_retrieval = SearchRetrieval()
        self.llm_generator = LLMGenerator()
    
    def create_session_id(self, user_id: str) -> BasicResponse:
        """
        Create a new chat session for a user
        
        Args:
            user_id: The ID of the user creating the chat session
            
        Returns:
            BasicResponse: Response with session ID as data
        """
        try:
            session_id = chat_service.create_chat_session(user_id)
            self.logger.info(f"Created new chat session with ID: {session_id}")
            
            return BasicResponse(
                status="Success",
                message="Session created successfully",
                data=session_id
            )
        except Exception as e:
            self.logger.error(f"Failed to create session: {str(e)}")
            return BasicResponse(
                status="Failed",
                message=f"Failed to create session: {str(e)}",
                data=None
            )

    async def _get_chat_flow(self, model_name: str, collection_name: str) -> Tuple[Runnable, Runnable]:
        """
        Create the chat flow for retrieving context and generating responses
        
        Args:
            model_name: The name of the LLM model to use
            collection_name: The name of the vector collection to query
            
        Returns:
            Tuple[Runnable, Runnable]: The conversation chain and rewrite chain
        """
        # Get the language model
        llm = await self.llm_generator.get_llm(model=model_name)
        
        # Chain for rewriting the question based on conversation history
        rewrite_prompt = ContextualizeQuestionHistoryTemplate
        rewrite_chain = (rewrite_prompt | llm | StrOutputParser()).with_config(run_name='rewrite_chain')

        # Define the retrieval function
        async def retriever_function(query):
            return await self.search_retrieval.qdrant_retrieval(query=query, collection_name=collection_name)
        
        # Format documents function
        def format_docs(docs):
            return "\n\n".join(doc.page_content for doc in docs)

        # Main conversation chain that combines the rewritten query, context, and generates a response
        chain = (
            {
                "context": itemgetter("rewrite_input") | RunnableLambda(retriever_function).with_config(run_name='stage_retrieval') | format_docs,
                "input": itemgetter("input")
            }
            | QuestionAnswerTemplate
            | llm
            | StrOutputParser()
        ).with_config(run_name='conversational_rag')

        return chain, rewrite_chain
    
    async def handle_request_chat(
        self,
        session_id: str,
        question_input: str,
        model_name: str,
        collection_name: str
    ) -> BasicResponse:
        """
        Handle a chat request: retrieve context, generate a response
        
        Args:
            session_id: The chat session ID
            question_input: The user's question
            model_name: The LLM model to use
            collection_name: The vector collection to query
            
        Returns:
            BasicResponse: The response to the chat request
        """
        try:
            # Get the chains needed for the chat flow
            conversational_rag_chain, rewrite_chain = await self._get_chat_flow(
                model_name=model_name, 
                collection_name=collection_name
            )

            # Save the user's question to the database
            question_id = chat_service.save_user_question(
                session_id=session_id,
                created_at=datetime.datetime.now(),
                created_by="user",
                content=question_input
            )
            
            # Create a placeholder for the assistant's response
            message_id = chat_service.save_assistant_response(
                session_id=session_id,
                created_at=datetime.datetime.now(),
                question_id=question_id,
                content="",
                response_time=0.0001
            )

            # Start timing the response
            start_time = time.time()
            
            # Get chat history and rewrite the question for better context
            chat_history = ChatMessageHistory.string_message_chat_history(session_id)
            rewrite_input = await rewrite_chain.ainvoke(
                input={"input": question_input, "chat_history": chat_history}
            )
            
            # Generate the response with the context
            resp = await conversational_rag_chain.ainvoke(
                input={"input": question_input, "rewrite_input": rewrite_input},
                config={"configurable": {"session_id": session_id}}
            )
            
            # Calculate the response time
            response_time = round(time.time() - start_time, 3)
            
            # Update the assistant's response in the database
            chat_service.update_assistant_response(
                updated_at=datetime.datetime.now(),
                message_id=message_id,
                content=resp,
                response_time=response_time
            )
            
            self.logger.info(f"Successfully handled chat request in session {session_id}")
            
            return BasicResponse(
                status='Success',
                message="Chat request processed successfully",
                data=resp
            )
            
        except Exception as e:
            self.logger.error(f"Failed to handle chat request: {str(e)}")
            return BasicResponse(
                status='Failed',
                message=f"Failed to handle chat request: {str(e)}",
                data=None
            )

class ChatMessageHistory(LoggerMixin):
    """
    Utility class for working with chat message history
    """
    def __init__(self):
        super().__init__()

    @staticmethod
    def messages_from_items(items: list) -> List[BaseMessage]:
        """
        Convert raw message items to BaseMessage objects
        
        Args:
            items: List of (content, type) tuples
            
        Returns:
            List[BaseMessage]: List of message objects
        """
        def _message_from_item(message: tuple) -> BaseMessage:
            _type = message[1]
            if _type == "human" or _type == "user":
                return HumanMessage(content=message[0])
            elif _type == "ai" or _type == "assistant":
                return AIMessage(content=message[0])
            elif _type == "system":
                return SystemMessage(content=message[0])
            else:
                raise ValueError(f"Got unexpected message type: {_type}")

        messages = [_message_from_item(msg) for msg in items]
        return messages

    @staticmethod
    def concat_message(messages: List[BaseMessage]) -> str:
        """
        Concatenate messages into a single string
        
        Args:
            messages: List of BaseMessage objects
            
        Returns:
            str: Concatenated message history
        """
        concat_chat = ""
        for mes in messages:
            if isinstance(mes, HumanMessage):
                concat_chat += " - user: " + mes.content + "\n"
            else:
                concat_chat += " - assistant: " + mes.content + "\n"
        return concat_chat
    
    @staticmethod
    def string_message_chat_history(session_id: str) -> str:
        """
        Get the chat history as a string
        
        Args:
            session_id: The ID of the chat session
            
        Returns:
            str: The chat history as a string
        """
        items = chat_service.get_chat_history(session_id=session_id, limit=6)
        messages = ChatMessageHistory.messages_from_items(items)
        
        # Reverse the order and skip the current message being processed
        history_str = ChatMessageHistory.concat_message(messages[::-1][:-2])
        return history_str

    def get_list_message_history(self, session_id: str, limit: int) -> BasicResponse:
        """
        Get the list of messages in the chat history
        
        Args:
            session_id: The ID of the chat session
            limit: Maximum number of messages to retrieve
            
        Returns:
            BasicResponse: Response with message history as data
        """
        try:
            items = chat_service.get_chat_history(session_id=session_id, limit=limit)
            # Format the items as "{role} : {content}"
            formatted_items = [f"{item[1]} : {item[0]}" for item in items]
            
            return BasicResponse(
                status="Success",
                message="Retrieved message history successfully",
                data=formatted_items
            )
        except Exception as e:
            self.logger.error(f"Failed to get message history: {str(e)}")
            return BasicResponse(
                status="Failed",
                message=f"Failed to get message history: {str(e)}",
                data=None
            )
                          
    def delete_message_history(self, session_id: str) -> BasicResponse:
        """
        Delete the chat history for a session
        
        Args:
            session_id: The ID of the chat session
            
        Returns:
            BasicResponse: Response indicating success or failure
        """
        try:
            if chat_service.is_session_exist(session_id):
                chat_service.delete_chat_history(session_id=session_id)
                return BasicResponse(
                    status="Success",
                    message="Chat history deleted successfully",
                    data=None
                )
            else:
                return BasicResponse(
                    status="Failed",
                    message="Chat session does not exist",
                    data=None
                )
        except Exception as e:
            self.logger.error(f"Failed to delete message history: {str(e)}")
            return BasicResponse(
                status="Failed",
                message=f"Failed to delete message history: {str(e)}",
                data=None
            )