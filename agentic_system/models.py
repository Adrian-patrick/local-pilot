from typing import List, Optional
from pydantic import BaseModel, Field

class FileMetadata(BaseModel):
    file_name: str = Field(description="Name of the file with extension")
    full_path: str = Field(description="Absolute system file path")
    extension: str = Field(description="Uppercase file extension")
    file_size: int = Field(description="File size in bytes")
    last_modified: str = Field(description="ISO formatted last modification date")
    is_readable: bool = Field(description="True if the file can be opened and read")

class RetrievalChunk(BaseModel):
    chunk_id: int = Field(description="Unique ID of the semantic chunk")
    content: str = Field(description="Text segment extracted from the file")
    score: float = Field(description="Mock semantic similarity retrieval score")

class AgentResponse(BaseModel):
    synthesis_summary: str = Field(description="Executive contextual summary synthesized by the LLM agent")
    key_highlights: List[str] = Field(description="Key highlight points extracted from the retrieved text context")
    action_items: List[str] = Field(description="Recommended action items or tasks related to this file context")
    confidence_score: float = Field(description="Agent confidence level on context understanding (0.0 to 1.0)")

class SharedState(BaseModel):
    """
    Shared Memory Context carried across all 7 layers of the Pydantic Graph.
    """
    # 1. User Action
    target_file_path: str = ""
    
    # 2. OS Context Layer
    os_platform: str = ""
    shell_environment: str = ""
    
    # 3. Context Builder
    neighbor_files: List[str] = Field(default_factory=list)
    parent_directory: str = ""
    
    # 4. File Processing Pipeline
    metadata: Optional[FileMetadata] = None
    raw_content_preview: str = ""
    
    # 5. Retrieval Layer
    retrieved_chunks: List[RetrievalChunk] = Field(default_factory=list)
    
    # 6. LLM Agent & 7. Response Generator
    agent_response: Optional[AgentResponse] = None

class PipelineCompleted(BaseModel):
    """
    Final wrapper returned when the local pilot graph execution terminates.
    """
    status: str = Field(default="success", description="Overall execution status of the pipeline")
    message: str = Field(default="Pipeline completed successfully.", description="Detailed termination message")
    response: Optional[AgentResponse] = Field(default=None, description="The final synthesized response from the LLM agent")

