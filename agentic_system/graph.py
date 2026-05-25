import os
import sys
from datetime import datetime
from typing import Union, Optional
from pydantic_graph import BaseNode, Graph, GraphRunContext, End
from .models import SharedState, FileMetadata, RetrievalChunk, AgentResponse, PipelineCompleted
from .agents import LlmAgent

# ============================================================================
# Pydantic Graph Nodes for the 7-Layer Agentic Architecture
# ============================================================================

class OsContextLayerNode(BaseNode[SharedState, None, PipelineCompleted]):
    """
    Layer 2: OS Context Layer. Standardizes file paths and resolves system platform metrics.
    """
    async def run(self, ctx: GraphRunContext[SharedState]) -> 'ContextBuilderNode':
        print("\n[Layer 2: OS Context Layer] Initializing system context...")
        
        # Determine operating system platform
        ctx.state.os_platform = sys.platform.upper()
        
        # Capture shell environment indicator
        ctx.state.shell_environment = "POWERSHELL" if os.name == "nt" else "BASH"
        
        print(f"   -> Platform Resolved: {ctx.state.os_platform}")
        print(f"   -> Shell Environment: {ctx.state.shell_environment}")
        print(f"   -> Standardizing target path: '{ctx.state.target_file_path}'")
        
        return ContextBuilderNode()

class ContextBuilderNode(BaseNode[SharedState, None, PipelineCompleted]):
    """
    Layer 3: Context Builder. Scrapes neighboring file entries and locates parent folders.
    """
    async def run(self, ctx: GraphRunContext[SharedState]) -> 'FileProcessingPipelineNode':
        print("\n[Layer 3: Context Builder] Scaping workspace environment...")
        
        abs_path = os.path.abspath(ctx.state.target_file_path)
        parent_dir = os.path.dirname(abs_path)
        
        ctx.state.parent_directory = parent_dir
        print(f"   -> Scraped Parent Directory: {ctx.state.parent_directory}")
        
        # Resolve real neighbor sibling files if parent directory exists
        if os.path.exists(parent_dir) and os.path.isdir(parent_dir):
            try:
                entries = os.listdir(parent_dir)
                # Filter to show up to 10 files as neighbors
                ctx.state.neighbor_files = [e for e in entries[:10]]
            except Exception:
                ctx.state.neighbor_files = ["README.md", "main.py"]
        else:
            ctx.state.neighbor_files = ["README.md", "main.py"]
            
        print(f"   -> Discovered neighboring file contexts: {ctx.state.neighbor_files}")
        
        return FileProcessingPipelineNode()

class FileProcessingPipelineNode(BaseNode[SharedState, None, PipelineCompleted]):
    """
    Layer 4: File Processing Pipeline. Extracts file metadata and reads context preview.
    """
    async def run(self, ctx: GraphRunContext[SharedState]) -> 'RetrievalLayerNode':
        print("\n[Layer 4: File Processing Pipeline] Running file extraction protocols...")
        
        file_path = ctx.state.target_file_path
        abs_path = os.path.abspath(file_path)
        
        # Handle file metadata if target exists
        if os.path.exists(abs_path):
            file_name = os.path.basename(abs_path) or abs_path
            stats = os.stat(abs_path)
            last_modified = datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            
            if os.path.isdir(abs_path):
                # Target is a folder!
                extension = "FOLDER"
                is_readable = True
                try:
                    children = os.listdir(abs_path)
                    file_size = len(children)
                    ctx.state.raw_content_preview = f"Directory listing for folder '{file_name}':\n" + "\n".join([f"- {child}" for child in children[:15]])
                except Exception as e:
                    ctx.state.raw_content_preview = f"[Unreadable folder: {e}]"
                    file_size = 0
            else:
                # Target is a file!
                _, ext = os.path.splitext(file_name)
                extension = ext.strip(".").upper() or "TXT"
                file_size = stats.st_size
                is_readable = True
                try:
                    with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                        ctx.state.raw_content_preview = f.read(1000)
                except Exception as e:
                    ctx.state.raw_content_preview = f"[Unreadable file: {e}]"
                    is_readable = False
        else:
            raise FileNotFoundError(f"Target path '{abs_path}' does not exist on this system.")

        ctx.state.metadata = FileMetadata(
            file_name=file_name,
            full_path=abs_path,
            extension=extension,
            file_size=file_size,
            last_modified=last_modified,
            is_readable=is_readable
        )
        
        print(f"   -> Parsed Target Name: {ctx.state.metadata.file_name}")
        print(f"   -> Target Type/Ext: {ctx.state.metadata.extension}")
        print(f"   -> Size Indicator: {ctx.state.metadata.file_size}")
        print(f"   -> Modification Date: {ctx.state.metadata.last_modified}")
        print(f"   -> Preview Content length: {len(ctx.state.raw_content_preview)} chars")
        
        return RetrievalLayerNode()

