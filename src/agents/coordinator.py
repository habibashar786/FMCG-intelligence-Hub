"""
Coordinator Agent
Main orchestrator for all sub-agents using LLM-powered decision making
"""
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime
import json

from src.models.base import (
    AgentType, AgentStatus, AgentContext, AgentResult,
    LLMAgent, AgentMessage, MessageType, ExecutionMode
)
from src.tools.registry import tool_registry
from src.memory.manager import memory_bank, session_service, context_compactor
from config.settings import get_settings

# Import specialized agents (to be created)
# from src.agents.analyst import DataAnalystAgent
# from src.agents.forecaster import ForecastingAgent
# from src.agents.reporter import ReportGeneratorAgent
# from src.agents.support import CustomerSupportAgent


settings = get_settings()


class CoordinatorAgent(LLMAgent):
    """
    Coordinator Agent - LLM-powered orchestration
    
    This agent:
    1. Receives user requests
    2. Determines which sub-agents to activate
    3. Coordinates parallel, sequential, or loop execution
    4. Aggregates results
    5. Uses memory and session management
    """
    
    def __init__(self):
        super().__init__(
            agent_type=AgentType.COORDINATOR,
            name="CoordinatorAgent",
            model_name=settings.gemini_model,
            temperature=settings.gemini_temperature,
            max_tokens=settings.gemini_max_tokens
        )
        
        # Sub-agents registry
        self.sub_agents: Dict[str, LLMAgent] = {}
        self._initialize_sub_agents()
        
        # Execution state
        self.current_execution_step = 0
        self.execution_plan: List[Dict[str, Any]] = []
        
    def _initialize_sub_agents(self):
        """Initialize all sub-agents"""
        # We'll import and initialize them when they're created
        # For now, this is a placeholder
        print("Coordinator: Sub-agents will be initialized here")
    
    async def execute(
        self,
        task: str,
        context: AgentContext,
        **kwargs
    ) -> AgentResult:
        """
        Main execution method
        Analyzes task and orchestrates appropriate agents
        """
        self.status = AgentStatus.RUNNING
        start_time = datetime.utcnow()
        
        try:
            # 1. Validate input
            if not await self.validate_input(task, context):
                return AgentResult(
                    agent_type=self.agent_type,
                    status=AgentStatus.FAILED,
                    error="Invalid input",
                    execution_time=0
                )
            
            # 2. Retrieve relevant memories
            memories = await memory_bank.retrieve(task, top_k=5)
            memory_context = [
                {"role": "system", "content": f"Previous context: {m.content}"}
                for m in memories
            ]
            
            # 3. Create execution plan using LLM
            execution_plan = await self._create_execution_plan(
                task, context, memory_context
            )
            self.execution_plan = execution_plan
            
            # 4. Execute plan
            result = await self._execute_plan(execution_plan, context)
            
            # 5. Store in memory
            await memory_bank.store(
                content=f"Task: {task}, Result: {json.dumps(result.data)}",
                metadata={
                    "task": task,
                    "session_id": context.session_id,
                    "status": result.status.value
                },
                importance=0.7
            )
            
            # 6. Update metrics
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            result.execution_time = execution_time
            self.update_metrics(result)
            
            self.status = AgentStatus.COMPLETED
            return result
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            self.status = AgentStatus.FAILED
            return AgentResult(
                agent_type=self.agent_type,
                status=AgentStatus.FAILED,
                error=str(e),
                execution_time=execution_time
            )
    
    async def _create_execution_plan(
        self,
        task: str,
        context: AgentContext,
        memory_context: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Use LLM to create execution plan
        Determines which agents to use and in what order
        """
        
        system_prompt = """You are a coordinator agent that creates execution plans.
Given a task, determine which specialized agents to use and how to execute them.

Available agents:
- DataAnalystAgent: Analyzes FMCG data, generates insights
- ForecastingAgent: Predicts future trends, demand forecasting
- ReportGeneratorAgent: Creates comprehensive reports
- CustomerSupportAgent: Handles customer queries

Execution modes:
- parallel: Multiple agents run simultaneously
- sequential: Agents run one after another
- loop: Agent runs iteratively until condition met
- single: Single agent execution

Respond with a JSON array of execution steps:
[
  {
    "agent": "agent_name",
    "mode": "execution_mode",
    "parameters": {...},
    "depends_on": [] // optional, for sequential
  }
]
"""
        
        # This is a simplified version - in production, use actual LLM
        # For now, we'll create a rule-based plan
        plan = await self._rule_based_plan(task)
        
        return plan
    
    async def _rule_based_plan(self, task: str) -> List[Dict[str, Any]]:
        """Create execution plan using rules (simplified)"""
        task_lower = task.lower()
        plan = []
        
        # Sales analysis task
        if "sales" in task_lower or "revenue" in task_lower or "analyze" in task_lower:
            plan.append({
                "agent": "analyst",
                "mode": ExecutionMode.PARALLEL,
                "parameters": {"analysis_type": "sales"},
                "depends_on": []
            })
        
        # Forecasting task
        if "forecast" in task_lower or "predict" in task_lower or "future" in task_lower:
            plan.append({
                "agent": "forecaster",
                "mode": ExecutionMode.SEQUENTIAL,
                "parameters": {"horizon": 30},
                "depends_on": ["analyst"] if plan else []
            })
        
        # Report generation
        if "report" in task_lower or "summary" in task_lower:
            plan.append({
                "agent": "reporter",
                "mode": ExecutionMode.LOOP,
                "parameters": {"format": "comprehensive"},
                "depends_on": [step["agent"] for step in plan]
            })
        
        # Customer support
        if "customer" in task_lower or "support" in task_lower or "question" in task_lower:
            plan.append({
                "agent": "support",
                "mode": ExecutionMode.SINGLE,
                "parameters": {"query": task},
                "depends_on": []
            })
        
        # Default to analysis if no specific task identified
        if not plan:
            plan.append({
                "agent": "analyst",
                "mode": ExecutionMode.SINGLE,
                "parameters": {},
                "depends_on": []
            })
        
        return plan
    
    async def _execute_plan(
        self,
        plan: List[Dict[str, Any]],
        context: AgentContext
    ) -> AgentResult:
        """Execute the plan with proper mode handling"""
        
        results = {}
        
        for step_idx, step in enumerate(plan):
            self.current_execution_step = step_idx
            agent_name = step["agent"]
            mode = step["mode"]
            parameters = step["parameters"]
            depends_on = step.get("depends_on", [])
            
            # Wait for dependencies
            if depends_on:
                await self._wait_for_dependencies(depends_on, results)
            
            # Execute based on mode
            if mode == ExecutionMode.PARALLEL:
                result = await self._execute_parallel(agent_name, parameters, context)
            elif mode == ExecutionMode.SEQUENTIAL:
                result = await self._execute_sequential(agent_name, parameters, context)
            elif mode == ExecutionMode.LOOP:
                result = await self._execute_loop(agent_name, parameters, context)
            else:  # SINGLE
                result = await self._execute_single(agent_name, parameters, context)
            
            results[agent_name] = result
        
        # Aggregate results
        aggregated_result = await self._aggregate_results(results)
        
        return AgentResult(
            agent_type=self.agent_type,
            status=AgentStatus.COMPLETED,
            data=aggregated_result,
            metrics={"plan_steps": len(plan), "agents_used": len(results)}
        )
    
    async def _execute_parallel(
        self,
        agent_name: str,
        parameters: Dict[str, Any],
        context: AgentContext
    ) -> Dict[str, Any]:
        """Execute agent in parallel mode"""
        # Simulate parallel execution with multiple tasks
        tasks = []
        
        # Create multiple instances or tasks
        for i in range(settings.max_parallel_agents):
            task = self._simulate_agent_execution(
                agent_name,
                {**parameters, "batch_id": i},
                context
            )
            tasks.append(task)
        
        # Execute all in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            "mode": "parallel",
            "results": [r for r in results if not isinstance(r, Exception)],
            "errors": [str(r) for r in results if isinstance(r, Exception)]
        }
    
    async def _execute_sequential(
        self,
        agent_name: str,
        parameters: Dict[str, Any],
        context: AgentContext
    ) -> Dict[str, Any]:
        """Execute agent in sequential mode"""
        results = []
        
        # Execute steps in sequence
        steps = parameters.get("steps", ["step1", "step2", "step3"])
        
        for step in steps:
            result = await self._simulate_agent_execution(
                agent_name,
                {**parameters, "current_step": step},
                context
            )
            results.append(result)
        
        return {
            "mode": "sequential",
            "results": results
        }
    
    async def _execute_loop(
        self,
        agent_name: str,
        parameters: Dict[str, Any],
        context: AgentContext
    ) -> Dict[str, Any]:
        """Execute agent in loop mode"""
        results = []
        max_iterations = parameters.get("max_iterations", 5)
        convergence_threshold = parameters.get("threshold", 0.95)
        
        for iteration in range(max_iterations):
            result = await self._simulate_agent_execution(
                agent_name,
                {**parameters, "iteration": iteration},
                context
            )
            results.append(result)
            
            # Check convergence (simplified)
            if result.get("quality_score", 0) >= convergence_threshold:
                break
        
        return {
            "mode": "loop",
            "iterations": len(results),
            "results": results,
            "converged": len(results) < max_iterations
        }
    
    async def _execute_single(
        self,
        agent_name: str,
        parameters: Dict[str, Any],
        context: AgentContext
    ) -> Dict[str, Any]:
        """Execute agent in single mode"""
        result = await self._simulate_agent_execution(agent_name, parameters, context)
        
        return {
            "mode": "single",
            "result": result
        }
    
    async def _simulate_agent_execution(
        self,
        agent_name: str,
        parameters: Dict[str, Any],
        context: AgentContext
    ) -> Dict[str, Any]:
        """
        Simulate agent execution
        In production, this would call actual sub-agents
        """
        await asyncio.sleep(0.1)  # Simulate work
        
        # Simulate different agent outputs
        if agent_name == "analyst":
            return {
                "agent": agent_name,
                "analysis": "Sales data shows 15% growth",
                "metrics": {"revenue": 1000000, "units": 5000},
                "quality_score": 0.92
            }
        elif agent_name == "forecaster":
            return {
                "agent": agent_name,
                "forecast": "Predicted 20% growth next quarter",
                "confidence": 0.85,
                "quality_score": 0.88
            }
        elif agent_name == "reporter":
            return {
                "agent": agent_name,
                "report": "Comprehensive quarterly report generated",
                "sections": 5,
                "quality_score": 0.95
            }
        else:  # support
            return {
                "agent": agent_name,
                "response": "Customer query resolved",
                "satisfaction": 0.9,
                "quality_score": 0.87
            }
    
    async def _wait_for_dependencies(
        self,
        dependencies: List[str],
        results: Dict[str, Any]
    ) -> None:
        """Wait for dependent agents to complete"""
        while not all(dep in results for dep in dependencies):
            await asyncio.sleep(0.1)
    
    async def _aggregate_results(
        self,
        results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Aggregate results from all agents"""
        return {
            "summary": "Multi-agent execution completed",
            "agents_executed": list(results.keys()),
            "detailed_results": results,
            "overall_quality": sum(
                r.get("quality_score", 0.5) for r in results.values()
            ) / len(results) if results else 0,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def validate_input(self, task: str, context: AgentContext) -> bool:
        """Validate input parameters"""
        if not task or len(task.strip()) == 0:
            return False
        if not context.session_id:
            return False
        return True
    
    async def send_to_agent(self, agent_name: str, message: AgentMessage) -> None:
        """Send message to sub-agent (A2A Protocol)"""
        # This will be implemented with actual message queue
        pass
    
    async def broadcast_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Broadcast event to all agents"""
        message = AgentMessage(
            type=MessageType.EVENT,
            sender=self.name,
            receiver="*",
            content={"event_type": event_type, "data": data}
        )
        # Broadcast through message queue
        pass
    
    # Override pause/resume for coordinator-specific logic
    def _get_current_state(self) -> Dict[str, Any]:
        """Get current state for checkpoint"""
        return {
            "status": self.status.value,
            "execution_plan": self.execution_plan,
            "current_step": self.current_execution_step
        }
    
    def _restore_state(self, state: Dict[str, Any]) -> None:
        """Restore state from checkpoint"""
        self.execution_plan = state.get("execution_plan", [])
        self.current_execution_step = state.get("current_step", 0)
    
    async def _continue_execution(self, step: int) -> AgentResult:
        """Continue execution from specific step"""
        # Resume from the saved step
        remaining_plan = self.execution_plan[step:]
        
        # Execute remaining steps
        context = AgentContext(session_id="resumed")
        result = await self._execute_plan(remaining_plan, context)
        
        return result


# Example usage functions
async def analyze_sales(
    period: str = "Q4-2024",
    category: Optional[str] = None
) -> Dict[str, Any]:
    """Analyze FMCG sales data"""
    coordinator = CoordinatorAgent()
    
    task = f"Analyze sales data for {period}"
    if category:
        task += f" in category {category}"
    
    context = AgentContext(
        session_id=f"sales_analysis_{datetime.utcnow().timestamp()}",
        metadata={"period": period, "category": category}
    )
    
    result = await coordinator.execute(task, context)
    return result.data


async def forecast_demand(
    product_id: str,
    horizon_days: int = 30
) -> Dict[str, Any]:
    """Forecast product demand"""
    coordinator = CoordinatorAgent()
    
    task = f"Forecast demand for product {product_id} for next {horizon_days} days"
    
    context = AgentContext(
        session_id=f"forecast_{datetime.utcnow().timestamp()}",
        metadata={"product_id": product_id, "horizon": horizon_days}
    )
    
    result = await coordinator.execute(task, context)
    return result.data


async def handle_support_query(query: str) -> Dict[str, Any]:
    """Handle customer support query"""
    coordinator = CoordinatorAgent()
    
    context = AgentContext(
        session_id=f"support_{datetime.utcnow().timestamp()}",
        metadata={"query_type": "customer_support"}
    )
    
    result = await coordinator.execute(query, context)
    return result.data
