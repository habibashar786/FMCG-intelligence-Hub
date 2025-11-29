import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from components.api_client import APIClient

st.set_page_config(page_title="Sales Analytics", page_icon="chart", layout="wide")

api = APIClient()

st.title("Sales Analytics Dashboard")
st.markdown("Get instant insights from your FMCG data")

st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("What would you like to analyze?")
    
    analysis_type = st.selectbox(
        "Choose analysis type:",
        [
            "Sales Performance by Category",
            "Top Performing Products",
            "Store Performance Comparison",
            "Monthly Sales Trends",
            "Customer Purchase Patterns"
        ]
    )
    
    period = st.selectbox(
        "Time Period:",
        ["Last 6 Months (2024)", "Q4 2024", "Q3 2024", "November 2024", "October 2024"]
    )

with col2:
    st.subheader("Analysis Speed")
    speed = st.radio(
        "How fast do you need results?",
        ["Fast (Parallel)", "Detailed (Sequential)"],
        help="Fast mode uses multiple AI agents at once. Detailed mode is more thorough."
    )

if st.button("Generate Insights", type="primary", use_container_width=True):
    mode = "parallel" if "Fast" in speed else "sequential"
    
    with st.spinner("Analyzing your data with AI agents..."):
        result = api.analyze(analysis_type, period, mode)
        
        if "error" not in result and result.get("success"):
            st.success("Analysis Complete!")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Analysis Time", f"{result.get('execution_time', 0):.2f}s")
            with col2:
                st.metric("Quality Score", f"{result['data'].get('overall_quality', 0) * 100:.0f}%")
            with col3:
                st.metric("AI Agents Used", len(result['data'].get('agents_executed', [])))
            
            st.markdown("---")
            st.subheader("Key Insights")
            
            if 'detailed_results' in result['data']:
                for agent_name, agent_data in result['data']['detailed_results'].items():
                    if 'results' in agent_data and agent_data['results']:
                        first_result = agent_data['results'][0]
                        
                        st.markdown(f"### {first_result.get('analysis', 'Analysis Results')}")
                        
                        if 'metrics' in first_result:
                            metrics = first_result['metrics']
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric("Total Revenue", f"${metrics.get('revenue', 0):,.2f}")
                            with col2:
                                st.metric("Units Sold", f"{metrics.get('units', 0):,}")
            
            with st.expander("View Technical Details"):
                st.json(result)
        else:
            st.error("Failed to generate insights. Please check if backend is running.")

st.markdown("---")
st.info("Tip: This dashboard uses AI agents to analyze your FMCG sales data in real-time.")
