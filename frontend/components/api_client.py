import requests
import streamlit as st
from typing import Dict, Any, Optional

class APIClient:
    """Client to communicate with backend API"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def health_check(self) -> Dict[str, Any]:
        """Check API health"""
        try:
            response = requests.get(f"{self.base_url}/health")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def analyze(self, task: str, period: str, mode: str = "parallel") -> Dict[str, Any]:
        """Run analysis"""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/analyze",
                json={"task": task, "period": period, "execution_mode": mode}
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_status(self) -> Dict[str, Any]:
        """Get system status"""
        try:
            response = requests.get(f"{self.base_url}/api/v1/status")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent metrics"""
        try:
            response = requests.get(f"{self.base_url}/api/v1/agents/metrics")
            return response.json()
        except Exception as e:
            return {"error": str(e)}
