from enum import Enum

from pydantic import BaseModel, ConfigDict, UUID4, HttpUrl, Field

from .config import Settings


class ErrorResponse(BaseModel):
    """
    Error response model.

    Attributes:
        status (str): Status of the response ('error').
        message (str): Message indicating the response status.
        exception (str): String representing the exception details.

    """

    status: str = "error"
    message: str
    exception: str | None = None


class ProcStatus(str, Enum):
    """Enum representing the processing status of a document."""

    PENDING = "pending"
    COMPLETE = "complete"
    ERROR = "error"


class DocumentResponse(BaseModel):
    """
    Represents a document response with various attributes.

    Attributes:
        id (UUID4, optional): The unique identifier for the document response.
        file_name (str): The name of the associated file.
        process_status (ProcStatus): The processing status of the document (default: 'pending').
        process_description (str, optional): A description of the document processing (default: None).
        collection_name (str, optional): The name of the collection the document belongs to (default: None).
        model_config (ConfigDict): Configuration dictionary for model settings (generated from attributes).
    """

    id: UUID4 = None
    file_name: str
    process_status: ProcStatus = ProcStatus.PENDING
    process_description: str | None = None
    collection_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class EmbeddingModel(BaseModel):
    """
    Data Transfer Object for representing embeddings of a document.

    Attributes:
        uuid (UUID4): Unique identifier for the embedding.
        collection_id (UUID4): Unique identifier for the collection this embedding belongs to.
        embedding (list[float]): List of floating-point values representing the embedding.
        document (str): The document associated with this embedding.
        cmetadata (dict): Custom metadata associated with the embedding.
        custom_id (UUID4): Custom identifier for the embedding.
    """

    uuid: UUID4
    collection_id: UUID4
    embedding: list[float]
    document: str
    cmetadata: dict
    custom_id: UUID4

    model_config = ConfigDict(from_attributes=True)


class DocumentWithMetadata(BaseModel):
    """
    Represents a document with associated metadata.

    Attributes:
        id (UUID4, optional): Unique identifier for the document (default: None).
        file_name (str): The name of the document file.
        process_status (ProcStatus): The processing status of the document (default: 'pending').
        process_description (str | None, optional): A description of the document processing (default: None).
        collection_name (str | None, optional): The name of the collection this document belongs to (default: None).
        summary (str | None, optional): A summary of the document (default: None).
        embeddings (list[EmbeddingModel], optional): List of embeddings associated with the document (default: []).
    """

    id: UUID4 = None
    file_name: str
    process_status: ProcStatus = ProcStatus.PENDING
    process_description: str | None = None
    collection_name: str | None = None
    summary: str | None = None
    embeddings: list[EmbeddingModel] = []

    model_config = ConfigDict(from_attributes=True)


class SummaryResponse(BaseModel):
    """
    Represents a summary response for a document.

    Attributes:
        document_id (UUID4): Unique identifier for the associated document.
        file_name (str): The name of the document file.
        summary (str): The summary of the document.
    """

    document_id: UUID4
    file_name: str
    summary: str


class CollectionModel(BaseModel):
    """
    Represents a collection of documents with metadata.

    Attributes:
        uuid (UUID4, optional): Unique identifier for the collection (default: None).
        name (str): The name of the collection.
        cmetadata (dict | None, optional): Custom metadata associated with the collection (default: None).
        documents (list[str] | None, optional): List of document names in the collection (default: None).
    """

    uuid: UUID4 = None
    name: str
    cmetadata: dict | None
    documents: list[str] | None = None

    model_config = ConfigDict(from_attributes=True)


class SummaryRequest(BaseModel):
    """
    Represents a request for document summary generation.

    Attributes:
        regenerate (bool, optional): Whether to regenerate the summary (default: False).
        synchronous (bool, optional): Whether to generate the summary synchronously (default: False).
    """

    regenerate: bool = False
    synchronous: bool = False


