"""
Memory and Session Management System
Implements long-term memory and session state management
"""
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json
import hashlib

from pydantic import BaseModel, Field
import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from config.settings import get_settings


settings = get_settings()


class MemoryEntry(BaseModel):
    """Single memory entry"""
    id: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    importance: float = 0.5
    access_count: int = 0
    last_accessed: datetime = Field(default_factory=datetime.utcnow)


class SessionState(BaseModel):
    """Session state for pause/resume"""
    session_id: str
    user_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    state: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class MemoryBank:
    """
    Long-term memory storage with vector similarity search
    Uses ChromaDB for persistent memory storage
    """
    
    def __init__(self):
        self.settings = get_settings()
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.Client(
            ChromaSettings(
                persist_directory=self.settings.chroma_persist_directory,
                anonymized_telemetry=False
            )
        )
        
        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.settings.chroma_collection_name,
            metadata={"description": "FMCG Agent Memory Bank"}
        )
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(
            self.settings.embedding_model
        )
        
        self.memories: Dict[str, MemoryEntry] = {}
    
    def _generate_id(self, content: str) -> str:
        """Generate unique ID for memory entry"""
        return hashlib.sha256(
            f"{content}{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
    
    def _generate_embedding(self, content: str) -> List[float]:
        """Generate embedding for content"""
        return self.embedding_model.encode(content).tolist()
    
    async def store(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 0.5
    ) -> str:
        """Store new memory"""
        memory_id = self._generate_id(content)
        embedding = self._generate_embedding(content)
        
        memory = MemoryEntry(
            id=memory_id,
            content=content,
            metadata=metadata or {},
            embedding=embedding,
            importance=importance
        )
        
        # Store in ChromaDB
        meta_dict = metadata or {}
        meta_dict.update({
            "importance": importance,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        self.collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[meta_dict]
        )
        
        self.memories[memory_id] = memory
        return memory_id
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        min_importance: float = 0.0
    ) -> List[MemoryEntry]:
        """Retrieve relevant memories using similarity search"""
        query_embedding = self._generate_embedding(query)
        
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"importance": {"$gte": min_importance}}
        )
        
        memories = []
        if results['ids']:
            for i, memory_id in enumerate(results['ids'][0]):
                if memory_id in self.memories:
                    memory = self.memories[memory_id]
                    memory.access_count += 1
                    memory.last_accessed = datetime.utcnow()
                    memories.append(memory)
        
        return memories
    
    async def update(
        self,
        memory_id: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        importance: Optional[float] = None
    ) -> bool:
        """Update existing memory"""
        if memory_id not in self.memories:
            return False
        
        memory = self.memories[memory_id]
        
        if content:
            memory.content = content
            memory.embedding = self._generate_embedding(content)
        
        if metadata:
            memory.metadata.update(metadata)
        
        if importance is not None:
            memory.importance = importance
        
        # Update in ChromaDB
        self.collection.update(
            ids=[memory_id],
            embeddings=[memory.embedding] if content else None,
            documents=[content] if content else None,
            metadatas=[{
                **memory.metadata,
                "importance": memory.importance,
                "timestamp": memory.timestamp.isoformat()
            }]
        )
        
        return True
    
    async def delete(self, memory_id: str) -> bool:
        """Delete memory"""
        if memory_id not in self.memories:
            return False
        
        self.collection.delete(ids=[memory_id])
        del self.memories[memory_id]
        return True
    
    async def cleanup_old_memories(self, days: int = 90) -> int:
        """Remove memories older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted_count = 0
        
        for memory_id, memory in list(self.memories.items()):
            if memory.timestamp < cutoff_date and memory.importance < 0.7:
                await self.delete(memory_id)
                deleted_count += 1
        
        return deleted_count
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get memory bank statistics"""
        return {
            "total_memories": len(self.memories),
            "average_importance": sum(
                m.importance for m in self.memories.values()
            ) / len(self.memories) if self.memories else 0,
            "most_accessed": max(
                self.memories.values(),
                key=lambda m: m.access_count,
                default=None
            ),
            "oldest_memory": min(
                self.memories.values(),
                key=lambda m: m.timestamp,
                default=None
            )
        }


class InMemorySessionService:
    """
    In-memory session management service
    Handles session state for pause/resume functionality
    """
    
    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}
        self.settings = get_settings()
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def create_session(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> SessionState:
        """Create new session"""
        session = SessionState(
            session_id=session_id,
            user_id=user_id
        )
        self.sessions[session_id] = session
        return session
    
    async def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get existing session"""
        session = self.sessions.get(session_id)
        if session:
            session.last_accessed = datetime.utcnow()
        return session
    
    async def update_session(
        self,
        session_id: str,
        state: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update session state"""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        if state:
            session.state.update(state)
        if context:
            session.context.update(context)
        
        session.last_accessed = datetime.utcnow()
        return True
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        timeout = timedelta(seconds=self.settings.session_timeout)
        cutoff_time = datetime.utcnow() - timeout
        deleted_count = 0
        
        for session_id, session in list(self.sessions.items()):
            if session.last_accessed < cutoff_time:
                await self.delete_session(session_id)
                deleted_count += 1
        
        return deleted_count
    
    async def start_cleanup_task(self) -> None:
        """Start background cleanup task"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop"""
        while True:
            await asyncio.sleep(self.settings.session_cleanup_interval)
            deleted = await self.cleanup_expired_sessions()
            if deleted > 0:
                print(f"Cleaned up {deleted} expired sessions")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get session statistics"""
        active_sessions = sum(
            1 for s in self.sessions.values() if s.is_active
        )
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": active_sessions,
            "inactive_sessions": len(self.sessions) - active_sessions
        }


class ContextCompactor:
    """
    Context engineering - dynamic context compaction
    Reduces context size while preserving important information
    """
    
    def __init__(self, max_size: int = 4096):
        self.max_size = max_size
    
    async def compact(
        self,
        context: List[Dict[str, str]],
        target_size: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """Compact context to target size"""
        if target_size is None:
            target_size = self.max_size
        
        # Calculate current size (rough estimate)
        current_size = sum(
            len(json.dumps(msg)) for msg in context
        )
        
        if current_size <= target_size:
            return context
        
        # Strategy: Keep first and last messages, summarize middle
        if len(context) <= 3:
            return context
        
        compacted = [
            context[0],  # Keep first message
            {
                "role": "system",
                "content": f"[Summarized {len(context) - 2} messages]"
            },
            context[-1]  # Keep last message
        ]
        
        return compacted
    
    async def extract_key_info(
        self,
        context: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Extract key information from context"""
        key_entities = set()
        key_topics = set()
        
        for msg in context:
            content = msg.get("content", "")
            # Simple extraction (can be enhanced with NLP)
            words = content.split()
            for word in words:
                if word.isupper() and len(word) > 2:
                    key_entities.add(word)
        
        return {
            "entities": list(key_entities),
            "topics": list(key_topics),
            "message_count": len(context)
        }


# Global instances
memory_bank = MemoryBank()
session_service = InMemorySessionService()
context_compactor = ContextCompactor()
