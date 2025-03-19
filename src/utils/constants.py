from enum import Enum

class MessageType(int, Enum):
    QUESTION = 0,
    ANSWER = 1

class ExtendedEnum(Enum):
    @classmethod
    def list(cls):
        return list(map(lambda c: c.value, cls))

class DocumentExtractionBackend(ExtendedEnum):
    Pymupdf = 'pymupdf'
    Docling = 'docling'

class TypeDocument(ExtendedEnum):
    Pdf = 'pdf'
    Word = 'word'
    Pptx = 'pptx'
    Image = 'image'

class LLMModelName(ExtendedEnum):
    DeepSeek_R1_Distill_Qwen_7B= "deepseek-r1:7b"
    # ChatGPT_4 = "gpt-4-turbo"

    Default="deepseek-r1:7b"

# class LocalModelName(ExtendedEnum):
#     Llama3_1_8b_latest= "llama3.1:8b"


# class APIModelName(ExtendedEnum):
#     ChatGPT_4 = "gpt-4-turbo"

class TypeDatabase(ExtendedEnum):
    Qdrant = 'qdrant'


class TypeSearch(ExtendedEnum):
    Key_word = 'key_word'
    Semantic = 'semantic'
    Hybrid = 'hybrid'
    Similarity = 'similarity'
    MMR = "mmr"
    SimilarityWithScore = 'similarity_score_threshold'

SCHEMA_DB = [
    
    {"name": "document_name", "type": "text_general", "indexed": "true", "stored": "true", "multiValued": "false"},
    {"name": "page", "type": "text_general", "indexed": "true", "stored": "true", "multiValued": "false"},
    {"name": "embedding_vector", "type": "knn_vector", "indexed": "true", "stored": "true"},
    {"name": "page_content", "type": "text_general", "indexed": "true", "stored": "true", "multiValued": "false"},
    {"name": "document_id", "type": "text_general", "indexed": "true", "stored": "true", "multiValued": "false"},
    {"name": "is_parent", "type": "boolean", "indexed": "true", "stored": "true", "multiValued": "false"}
]

# SCHEMA_TYPE = [{
#     "name": "knn_vector",
#     "class": "solr.DenseVectorField",
#     "vectorDimension": "384",  # based on embedding_vector dimension
#     "similarityFunction": "cosine"
# }]


DPI = 150

HONGTHAI_LLM = r""" 
 _   _  ___  _   _   ____     ________  _   _     _     _    
| |_| |/ _ \| \ | | / ___|   |__    __|| |_| |   / \   | |         
|     | | | |  \| || |  _|      |  |   |     |  / _ \  | |
|  _  | |_| | |\  |\ |_| |      |  |   |  _  | / ___ \ | |
|_| |_|\___/|_| \_|_\____|      |__|   |_| |_|/_/   \_\|_|

"""