class Links(BaseModel):
    """
    Represents navigation links for paginated results.

    Attributes:
        current_page (HttpUrl): The URL of the current page.
        first_page (HttpUrl): The URL of the first page.
        prev_page (HttpUrl | None, optional): The URL of the previous page or None if not available.
        next_page (HttpUrl | None, optional): The URL of the next page or None if not available.
        last_page (HttpUrl): The URL of the last page.
    """

    current_page: HttpUrl
    first_page: HttpUrl
    prev_page: HttpUrl | None
    next_page: HttpUrl | None
    last_page: HttpUrl


class Meta(BaseModel):
    """
    Represents metadata information.

    Attributes:
        total_records (int): Total number of records.
        total_pages (int): Total number of pages.
    """

    total_records: int
    total_pages: int


class DocumentListResponse(BaseModel):
    """
    Represents a response containing a list of documents.

    Attributes:
        documents (list[DocumentResponse]): List of DocumentResponse objects.
        links (Links | None, optional): Navigation links or None if not available.
        meta (Meta | None, optional): Metadata information or None if not available.
    """

    documents: list[DocumentResponse]
    links: Links | None
    meta: Meta | None


class CollectionListModel(BaseModel):
    """
    Represents a response containing a list of collections.

    Attributes:
        collections (list[CollectionModel]): List of CollectionModel objects.
        links (Links): Navigation links.
        meta (Meta): Metadata information.
    """

    collections: list[CollectionModel]
    links: Links
    meta: Meta


class LLM(BaseModel):
    """
    Represents configuration options for a Language Model (LLM).

    Attributes:
        model (str): The LLM model to use (default: Settings.get_settings().openai_default_llm_model).
        temperature (float): The temperature parameter (default: 0, range: [0, 2]).
        top_p (float): The top_p parameter (default: 1, range: [0, 1]).
        max_tokens (int): The maximum number of tokens (default: 500, minimum: 0).
        presence_penalty (float): The presence penalty (default: 0, range: [-2, 2]).
        frequency_penalty (float): The frequency penalty (default: 0, range: [-2, 2]).
        logit_bias (dict[str, int] | None): Logit bias dictionary (default: {"50256": -100}).
    """

    model: str = Field(default=Settings.get_settings().openai_default_llm_model)
    temperature: float = Field(default=0, ge=0, le=2)
    top_p: float = Field(default=1, ge=0, le=1)
    max_tokens: int = Field(default=500, ge=0)
    presence_penalty: float = Field(default=0, ge=-2, le=2)
    frequency_penalty: float = Field(default=0, ge=-2, le=2)
    logit_bias: dict[str, int] | None = {"50256": -100}


class Filter(BaseModel):
    """
    Represents filter criteria
    """

    document_name: str


class Usage(BaseModel):
    """
    Represents usage statistics for a language model.

    Attributes:
        prompt_tokens (int): The number of tokens in the prompt.
        completion_tokens (int): The number of tokens in the completion.
        total_tokens (int): The total number of tokens used.
    """

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class Citation(BaseModel):
    """
    Represents a citation within a document.

    Attributes:
        content (str | None, optional): The content of the citation (default: None).
        document (str | None, optional): The document associated with the citation (default: None).
        page (int | None, optional): The page number of the citation (default: None).
        page_offset (int | None, optional): The page offset of the citation (default: None).
    """

    content: str | None = None
    document: str | None = None
    page: int | None = None
    page_offset: int | None = None


class QueryRequest(BaseModel):
    """
    Represents a request for a query on a collection of documents.

    Attributes:
        collection_name (str): The name of the collection to query.
        filter (Filter | None, optional): Filter criteria for the query (default: None).
        query (str): The query string.
        llm (LLM | None, optional): Language Model configuration for the query (default: None).
    """

    collection_name: str
    filter: Filter | None = None
    query: str
    llm: LLM | None = None


class QueryResponse(BaseModel):
    """
    Represents the response to a query.

    Attributes:
        result (str): The query result.
        citations (list[Citation] | None, optional): List of citations (default: None).
        usage (Usage | None, optional): Usage statistics (default: None).
    """

    result: str
    citations: list[Citation] | None = None
    usage: Usage | None = None