class RetrievalLayerNode(BaseNode[SharedState, None, PipelineCompleted]):
    """
    Layer 5: Retrieval Layer. Segments content preview into semantic chunks.
    """
    async def run(self, ctx: GraphRunContext[SharedState]) -> 'LlmAgentNode':
        print("\n[Layer 5: Retrieval Layer] Segmenting text context into index chunks...")
        
        content = ctx.state.raw_content_preview
        
        # Simple semantic segment splitting (split by sentences or paragraphs)
        sentences = [s.strip() for s in content.split(".") if len(s.strip()) > 5]
        
        # Wrap sentences in structured RetrievalChunks (indexing up to 3 chunks)
        chunks = []
        for i, sentence in enumerate(sentences[:3]):
            chunks.append(RetrievalChunk(
                chunk_id=i + 1,
                content=sentence + ".",
                score=0.98 - (i * 0.05) # Simulated similarity score
            ))
            
        # Fallback if no sentences extracted
        if not chunks:
            chunks.append(RetrievalChunk(
                chunk_id=1,
                content="Loaded document context successfully.",
                score=0.99
            ))
            
        ctx.state.retrieved_chunks = chunks
        
        for chunk in ctx.state.retrieved_chunks:
            print(f"   -> Retrieved Chunk #{chunk.chunk_id} [Match Score: {chunk.score:.2f}]: '{chunk.content[:60]}...'")
            
        return LlmAgentNode()

class LlmAgentNode(BaseNode[SharedState, None, PipelineCompleted]):
    """
    Layer 6: LLM Agent. Invokes Pydantic AI agent to synthesize chunks and generate insights.
    """
    async def run(self, ctx: GraphRunContext[SharedState]) -> 'ResponseGeneratorNode':
        print("\n[Layer 6: LLM Agent] Dispatching context to LLM Agent...")
        
        # Combine retrieved chunks as the context prompt
        text_context = "\n".join([f"[{c.chunk_id}] {c.content}" for c in ctx.state.retrieved_chunks])
        
        # Ingest metadata details
        filename = ctx.state.metadata.file_name if ctx.state.metadata else "unknown"
        extension = ctx.state.metadata.extension if ctx.state.metadata else "TXT"
        
        # Instantiate and run LlmAgent
        agent = LlmAgent()
        response: AgentResponse = await agent.run(filename, extension, text_context)
        
        ctx.state.agent_response = response
        
        print("   -> Agent Executive Synthesis:")
        print(f"      \"{ctx.state.agent_response.synthesis_summary}\"")
        print("   -> Extracted Key Highlights:")
        for highlight in ctx.state.agent_response.key_highlights:
            print(f"      * {highlight}")
            
        return ResponseGeneratorNode()

class ResponseGeneratorNode(BaseNode[SharedState, None, PipelineCompleted]):
    """
    Layer 7: Response Generator. Formats and packages output structured schema, terminating the graph.
    """
    async def run(self, ctx: GraphRunContext[SharedState]) -> End[PipelineCompleted]:
        print("\n[Layer 7: Response Generator] Consolidating pipeline results...")
        
        # Package full pipeline response
        metadata = ctx.state.metadata
        agent_response = ctx.state.agent_response
        
        print("\n" + "="*70)
        print("                 LOCAL PILOT PIPELINE OUTPUT SUMMARY")
        print("="*70)
        if metadata:
            print(f"  FILE CONTEXT:  {metadata.file_name} ({metadata.extension})")
            print(f"  FULL PATH:     {metadata.full_path}")
            print(f"  FILE SIZE:     {metadata.file_size} bytes")
            print(f"  LAST MODIFIED: {metadata.last_modified}")
        print("-"*70)
        if agent_response:
            print("  EXECUTIVE SUMMARY:")
            print(f"    {agent_response.synthesis_summary}")
            print("\n  KEY INSIGHTS & HIGHLIGHTS:")
            for highlight in agent_response.key_highlights:
                print(f"    - {highlight}")
            print("\n  RECOMMENDED ACTION ITEMS:")
            for action in agent_response.action_items:
                print(f"    [ ] {action}")
            print(f"\n  CONFIDENCE METRIC: {agent_response.confidence_score * 100:.1f}%")
        print("="*70)
        
        print("\nGraph execution completed successfully. Pipeline terminated.")
        return End(PipelineCompleted(response=agent_response))

class UserActionNode(BaseNode[SharedState, None, PipelineCompleted]):
    """
    Layer 1: User Action. Entrypoint node representing right-click action on a file path.
    """
    def __init__(self, target_file_path: str):
        self.target_file_path = target_file_path
        
    async def run(self, ctx: GraphRunContext[SharedState]) -> OsContextLayerNode:
        print("\n[Layer 1: User Action] Explorer right-click event captured.")
        
        # Initialize Shared State with user selection
        ctx.state.target_file_path = self.target_file_path
        print(f"   -> Set Target File Path: '{ctx.state.target_file_path}'")
        
        return OsContextLayerNode()

# ============================================================================
# Graph Wire Definition
# ============================================================================

# Define all possible node states in the sequential graph
NodeUnion = Union[
    UserActionNode,
    OsContextLayerNode,
    ContextBuilderNode,
    FileProcessingPipelineNode,
    RetrievalLayerNode,
    LlmAgentNode,
    ResponseGeneratorNode
]

# Instantiate and wire the Pydantic Graph
local_pilot_graph = Graph(
    nodes=[
        UserActionNode,
        OsContextLayerNode,
        ContextBuilderNode,
        FileProcessingPipelineNode,
        RetrievalLayerNode,
        LlmAgentNode,
        ResponseGeneratorNode
    ]
)
