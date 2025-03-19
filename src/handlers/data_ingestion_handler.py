import os
import hashlib
import tempfile
import uuid
from typing import Tuple
from fastapi import UploadFile

from src.utils.config import settings
from src.helpers.qdrant_connection_helper import QdrantConnection
from src.database.data_layer_access.file_management_dal import FileManagementDAL

from src.handlers.file_partition_handler import DocumentExtraction
from src.utils.logger.custom_logging import LoggerMixin

# Temporarily disable FileManagementService
file_management = FileManagementDAL()

class DataIngestion(LoggerMixin):
    def __init__(self) -> None:
        super().__init__()
        
        # Comment out vector database connection
        self.qdrant_client = QdrantConnection()
        self.data_extraction = DocumentExtraction() 
    
    @staticmethod
    def _save_temp_file(file_name: str, file_data: bytes) -> str:
        # Save the uploaded file to a temporary directory -> optimize for I/O
        TEMP_DIR = tempfile.gettempdir()
        temp_file_path = os.path.join(TEMP_DIR, file_name)
        with open(temp_file_path, "wb") as temp_file:
            temp_file.write(file_data)
        return temp_file_path

    async def ingest(self, file: UploadFile, collection_name: str, backend: str) -> dict:
        self.logger.info('event=extract-metadata-from-file message="Ingesting document ..."')
        try:
            # Read file data
            file_data = await file.read()
            file_extension = os.path.splitext(file.filename)[1][1:]
            temp_file_path = self._save_temp_file(file_name=file.filename, file_data=file_data)
            
            # Calculate hash
            sha256 = hashlib.sha256(file_data).hexdigest()
            
            # Generate a UUID instead of using file management service
            document_id = str(uuid.uuid4())
            
            # Print file metadata for debugging
            print(f"File Metadata:")
            print(f"  - Name: {file.filename}")
            print(f"  - Collection: {collection_name}")
            print(f"  - Extension: {file_extension}")
            print(f"  - Size: {len(file_data)} bytes")
            print(f"  - SHA256: {sha256}")
            print(f"  - Document ID: {document_id}")
            
            # Extract text from the file
            resp = await self.data_extraction.extract_text(
                file=file,
                backend=backend,
                temp_file_path=temp_file_path, 
                document_id=document_id
            )
            
            # Comment out adding to vector database
            await self.qdrant_client.add_data(
               documents=resp.data, 
               collection_name=collection_name
            )
            
            print(f"\nChunking Results:")
            print(f"  - Total chunks: {len(resp.data)}")
            for i, chunk in enumerate(resp.data[:3]):  # Print first 3 chunks
                print(f"\nChunk {i+1}:")
                print(f"  - Content length: {len(chunk.page_content)}")
                print(f"  - Metadata: {chunk.metadata}")
                print(f"  - Preview: {chunk.page_content[:100]}...")
            
            # Return results
            data = [docs.json() for docs in resp.data]
            return {"status": "success", "message": "Processed successfully", "data": data}
        
        except Exception as e:
            self.logger.error(f'error={e}')           
            return {"status": "error", "message": f"Processing failed because of {e}"}
        
        finally:
            # Reset file cursor for potential reuse
            await file.seek(0)