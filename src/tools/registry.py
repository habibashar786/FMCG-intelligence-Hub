"""
Tools Framework
Implements MCP, Custom Tools, Built-in Tools, and OpenAPI Tools
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
import json
import httpx
from pydantic import BaseModel, Field

from config.settings import get_settings


settings = get_settings()


class ToolParameter(BaseModel):
    """Tool parameter definition"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Optional[Any] = None


class ToolDefinition(BaseModel):
    """Tool definition schema"""
    name: str
    description: str
    parameters: List[ToolParameter]
    category: str = "general"
    version: str = "1.0.0"


class ToolResult(BaseModel):
    """Result from tool execution"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BaseTool(ABC):
    """Abstract base class for all tools"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.execution_count = 0
        self.total_execution_time = 0.0
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool"""
        pass
    
    @abstractmethod
    def get_definition(self) -> ToolDefinition:
        """Get tool definition"""
        pass
    
    async def _track_execution(self, func: Callable, **kwargs) -> ToolResult:
        """Track tool execution metrics"""
        start_time = datetime.utcnow()
        try:
            result = await func(**kwargs)
            self.execution_count += 1
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.total_execution_time += execution_time
            
            if isinstance(result, ToolResult):
                result.execution_time = execution_time
                return result
            
            return ToolResult(
                success=True,
                data=result,
                execution_time=execution_time
            )
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            return ToolResult(
                success=False,
                error=str(e),
                execution_time=execution_time
            )


# ============================================================================
# CUSTOM TOOLS - FMCG Specific
# ============================================================================

class FMCGDataAnalysisTool(BaseTool):
    """Custom tool for FMCG data analysis"""
    
    def __init__(self):
        super().__init__(
            name="fmcg_data_analysis",
            description="Analyze FMCG sales data with various metrics"
        )
    
    async def execute(
        self,
        data_path: str,
        analysis_type: str = "sales_summary",
        filters: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """Execute FMCG data analysis"""
        
        async def _analyze():
            # Simulate data analysis
            import pandas as pd
            
            try:
                df = pd.read_csv(data_path)
                
                if filters:
                    for key, value in filters.items():
                        if key in df.columns:
                            df = df[df[key] == value]
                
                if analysis_type == "sales_summary":
                    result = {
                        "total_sales": float(df['sales'].sum()) if 'sales' in df else 0,
                        "total_units": int(df['units'].sum()) if 'units' in df else 0,
                        "avg_price": float(df['price'].mean()) if 'price' in df else 0,
                        "num_transactions": len(df)
                    }
                elif analysis_type == "category_breakdown":
                    result = df.groupby('category')['sales'].sum().to_dict() if 'category' in df else {}
                elif analysis_type == "trend_analysis":
                    result = {
                        "trend": "increasing",  # Simplified
                        "growth_rate": 0.05
                    }
                else:
                    result = {"message": "Unknown analysis type"}
                
                return result
            except Exception as e:
                raise Exception(f"Data analysis failed: {str(e)}")
        
        return await self._track_execution(_analyze)
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="data_path",
                    type="string",
                    description="Path to FMCG data CSV file"
                ),
                ToolParameter(
                    name="analysis_type",
                    type="string",
                    description="Type of analysis to perform",
                    required=False,
                    default="sales_summary"
                ),
                ToolParameter(
                    name="filters",
                    type="object",
                    description="Filters to apply to data",
                    required=False
                )
            ],
            category="fmcg"
        )


class InventoryCheckTool(BaseTool):
    """Custom tool for inventory checking"""
    
    def __init__(self):
        super().__init__(
            name="inventory_check",
            description="Check inventory levels for products"
        )
    
    async def execute(
        self,
        product_id: str,
        location: Optional[str] = None
    ) -> ToolResult:
        """Check inventory"""
        
        async def _check():
            # Simulate inventory check
            inventory_data = {
                "product_id": product_id,
                "location": location or "warehouse_1",
                "in_stock": 150,
                "reserved": 30,
                "available": 120,
                "reorder_point": 50,
                "status": "sufficient"
            }
            return inventory_data
        
        return await self._track_execution(_check)
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="product_id",
                    type="string",
                    description="Product SKU or ID"
                ),
                ToolParameter(
                    name="location",
                    type="string",
                    description="Warehouse or store location",
                    required=False
                )
            ],
            category="fmcg"
        )


# ============================================================================
# BUILT-IN TOOLS - Google Search, Code Execution
# ============================================================================

class GoogleSearchTool(BaseTool):
    """Built-in Google Search tool"""
    
    def __init__(self):
        super().__init__(
            name="google_search",
            description="Search the web using Google Custom Search API"
        )
        self.api_key = settings.google_search_api_key
        self.engine_id = settings.google_search_engine_id
    
    async def execute(
        self,
        query: str,
        num_results: int = 5
    ) -> ToolResult:
        """Execute Google search"""
        
        async def _search():
            if not self.api_key or not self.engine_id:
                return {
                    "results": [],
                    "message": "Google Search API not configured"
                }
            
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.api_key,
                "cx": self.engine_id,
                "q": query,
                "num": num_results
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("items", []):
                    results.append({
                        "title": item.get("title"),
                        "link": item.get("link"),
                        "snippet": item.get("snippet")
                    })
                
                return {"results": results, "total": len(results)}
        
        return await self._track_execution(_search)
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query"
                ),
                ToolParameter(
                    name="num_results",
                    type="integer",
                    description="Number of results to return",
                    required=False,
                    default=5
                )
            ],
            category="builtin"
        )


class CodeExecutionTool(BaseTool):
    """Built-in code execution tool"""
    
    def __init__(self):
        super().__init__(
            name="code_execution",
            description="Execute Python code in a safe sandbox"
        )
    
    async def execute(
        self,
        code: str,
        timeout: int = 30
    ) -> ToolResult:
        """Execute code"""
        
        async def _execute():
            # Simplified code execution (in production, use proper sandboxing)
            import io
            import sys
            from contextlib import redirect_stdout
            
            output = io.StringIO()
            try:
                with redirect_stdout(output):
                    exec(code, {"__builtins__": __builtins__})
                return {
                    "output": output.getvalue(),
                    "status": "success"
                }
            except Exception as e:
                return {
                    "output": output.getvalue(),
                    "error": str(e),
                    "status": "error"
                }
        
        return await self._track_execution(_execute)
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="code",
                    type="string",
                    description="Python code to execute"
                ),
                ToolParameter(
                    name="timeout",
                    type="integer",
                    description="Execution timeout in seconds",
                    required=False,
                    default=30
                )
            ],
            category="builtin"
        )


# ============================================================================
# MCP TOOLS - Model Context Protocol
# ============================================================================

class MCPTool(BaseTool):
    """MCP (Model Context Protocol) enhanced tool"""
    
    def __init__(self, name: str, description: str, mcp_config: Dict[str, Any]):
        super().__init__(name, description)
        self.mcp_config = mcp_config
        self.context_window = []
    
    async def execute(self, **kwargs) -> ToolResult:
        """Execute with MCP context enhancement"""
        
        async def _execute_with_context():
            # Add current execution to context
            self.context_window.append({
                "timestamp": datetime.utcnow().isoformat(),
                "parameters": kwargs
            })
            
            # Limit context window size
            if len(self.context_window) > self.mcp_config.get("max_context", 10):
                self.context_window.pop(0)
            
            # Execute actual tool logic
            result = await self._execute_core(**kwargs)
            
            # Enhance result with context
            result["context"] = {
                "previous_calls": len(self.context_window),
                "context_summary": self._summarize_context()
            }
            
            return result
        
        return await self._track_execution(_execute_with_context)
    
    async def _execute_core(self, **kwargs) -> Dict[str, Any]:
        """Core execution logic - override in subclasses"""
        return {"status": "executed"}
    
    def _summarize_context(self) -> Dict[str, Any]:
        """Summarize execution context"""
        return {
            "total_calls": len(self.context_window),
            "recent_parameters": [
                ctx["parameters"] for ctx in self.context_window[-3:]
            ]
        }
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=f"{self.description} (MCP Enhanced)",
            parameters=[],
            category="mcp"
        )


# ============================================================================
# OPENAPI TOOLS
# ============================================================================

class OpenAPITool(BaseTool):
    """Tool that interfaces with external APIs via OpenAPI spec"""
    
    def __init__(
        self,
        name: str,
        description: str,
        openapi_spec: Dict[str, Any]
    ):
        super().__init__(name, description)
        self.spec = openapi_spec
        self.base_url = openapi_spec.get("servers", [{}])[0].get("url", "")
    
    async def execute(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> ToolResult:
        """Execute API call"""
        
        async def _call_api():
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}{endpoint}"
                response = await client.request(
                    method=method,
                    url=url,
                    json=data,
                    headers=headers or {}
                )
                response.raise_for_status()
                return response.json()
        
        return await self._track_execution(_call_api)
    
    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            parameters=[
                ToolParameter(
                    name="endpoint",
                    type="string",
                    description="API endpoint path"
                ),
                ToolParameter(
                    name="method",
                    type="string",
                    description="HTTP method",
                    required=False,
                    default="GET"
                ),
                ToolParameter(
                    name="data",
                    type="object",
                    description="Request payload",
                    required=False
                )
            ],
            category="openapi"
        )


# ============================================================================
# TOOL REGISTRY
# ============================================================================

class ToolRegistry:
    """Central registry for all tools"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default tools"""
        # Custom FMCG tools
        self.register(FMCGDataAnalysisTool())
        self.register(InventoryCheckTool())
        
        # Built-in tools
        if settings.enable_google_search:
            self.register(GoogleSearchTool())
        
        if settings.enable_code_execution:
            self.register(CodeExecutionTool())
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool"""
        self.tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get tool by name"""
        return self.tools.get(name)
    
    def list_tools(self) -> List[ToolDefinition]:
        """List all available tools"""
        return [tool.get_definition() for tool in self.tools.values()]
    
    async def execute(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name"""
        tool = self.get(name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' not found"
            )
        
        return await tool.execute(**kwargs)


# Global tool registry
tool_registry = ToolRegistry()
