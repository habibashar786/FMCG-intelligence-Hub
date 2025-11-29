"""
Agent Evaluation Framework
Implements comprehensive evaluation metrics for agent performance
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
import numpy as np

from src.models.base import AgentResult, AgentStatus, AgentType
from src.observability.monitor import get_logger


logger = get_logger(__name__)


@dataclass
class EvaluationMetrics:
    """Comprehensive evaluation metrics for an agent"""
    
    # Performance Metrics
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    average_response_time: float = 0.0
    p50_response_time: float = 0.0
    p95_response_time: float = 0.0
    p99_response_time: float = 0.0
    
    # Quality Metrics
    accuracy_score: float = 0.0
    relevance_score: float = 0.0
    completeness_score: float = 0.0
    overall_quality_score: float = 0.0
    
    # User Satisfaction
    user_satisfaction: float = 0.0
    positive_feedback_rate: float = 0.0
    negative_feedback_rate: float = 0.0
    
    # Resource Metrics
    average_token_usage: float = 0.0
    average_tool_calls: float = 0.0
    cache_hit_rate: float = 0.0
    
    # Reliability Metrics
    error_rate: float = 0.0
    timeout_rate: float = 0.0
    retry_rate: float = 0.0
    
    # Timestamp
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "performance": {
                "total_executions": self.total_executions,
                "successful_executions": self.successful_executions,
                "failed_executions": self.failed_executions,
                "average_response_time": round(self.average_response_time, 3),
                "p50_response_time": round(self.p50_response_time, 3),
                "p95_response_time": round(self.p95_response_time, 3),
                "p99_response_time": round(self.p99_response_time, 3)
            },
            "quality": {
                "accuracy": round(self.accuracy_score, 3),
                "relevance": round(self.relevance_score, 3),
                "completeness": round(self.completeness_score, 3),
                "overall": round(self.overall_quality_score, 3)
            },
            "user_satisfaction": {
                "score": round(self.user_satisfaction, 3),
                "positive_rate": round(self.positive_feedback_rate, 3),
                "negative_rate": round(self.negative_feedback_rate, 3)
            },
            "resource_usage": {
                "avg_token_usage": round(self.average_token_usage, 1),
                "avg_tool_calls": round(self.average_tool_calls, 1),
                "cache_hit_rate": round(self.cache_hit_rate, 3)
            },
            "reliability": {
                "error_rate": round(self.error_rate, 3),
                "timeout_rate": round(self.timeout_rate, 3),
                "retry_rate": round(self.retry_rate, 3)
            },
            "last_updated": self.last_updated.isoformat()
        }


class AgentEvaluator:
    """
    Evaluates agent performance and quality
    
    Features:
    - Real-time performance tracking
    - Quality scoring
    - User satisfaction measurement
    - Resource utilization analysis
    - Comparative analysis
    """
    
    def __init__(self, sample_rate: float = 0.1):
        self.sample_rate = sample_rate
        self.logger = get_logger(__name__)
        
        # Storage for metrics by agent type
        self.metrics: Dict[AgentType, EvaluationMetrics] = defaultdict(
            EvaluationMetrics
        )
        
        # Detailed execution history (limited size)
        self.execution_history: Dict[AgentType, List[Dict[str, Any]]] = defaultdict(
            lambda: []
        )
        self.max_history_size = 1000
        
        # Response time tracking for percentiles
        self.response_times: Dict[AgentType, List[float]] = defaultdict(list)
        
        # User feedback
        self.feedback: Dict[AgentType, List[Dict[str, Any]]] = defaultdict(list)
    
    def record_execution(
        self,
        agent_type: AgentType,
        result: AgentResult,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record agent execution for evaluation"""
        
        metrics = self.metrics[agent_type]
        
        # Update execution counts
        metrics.total_executions += 1
        
        if result.status == AgentStatus.COMPLETED:
            metrics.successful_executions += 1
        elif result.status == AgentStatus.FAILED:
            metrics.failed_executions += 1
        
        # Update response time
        self.response_times[agent_type].append(result.execution_time)
        
        # Limit response time history
        if len(self.response_times[agent_type]) > self.max_history_size:
            self.response_times[agent_type].pop(0)
        
        # Calculate average response time
        metrics.average_response_time = np.mean(
            self.response_times[agent_type]
        )
        
        # Calculate percentiles
        if len(self.response_times[agent_type]) >= 10:
            times = np.array(self.response_times[agent_type])
            metrics.p50_response_time = np.percentile(times, 50)
            metrics.p95_response_time = np.percentile(times, 95)
            metrics.p99_response_time = np.percentile(times, 99)
        
        # Calculate error rate
        if metrics.total_executions > 0:
            metrics.error_rate = (
                metrics.failed_executions / metrics.total_executions
            )
        
        # Record in history
        execution_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": result.status.value,
            "execution_time": result.execution_time,
            "data_size": len(str(result.data)),
            "details": details or {}
        }
        
        self.execution_history[agent_type].append(execution_record)
        
        # Limit history size
        if len(self.execution_history[agent_type]) > self.max_history_size:
            self.execution_history[agent_type].pop(0)
        
        # Update quality metrics (if available in result)
        if result.metrics:
            self._update_quality_metrics(agent_type, result.metrics)
        
        metrics.last_updated = datetime.utcnow()
        
        self.logger.info(
            "execution_recorded",
            agent_type=agent_type.value,
            status=result.status.value,
            execution_time=result.execution_time
        )
    
    def _update_quality_metrics(
        self,
        agent_type: AgentType,
        result_metrics: Dict[str, Any]
    ) -> None:
        """Update quality metrics from result"""
        metrics = self.metrics[agent_type]
        
        # Extract quality scores if available
        if "accuracy" in result_metrics:
            metrics.accuracy_score = result_metrics["accuracy"]
        
        if "relevance" in result_metrics:
            metrics.relevance_score = result_metrics["relevance"]
        
        if "completeness" in result_metrics:
            metrics.completeness_score = result_metrics["completeness"]
        
        # Calculate overall quality score
        quality_scores = [
            metrics.accuracy_score,
            metrics.relevance_score,
            metrics.completeness_score
        ]
        
        if any(quality_scores):
            metrics.overall_quality_score = np.mean([
                s for s in quality_scores if s > 0
            ])
    
    def record_feedback(
        self,
        agent_type: AgentType,
        rating: float,
        comment: Optional[str] = None,
        is_positive: bool = True
    ) -> None:
        """Record user feedback"""
        
        feedback_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "rating": rating,
            "comment": comment,
            "is_positive": is_positive
        }
        
        self.feedback[agent_type].append(feedback_record)
        
        # Limit feedback history
        if len(self.feedback[agent_type]) > self.max_history_size:
            self.feedback[agent_type].pop(0)
        
        # Update satisfaction metrics
        self._update_satisfaction_metrics(agent_type)
        
        self.logger.info(
            "feedback_recorded",
            agent_type=agent_type.value,
            rating=rating,
            is_positive=is_positive
        )
    
    def _update_satisfaction_metrics(self, agent_type: AgentType) -> None:
        """Update user satisfaction metrics"""
        metrics = self.metrics[agent_type]
        feedback_list = self.feedback[agent_type]
        
        if not feedback_list:
            return
        
        # Calculate average satisfaction
        ratings = [f["rating"] for f in feedback_list]
        metrics.user_satisfaction = np.mean(ratings)
        
        # Calculate feedback rates
        total_feedback = len(feedback_list)
        positive_count = sum(1 for f in feedback_list if f["is_positive"])
        
        metrics.positive_feedback_rate = positive_count / total_feedback
        metrics.negative_feedback_rate = 1 - metrics.positive_feedback_rate
    
    def record_resource_usage(
        self,
        agent_type: AgentType,
        token_usage: int,
        tool_calls: int,
        cache_hit: bool = False
    ) -> None:
        """Record resource usage"""
        metrics = self.metrics[agent_type]
        
        # Update token usage (running average)
        if metrics.total_executions > 0:
            total_tokens = (
                metrics.average_token_usage * (metrics.total_executions - 1) +
                token_usage
            )
            metrics.average_token_usage = total_tokens / metrics.total_executions
        else:
            metrics.average_token_usage = token_usage
        
        # Update tool calls (running average)
        if metrics.total_executions > 0:
            total_tools = (
                metrics.average_tool_calls * (metrics.total_executions - 1) +
                tool_calls
            )
            metrics.average_tool_calls = total_tools / metrics.total_executions
        else:
            metrics.average_tool_calls = tool_calls
        
        # Update cache hit rate
        # (Simplified - in production, track hits and misses separately)
        if cache_hit:
            metrics.cache_hit_rate = min(1.0, metrics.cache_hit_rate + 0.01)
        else:
            metrics.cache_hit_rate = max(0.0, metrics.cache_hit_rate - 0.001)
    
    def get_metrics(self, agent_type: AgentType) -> EvaluationMetrics:
        """Get evaluation metrics for an agent"""
        return self.metrics[agent_type]
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all agents"""
        return {
            agent_type.value: metrics.to_dict()
            for agent_type, metrics in self.metrics.items()
        }
    
    def compare_agents(
        self,
        agent_types: List[AgentType]
    ) -> Dict[str, Any]:
        """Compare multiple agents"""
        
        comparison = {
            "agents": agent_types,
            "metrics": {}
        }
        
        # Performance comparison
        comparison["metrics"]["response_time"] = {
            agent_type.value: self.metrics[agent_type].average_response_time
            for agent_type in agent_types
        }
        
        # Quality comparison
        comparison["metrics"]["quality_score"] = {
            agent_type.value: self.metrics[agent_type].overall_quality_score
            for agent_type in agent_types
        }
        
        # Reliability comparison
        comparison["metrics"]["error_rate"] = {
            agent_type.value: self.metrics[agent_type].error_rate
            for agent_type in agent_types
        }
        
        # Identify best performer
        best_quality = max(
            agent_types,
            key=lambda t: self.metrics[t].overall_quality_score
        )
        best_speed = min(
            agent_types,
            key=lambda t: self.metrics[t].average_response_time
        )
        most_reliable = min(
            agent_types,
            key=lambda t: self.metrics[t].error_rate
        )
        
        comparison["best_performers"] = {
            "highest_quality": best_quality.value,
            "fastest": best_speed.value,
            "most_reliable": most_reliable.value
        }
        
        return comparison
    
    def get_performance_report(
        self,
        agent_type: AgentType,
        time_window: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """Generate performance report"""
        
        metrics = self.metrics[agent_type]
        history = self.execution_history[agent_type]
        
        # Filter by time window if specified
        if time_window:
            cutoff = datetime.utcnow() - time_window
            history = [
                h for h in history
                if datetime.fromisoformat(h["timestamp"]) > cutoff
            ]
        
        report = {
            "agent_type": agent_type.value,
            "summary": metrics.to_dict(),
            "trends": self._calculate_trends(history),
            "recommendations": self._generate_recommendations(metrics)
        }
        
        return report
    
    def _calculate_trends(
        self,
        history: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Calculate performance trends"""
        
        if len(history) < 10:
            return {"trend": "insufficient_data"}
        
        # Split into two halves
        mid = len(history) // 2
        first_half = history[:mid]
        second_half = history[mid:]
        
        # Calculate average response time for each half
        avg_first = np.mean([h["execution_time"] for h in first_half])
        avg_second = np.mean([h["execution_time"] for h in second_half])
        
        # Determine trend
        if avg_second < avg_first * 0.9:
            trend = "improving"
        elif avg_second > avg_first * 1.1:
            trend = "degrading"
        else:
            trend = "stable"
        
        return {
            "response_time_trend": trend,
            "change_percent": round(
                ((avg_second - avg_first) / avg_first) * 100, 2
            )
        }
    
    def _generate_recommendations(
        self,
        metrics: EvaluationMetrics
    ) -> List[str]:
        """Generate improvement recommendations"""
        
        recommendations = []
        
        # Response time recommendations
        if metrics.average_response_time > 5.0:
            recommendations.append(
                "Consider optimizing response time (currently > 5s)"
            )
        
        # Error rate recommendations
        if metrics.error_rate > 0.05:
            recommendations.append(
                "High error rate detected (> 5%). Review error logs."
            )
        
        # Quality recommendations
        if metrics.overall_quality_score < 0.7:
            recommendations.append(
                "Quality score below threshold. Consider improving prompts or training."
            )
        
        # User satisfaction recommendations
        if metrics.user_satisfaction < 3.5:
            recommendations.append(
                "Low user satisfaction. Review user feedback and improve responses."
            )
        
        # Resource optimization
        if metrics.average_token_usage > 5000:
            recommendations.append(
                "High token usage. Consider implementing context compaction."
            )
        
        if not recommendations:
            recommendations.append("Performance is within acceptable parameters.")
        
        return recommendations


# Global evaluator instance
agent_evaluator = AgentEvaluator()
