"""
Main FastAPI Application
Implements REST API for the multi-agent system
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import uvicorn
from datetime import datetime

from config.settings import get_settings
from src.agents.coordinator import CoordinatorAgent, analyze_sales, forecast_demand, handle_support_query
from src.memory.manager import session_service, memory_bank
from src.observability.monitor import agent_monitor, get_logger
from src.models.base import AgentContext, AgentStatus


settings = get_settings()
logger = get_logger(__name__)


# ============================================================================
# LIFESPAN MANAGEMENT
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("application_startup", version=settings.app_version)
    
    # Start session cleanup task
    await session_service.start_cleanup_task()
    
    yield
    
    # Shutdown
    logger.info("application_shutdown")


# ============================================================================
# APPLICATION SETUP
# ============================================================================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Enterprise Multi-Agent System for FMCG Data Analysis",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AnalysisRequest(BaseModel):
    """Request model for data analysis"""
    task: str = Field(..., description="Analysis task description")
    period: Optional[str] = Field(None, description="Time period (e.g., Q4-2024)")
    category: Optional[str] = Field(None, description="Product category")
    metrics: List[str] = Field(default_factory=list, description="Metrics to analyze")
    session_id: Optional[str] = None
    user_id: Optional[str] = None


class ForecastRequest(BaseModel):
    """Request model for forecasting"""
    product_id: str = Field(..., description="Product SKU or ID")
    horizon_days: int = Field(30, description="Forecast horizon in days")
    confidence_interval: float = Field(0.95, description="Confidence interval")
    session_id: Optional[str] = None


class SupportQueryRequest(BaseModel):
    """Request model for customer support"""
    query: str = Field(..., description="Customer query")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    session_id: Optional[str] = None


class SessionCreateRequest(BaseModel):
    """Request to create a new session"""
    user_id: Optional[str] = None


class PauseResumeRequest(BaseModel):
    """Request to pause/resume agent execution"""
    session_id: str


class AgentResponse(BaseModel):
    """Standard agent response"""
    success: bool
    data: Dict[str, Any]
    session_id: str
    execution_time: float
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health_status = agent_monitor.get_health_status()
    return health_status


@app.get("/api/v1/status")
async def system_status():
    """Get system status"""
    session_stats = await session_service.get_stats()
    memory_stats = await memory_bank.get_stats()
    
    return {
        "status": "operational",
        "version": settings.app_version,
        "environment": settings.environment,
        "sessions": session_stats,
        "memory": memory_stats,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# AGENT EXECUTION ENDPOINTS
# ============================================================================

@app.post("/api/v1/analyze", response_model=AgentResponse)
async def analyze_data(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """
    Analyze FMCG data
    
    This endpoint demonstrates:
    - Multi-agent coordination
    - Parallel agent execution
    - Memory integration
    """
    try:
        # Create or get session
        session_id = request.session_id or f"analysis_{datetime.utcnow().timestamp()}"
        session = await session_service.get_session(session_id)
        if not session:
            session = await session_service.create_session(session_id, request.user_id)
        
        # Create coordinator
        coordinator = CoordinatorAgent()
        
        # Build task
        task = request.task
        if request.period:
            task += f" for period {request.period}"
        if request.category:
            task += f" in category {request.category}"
        
        # Create context
        context = AgentContext(
            session_id=session_id,
            user_id=request.user_id,
            metadata={
                "period": request.period,
                "category": request.category,
                "metrics": request.metrics
            }
        )
        
        # Execute with monitoring
        with agent_monitor.monitor_execution("coordinator", task, session_id):
            result = await coordinator.execute(task, context)
        
        # Update session
        await session_service.update_session(
            session_id,
            state={"last_result": result.data}
        )
        
        return AgentResponse(
            success=result.status == AgentStatus.COMPLETED,
            data=result.data,
            session_id=session_id,
            execution_time=result.execution_time
        )
        
    except Exception as e:
        logger.error("analysis_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/forecast", response_model=AgentResponse)
async def create_forecast(request: ForecastRequest):
    """
    Generate demand forecast
    
    This endpoint demonstrates:
    - Sequential agent execution
    - Time-series analysis
    - Predictive modeling
    """
    try:
        session_id = request.session_id or f"forecast_{datetime.utcnow().timestamp()}"
        
        result_data = await forecast_demand(
            product_id=request.product_id,
            horizon_days=request.horizon_days
        )
        
        return AgentResponse(
            success=True,
            data=result_data,
            session_id=session_id,
            execution_time=0.5
        )
        
    except Exception as e:
        logger.error("forecast_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/support", response_model=AgentResponse)
async def customer_support(request: SupportQueryRequest):
    """
    Handle customer support query
    
    This endpoint demonstrates:
    - Single agent execution
    - Context-aware responses
    - Customer interaction patterns
    """
    try:
        session_id = request.session_id or f"support_{datetime.utcnow().timestamp()}"
        
        result_data = await handle_support_query(request.query)
        
        return AgentResponse(
            success=True,
            data=result_data,
            session_id=session_id,
            execution_time=0.3
        )
        
    except Exception as e:
        logger.error("support_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SESSION MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/api/v1/sessions")
async def create_session(request: SessionCreateRequest):
    """Create a new session"""
    session_id = f"session_{datetime.utcnow().timestamp()}"
    session = await session_service.create_session(session_id, request.user_id)
    
    return {
        "session_id": session.session_id,
        "created_at": session.created_at.isoformat()
    }


@app.get("/api/v1/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session details"""
    session = await session_service.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "created_at": session.created_at.isoformat(),
        "last_accessed": session.last_accessed.isoformat(),
        "is_active": session.is_active,
        "state": session.state
    }


