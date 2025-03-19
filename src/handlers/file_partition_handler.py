import uuid
from fastapi import UploadFile
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat, FormatToExtensions
from docling.document_converter import DocumentConverter, PdfFormatOption
# from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from langchain_core.documents import Document
import pymupdf, pymupdf4llm

# from handlers.ocr_client.ocr_pipeline import OCRPipeline

from src.schemas.response import BasicResponse
from src.utils.logger.custom_logging import LoggerMixin

# Initialize OCR pipeline
# ocr_pipeline = OCRPipeline()

# Configure PDF processing options
pipeline_options = PdfPipelineOptions()
pipeline_options.do_ocr = True  # Enable OCR for text in images
pipeline_options.do_table_structure = True
pipeline_options.table_structure_options.do_cell_matching = True
pipeline_options.ocr_options.lang = ["es"]
# pipeline_options.accelerator_options = AcceleratorOptions(
#     num_threads=4, device=AcceleratorDevice.AUTO
# )

# Get supported file formats from docling
SUPPORTED_FORMATS = [item for sublist in FormatToExtensions.values() for item in sublist]


class DocumentExtraction(LoggerMixin):
    def __init__(self) -> None:
        super().__init__()

    async def extract_text(self,
                    backend: str,
                    file: UploadFile, 
                    temp_file_path: str, 
                    document_id: uuid):
        
        valid= self.validate_file_extension(file)
        
        if valid == "pdf" and backend == "pymupdf":
            markdown_text= await self.pymupdf_extract(temp_file_path)
        else: 
            markdown_text= await self.docling_extract(temp_file_path)
        
        if len(markdown_text) < 4000:
            doc = Document(page_content=markdown_text)
            doc.metadata = {
                'document_name': file.filename,
                'index': 1,
                'headers': file.filename,
                'document_id': document_id
            }
            documents = [doc]
        else:
            headers_to_split_on = [
                    ("#", "Header 1"),
                    ("##", "Header 2"),
                    ("###", "Header 3"),
                    ("####", "Header 4"),
                    ("#####", "Header 5"),
                ]

            md_splitter = MarkdownHeaderTextSplitter(
                    headers_to_split_on=headers_to_split_on, strip_headers=False
                )
            md_splits = md_splitter.split_text(markdown_text)

            chunk_size = 300
            chunk_overlap = 0
                
            text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=chunk_size, chunk_overlap=chunk_overlap
                )
            documents = text_splitter.split_documents(md_splits)

            for idx, document in enumerate(documents):
                headers = document.metadata.copy()
                headers_string = ', '.join([f"{key}: {value}" for key, value in headers.items()])

                document.metadata = {
                        'document_name': file.filename,
                        'index': idx,
                        'headers': headers_string,
                        'document_id': document_id
                    }
            
        if len(documents) > 0:
            response = BasicResponse(status='success',
                                         message='Extract text from file successfully.',
                                         data=documents)
        else:
            response = BasicResponse(status='Failed',
                                    message='Extract text from file was failed.',
                                    data=None)
        return response
    
    async def pymupdf_extract(self, temp_file_path: str):
        doc = pymupdf.open(temp_file_path)
        header_identifier = pymupdf4llm.IdentifyHeaders(doc, body_limit=6)
        markdown_text = pymupdf4llm.to_markdown(
                doc, 
                hdr_info=header_identifier.get_header_id, 
            )
        return markdown_text
    
    
    async def docling_extract(self, temp_file_path: str):
        
        doc_converter = (DocumentConverter(allowed_formats=[
                        InputFormat.PDF,
                        InputFormat.IMAGE,
                        InputFormat.DOCX,
                        InputFormat.HTML,
                        InputFormat.PPTX,
                        InputFormat.ASCIIDOC,
                        InputFormat.MD,
                    ], 
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options, 
                        # backend=PyPdfiumDocumentBackend 
                    ),
                },
            )
        )
        result = doc_converter.convert(temp_file_path)
        markdown_text= result.document.export_to_markdown()
        return markdown_text 
    
    # Extract text from image if input is image
    # async def extract_image(self, temp_file_path: str):
    #     self.logger.info(f"Extracting text from image {temp_file_path}")
    #     results = ocr_pipeline.execute(temp_file_path)
    #     return results
    
    def validate_file_extension(self, file: UploadFile):
        extension = file.filename.split(".")[-1].lower()
        if extension in SUPPORTED_FORMATS:
            if extension in FormatToExtensions["pdf"]:
                return "pdf"
            elif extension in FormatToExtensions["image"]:
                return "image"
            else:
                return "other"
        return "unsupported"    