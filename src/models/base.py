"""
Base Agent Models and Interfaces
Core abstractions for all agents in the system
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field
import uuid


class AgentType(str, Enum):
    """Types of agents in the system"""
    COORDINATOR = "coordinator"
    ANALYST = "analyst"
    FORECASTER = "forecaster"
    REPORTER = "reporter"
    CUSTOMER_SUPPORT = "customer_support"


class AgentStatus(str, Enum):
    """Agent execution status"""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionMode(str, Enum):
    """Agent execution modes"""
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    LOOP = "loop"
    SINGLE = "single"


class MessageType(str, Enum):
    """A2A message types"""
    REQUEST = "request"
    RESPONSE = "response"
    EVENT = "event"
    NOTIFICATION = "notification"


class AgentMessage(BaseModel):
    """Message format for agent communication (A2A Protocol)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType
    sender: str
    receiver: str
    content: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AgentContext(BaseModel):
    """Context for agent execution"""
    session_id: str
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    memory: Dict[str, Any] = Field(default_factory=dict)
    state: Dict[str, Any] = Field(default_factory=dict)


class AgentCheckpoint(BaseModel):
    """Checkpoint for pause/resume functionality"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_type: AgentType
    session_id: str
    state: Dict[str, Any]
    context: AgentContext
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    execution_step: int = 0
    can_resume: bool = True


class AgentResult(BaseModel):
    """Result from agent execution"""
    agent_type: AgentType
    status: AgentStatus
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    execution_time: float = 0.0
    metrics: Dict[str, Any] = Field(default_factory=dict)
    checkpoint: Optional[AgentCheckpoint] = None
    trace_id: Optional[str] = None


class ToolCall(BaseModel):
    """Tool execution details"""
    name: str
    parameters: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0


class AgentMetrics(BaseModel):
    """Metrics for agent evaluation"""
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    average_execution_time: float = 0.0
    total_tool_calls: int = 0
    cache_hit_rate: float = 0.0
    quality_score: float = 0.0
    user_satisfaction: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class BaseAgent(ABC):
    """Abstract base class for all agents"""
    
    def __init__(
        self,
        agent_type: AgentType,
        name: str,
        execution_mode: ExecutionMode = ExecutionMode.SINGLE
    ):
        self.agent_type = agent_type
        self.name = name
        self.execution_mode = execution_mode
        self.status = AgentStatus.IDLE
        self.metrics = AgentMetrics()
        self._checkpoints: Dict[str, AgentCheckpoint] = {}
    
    @abstractmethod
    async def execute(
        self,
        task: str,
        context: AgentContext,
        **kwargs
    ) -> AgentResult:
        """Execute the agent's main task"""
        pass
    
    @abstractmethod
    async def validate_input(self, task: str, context: AgentContext) -> bool:
        """Validate input before execution"""
        pass
    
    async def pause(self, session_id: str) -> AgentCheckpoint:
        """Pause execution and create checkpoint"""
        checkpoint = AgentCheckpoint(
            agent_type=self.agent_type,
            session_id=session_id,
            state=self._get_current_state(),
            context=self._get_current_context(),
            execution_step=self._get_execution_step()
        )
        self._checkpoints[session_id] = checkpoint
        self.status = AgentStatus.PAUSED
        return checkpoint
    
    async def resume(self, checkpoint: AgentCheckpoint) -> AgentResult:
        """Resume execution from checkpoint"""
        self._restore_state(checkpoint.state)
        self._restore_context(checkpoint.context)
        self.status = AgentStatus.RUNNING
        return await self._continue_execution(checkpoint.execution_step)
    
    def _get_current_state(self) -> Dict[str, Any]:
        """Get current agent state - override in subclasses"""
        return {"status": self.status.value}
    
    def _get_current_context(self) -> AgentContext:
        """Get current execution context - override in subclasses"""
        return AgentContext(session_id="default")
    
    def _get_execution_step(self) -> int:
        """Get current execution step - override in subclasses"""
        return 0
    
    def _restore_state(self, state: Dict[str, Any]) -> None:
        """Restore agent state - override in subclasses"""
        pass
    
    def _restore_context(self, context: AgentContext) -> None:
        """Restore execution context - override in subclasses"""
        pass
    
    async def _continue_execution(self, step: int) -> AgentResult:
        """Continue execution from step - override in subclasses"""
        return AgentResult(
            agent_type=self.agent_type,
            status=AgentStatus.COMPLETED,
            data={}
        )
    
    async def send_message(self, message: AgentMessage) -> None:
        """Send message to another agent (A2A Protocol)"""
        # Will be implemented with message queue
        pass
    
    async def receive_message(self) -> Optional[AgentMessage]:
        """Receive message from another agent"""
        # Will be implemented with message queue
        pass
    
    def update_metrics(self, result: AgentResult) -> None:
        """Update agent metrics"""
        self.metrics.total_executions += 1
        if result.status == AgentStatus.COMPLETED:
            self.metrics.successful_executions += 1
        elif result.status == AgentStatus.FAILED:
            self.metrics.failed_executions += 1
        
        # Update average execution time
        total_time = (self.metrics.average_execution_time * 
                     (self.metrics.total_executions - 1) + 
                     result.execution_time)
        self.metrics.average_execution_time = (
            total_time / self.metrics.total_executions
        )
        self.metrics.last_updated = datetime.utcnow()


class LLMAgent(BaseAgent):
    """Base class for LLM-powered agents"""
    
    def __init__(
        self,
        agent_type: AgentType,
        name: str,
        model_name: str = "gemini-2.0-flash-exp",
        temperature: float = 0.7,
        max_tokens: int = 8192,
        execution_mode: ExecutionMode = ExecutionMode.SINGLE
    ):
        super().__init__(agent_type, name, execution_mode)
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.conversation_history: List[Dict[str, str]] = []
    
    async def generate_response(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate LLM response - to be implemented with actual LLM"""
        # This will be implemented with Google Gemini
        pass
    
    def add_to_history(self, role: str, content: str) -> None:
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
    
    def clear_history(self) -> None:
        """Clear conversation history"""
        self.conversation_history.clear()