@app.post("/api/v1/sessions/{session_id}/pause")
async def pause_session(session_id: str):
    """
    Pause agent execution
    
    Demonstrates long-running operations with pause capability
    """
    session = await session_service.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # In production, this would pause actual agent execution
    await session_service.update_session(
        session_id,
        state={"paused": True, "paused_at": datetime.utcnow().isoformat()}
    )
    
    return {
        "status": "paused",
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/v1/sessions/{session_id}/resume")
async def resume_session(session_id: str):
    """
    Resume paused agent execution
    
    Demonstrates resume capability for long-running operations
    """
    session = await session_service.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # In production, this would resume actual agent execution
    await session_service.update_session(
        session_id,
        state={"paused": False, "resumed_at": datetime.utcnow().isoformat()}
    )
    
    return {
        "status": "resumed",
        "session_id": session_id,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.delete("/api/v1/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    success = await session_service.delete_session(session_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {"status": "deleted", "session_id": session_id}


# ============================================================================
# MEMORY ENDPOINTS
# ============================================================================

@app.post("/api/v1/memory")
async def store_memory(content: str, metadata: Dict[str, Any] = None, importance: float = 0.5):
    """Store information in long-term memory"""
    memory_id = await memory_bank.store(content, metadata, importance)
    
    return {
        "memory_id": memory_id,
        "status": "stored",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/api/v1/memory/search")
async def search_memory(query: str, top_k: int = 5):
    """Search memory bank"""
    memories = await memory_bank.retrieve(query, top_k)
    
    return {
        "query": query,
        "results": [
            {
                "id": m.id,
                "content": m.content,
                "metadata": m.metadata,
                "importance": m.importance,
                "timestamp": m.timestamp.isoformat()
            }
            for m in memories
        ]
    }


# ============================================================================
# METRICS & OBSERVABILITY ENDPOINTS
# ============================================================================

@app.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics endpoint"""
    # Metrics are exposed on a separate port by Prometheus
    return {"message": "Metrics available on port " + str(settings.prometheus_port)}


@app.get("/api/v1/agents/metrics")
async def agent_metrics():
    """Get agent performance metrics"""
    coordinator = CoordinatorAgent()
    
    return {
        "coordinator": {
            "total_executions": coordinator.metrics.total_executions,
            "successful_executions": coordinator.metrics.successful_executions,
            "failed_executions": coordinator.metrics.failed_executions,
            "average_execution_time": coordinator.metrics.average_execution_time,
            "quality_score": coordinator.metrics.quality_score
        },
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        error=str(exc),
        exc_info=True
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Run the application"""
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        workers=settings.api_workers if not settings.debug else 1,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
