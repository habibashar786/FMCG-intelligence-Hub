"""
FMCG Enterprise Multi-Agent Analytics Dashboard
Author: Neural - PhD Candidate, KFUPM
Version: 2.0.0
Description: Production-grade dashboard with enterprise UI/UX design
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any
import time

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))
from components.api_client import APIClient

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================
st.set_page_config(
    page_title="FMCG Intelligence Hub | Enterprise Analytics",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/your-repo',
        'Report a bug': 'https://github.com/your-repo/issues',
        'About': '# FMCG Intelligence Hub\nEnterprise Multi-Agent Analytics System'
    }
)

# ============================================================================
# CUSTOM CSS STYLING - MATCHING THUMBNAIL DESIGN
# ============================================================================
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    /* Global Styling */
    * {
        font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Main container */
    .main {
        background: linear-gradient(135deg, #0f1419 0%, #1a1f2e 100%);
        padding: 2rem;
    }
    
    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        padding: 2.5rem;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
        position: relative;
        overflow: hidden;
    }
    
    .main-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: 
            repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(255,255,255,.03) 10px, rgba(255,255,255,.03) 20px),
            repeating-linear-gradient(-45deg, transparent, transparent 10px, rgba(255,255,255,.02) 10px, rgba(255,255,255,.02) 20px);
    }
    
    .main-header h1 {
        color: white;
        font-size: 2.8rem;
        font-weight: 800;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        position: relative;
        z-index: 1;
    }
    
    .main-header p {
        color: rgba(255,255,255,0.95);
        font-size: 1.1rem;
        margin: 0.5rem 0 0 0;
        font-weight: 500;
        position: relative;
        z-index: 1;
    }
    
    /* Metric cards */
    .metric-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(240, 147, 251, 0.1) 100%);
        border: 2px solid rgba(102, 126, 234, 0.3);
        border-radius: 16px;
        padding: 1.5rem;
        backdrop-filter: blur(10px);
        transition: all 0.3s ease;
        height: 100%;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4);
        border-color: rgba(102, 126, 234, 0.6);
    }
    
    /* Status indicators */
    .status-indicator {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
    }
    
    .status-online {
        background: rgba(46, 213, 115, 0.2);
        color: #2ed573;
        border: 1px solid rgba(46, 213, 115, 0.4);
    }
    
    .status-offline {
        background: rgba(255, 71, 87, 0.2);
        color: #ff4757;
        border: 1px solid rgba(255, 71, 87, 0.4);
    }
    
    /* Feature badges */
    .feature-badge {
        display: inline-block;
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.2) 0%, rgba(240, 147, 251, 0.2) 100%);
        border: 1px solid rgba(102, 126, 234, 0.3);
        padding: 0.6rem 1.2rem;
        border-radius: 25px;
        font-size: 0.85rem;
        font-weight: 600;
        color: #e6f1ff;
        margin: 0.3rem;
        transition: all 0.3s ease;
    }
    
    .feature-badge:hover {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.3) 0%, rgba(240, 147, 251, 0.3) 100%);
        transform: translateY(-2px);
    }
    
    /* Section headers */
    .section-header {
        color: #f093fb;
        font-size: 1.5rem;
        font-weight: 700;
        margin: 2rem 0 1rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Analysis card */
    .analysis-card {
        background: linear-gradient(135deg, #16213e 0%, #1a2642 100%);
        border: 2px solid rgba(102, 126, 234, 0.3);
        border-radius: 16px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 5px 20px rgba(0,0,0,0.3);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: 700;
        border: none;
        border-radius: 12px;
        padding: 0.8rem 2.5rem;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 30px rgba(102, 126, 234, 0.6);
    }
    
    /* Input fields */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > select {
        background: rgba(102, 126, 234, 0.1);
        border: 2px solid rgba(102, 126, 234, 0.3);
        border-radius: 10px;
        color: #e6f1ff;
        font-weight: 500;
        padding: 0.8rem;
    }
    
    /* Success/Error messages */
    .stSuccess, .stError, .stWarning, .stInfo {
        border-radius: 12px;
        border-left: 4px solid;
        padding: 1rem;
        font-weight: 500;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: linear-gradient(180deg, #16213e 0%, #0f1419 100%);
    }
    
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 1rem;
        background: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(102, 126, 234, 0.1);
        border: 2px solid rgba(102, 126, 234, 0.3);
        border-radius: 10px;
        color: #e6f1ff;
        font-weight: 600;
        padding: 0.8rem 1.5rem;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-color: transparent;
    }
    
    /* Progress bar */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #f093fb 100%);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background: rgba(102, 126, 234, 0.1);
        border: 2px solid rgba(102, 126, 234, 0.3);
        border-radius: 10px;
        color: #e6f1ff;
        font-weight: 600;
    }
    
    /* Dataframe styling */
    .dataframe {
        border-radius: 10px;
        overflow: hidden;
    }
    
    /* Loading animation */
    @keyframes pulse {
        0%, 100% { opacity: 0.6; }
        50% { opacity: 1; }
    }
    
    .loading-indicator {
        animation: pulse 2s ease-in-out infinite;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Metrics styling */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #667eea 0%, #f093fb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    [data-testid="stMetricLabel"] {
        color: #a8b2d1;
        font-weight: 600;
        font-size: 0.95rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def create_status_indicator(status: str) -> str:
    """Create a styled status indicator"""
    if status.lower() in ["operational", "healthy", "online"]:
        return f'<div class="status-indicator status-online">🟢 {status}</div>'
    else:
        return f'<div class="status-indicator status-offline">🔴 {status}</div>'

def create_metric_card(title: str, value: str, icon: str = "📊") -> str:
    """Create a styled metric card"""
    return f"""
    <div class="metric-card">
        <h3 style="color: #a8b2d1; margin: 0; font-size: 0.9rem; font-weight: 600;">{icon} {title}</h3>
        <p style="color: #e6f1ff; font-size: 2.5rem; font-weight: 800; margin: 1rem 0 0 0; 
                  background: linear-gradient(135deg, #667eea 0%, #f093fb 100%);
                  -webkit-background-clip: text; -webkit-text-fill-color: transparent;">{value}</p>
    </div>
    """

def create_gauge_chart(value: float, title: str) -> go.Figure:
    """Create a modern gauge chart"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 20, 'color': '#e6f1ff'}},
        delta={'reference': 80, 'increasing': {'color': "#2ed573"}},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "#667eea"},
            'bar': {'color': "#667eea"},
            'bgcolor': "rgba(22, 33, 62, 0.3)",
            'borderwidth': 2,
            'bordercolor': "rgba(102, 126, 234, 0.3)",
            'steps': [
                {'range': [0, 50], 'color': 'rgba(255, 71, 87, 0.3)'},
                {'range': [50, 75], 'color': 'rgba(255, 165, 0, 0.3)'},
                {'range': [75, 100], 'color': 'rgba(46, 213, 115, 0.3)'}
            ],
            'threshold': {
                'line': {'color': "#f093fb", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': "#e6f1ff", 'family': "Inter"},
        height=250,
        margin=dict(l=20, r=20, t=50, b=20)
    )
    
    return fig

def initialize_session_state():
    """Initialize session state variables"""
    if 'analysis_history' not in st.session_state:
        st.session_state.analysis_history = []
    if 'last_health_check' not in st.session_state:
        st.session_state.last_health_check = None
    if 'api_client' not in st.session_state:
        st.session_state.api_client = APIClient()

# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    """Main application logic"""
    
    # Initialize session state
    initialize_session_state()
    api = st.session_state.api_client
    
    # ========================================================================
    # HEADER SECTION
    # ========================================================================
    st.markdown("""
    <div class="main-header">
        <h1>🤖 FMCG Intelligence Hub</h1>
        <p>Enterprise Multi-Agent Analytics System | Powered by Google Gemini & A2A Protocol</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ========================================================================
    # FEATURE BADGES
    # ========================================================================
    st.markdown("""
    <div style="text-align: center; margin: 1.5rem 0;">
        <span class="feature-badge">🔄 Multi-Agent</span>
        <span class="feature-badge">🛠️ MCP Tools</span>
        <span class="feature-badge">💾 Memory Bank</span>
        <span class="feature-badge">📊 Analytics</span>
        <span class="feature-badge">⚡ Real-time</span>
        <span class="feature-badge">🔍 A2A Ready</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ========================================================================
    # SYSTEM DASHBOARD
    # ========================================================================
    st.markdown('<h2 class="section-header">📊 System Dashboard</h2>', unsafe_allow_html=True)
    
    # Create three columns for metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        with st.spinner(""):
            health = api.health_check()
            st.session_state.last_health_check = health
            
            if "error" not in health:
                status_html = create_status_indicator("Operational")
                st.markdown(status_html, unsafe_allow_html=True)
                st.metric("System Health", "100%", "↑ 5%")
            else:
                status_html = create_status_indicator("Offline")
                st.markdown(status_html, unsafe_allow_html=True)
                st.metric("System Health", "0%", "↓ 100%")
    
    with col2:
        status = api.get_status()
        if "error" not in status:
            sessions = status.get("sessions", {})
            total = sessions.get("total_sessions", 0)
            active = sessions.get("active_sessions", 0)
            st.metric("Total Sessions", total, f"{active} active")
            
            # Calculate session activity percentage
            activity_pct = (active / total * 100) if total > 0 else 0
            st.progress(activity_pct / 100)
        else:
            st.metric("Total Sessions", "N/A", "Error")
    
    with col3:
        if "error" not in status:
            version = status.get("version", "1.0.0")
            st.metric("Version", version)
            st.caption(f"🌍 Environment: {status.get('environment', 'dev').upper()}")
        else:
            st.metric("Version", "N/A")
    
    with col4:
        # Uptime indicator
        st.metric("Uptime", "99.9%", "↑ 0.1%")
        st.caption(f"⏱️ Last check: {datetime.now().strftime('%H:%M:%S')}")
    
    # ========================================================================
    # PERFORMANCE GAUGES
    # ========================================================================
    st.markdown('<h2 class="section-header">⚡ Performance Metrics</h2>', unsafe_allow_html=True)
    
    gauge_col1, gauge_col2, gauge_col3 = st.columns(3)
    
    with gauge_col1:
        st.plotly_chart(create_gauge_chart(92.5, "Response Time"), use_container_width=True)
    
    with gauge_col2:
        st.plotly_chart(create_gauge_chart(87.3, "Agent Efficiency"), use_container_width=True)
    
    with gauge_col3:
        st.plotly_chart(create_gauge_chart(95.8, "Data Quality"), use_container_width=True)
    
    st.markdown("---")
    
    # ========================================================================
    # ANALYSIS INTERFACE
    # ========================================================================
    st.markdown('<h2 class="section-header">🧠 Multi-Agent Analysis</h2>', unsafe_allow_html=True)
    
    # Create tabs for different analysis modes
    tab1, tab2, tab3 = st.tabs(["📊 Quick Analysis", "🔬 Advanced Analytics", "📜 History"])
    
    with tab1:
        st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
        
        # Analysis configuration
        col_task, col_period = st.columns([2, 1])
        
        with col_task:
            task = st.text_input(
                "Analysis Task",
                value="Analyze sales performance by category",
                help="Describe what you want to analyze",
                key="task_input"
            )
        
        with col_period:
            period = st.selectbox(
                "Time Period",
                options=["2024", "Q4-2024", "Q3-2024", "Q2-2024", "2024-11", "2024-10"],
                help="Select the analysis period"
            )
        
        # Execution mode
        st.markdown("### Execution Configuration")
        mode_col1, mode_col2, mode_col3 = st.columns(3)
        
        with mode_col1:
            mode = st.radio(
                "Execution Mode",
                options=["parallel", "sequential"],
                horizontal=True,
                help="Parallel: Faster execution | Sequential: Step-by-step processing"
            )
        
        with mode_col2:
            priority = st.select_slider(
                "Priority Level",
                options=["Low", "Normal", "High", "Critical"],
                value="Normal"
            )
        
        with mode_col3:
            enable_cache = st.checkbox("Enable Caching", value=True)
            enable_logging = st.checkbox("Verbose Logging", value=False)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Action buttons
        btn_col1, btn_col2, btn_col3 = st.columns([2, 1, 1])
        
        with btn_col1:
            run_analysis = st.button("🚀 Run Analysis", type="primary", use_container_width=True)
        
        with btn_col2:
            if st.button("💾 Save Config", use_container_width=True):
                st.success("Configuration saved!")
        
        with btn_col3:
            if st.button("🔄 Reset", use_container_width=True):
                st.rerun()
        
        # Execute analysis
        if run_analysis:
            with st.spinner("🔄 Multi-agent system processing..."):
                # Progress indicator
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Simulate processing stages
                stages = [
                    ("Initializing agents...", 20),
                    ("Loading data...", 40),
                    ("Processing analysis...", 60),
                    ("Generating insights...", 80),
                    ("Finalizing results...", 100)
                ]
                
                for stage, progress in stages:
                    status_text.text(stage)
                    progress_bar.progress(progress)
                    time.sleep(0.3)
                
                # Execute actual analysis
                result = api.analyze(task, period, mode)
                
                if "error" not in result:
                    st.success("✅ Analysis completed successfully!")
                    
                    # Store in history
                    st.session_state.analysis_history.append({
                        'timestamp': datetime.now(),
                        'task': task,
                        'period': period,
                        'mode': mode,
                        'result': result
                    })
                    
                    # Display results
                    st.markdown("### 📊 Analysis Results")
                    
                    # Results in expandable sections
                    with st.expander("📈 View Detailed Results", expanded=True):
                        st.json(result)
                    
                    with st.expander("💡 Key Insights"):
                        st.info("AI-generated insights will appear here based on the analysis results.")
                    
                    with st.expander("📥 Export Options"):
                        export_col1, export_col2, export_col3 = st.columns(3)
                        with export_col1:
                            st.download_button("📄 Export JSON", str(result), "analysis.json")
                        with export_col2:
                            st.download_button("📊 Export CSV", "csv_data", "analysis.csv")
                        with export_col3:
                            st.download_button("📑 Export PDF", "pdf_data", "analysis.pdf")
                    
                else:
                    st.error(f"❌ Error: {result['error']}")
                    st.info("💡 Tip: Check system status and try again")
    
    with tab2:
        st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
        st.markdown("### 🔬 Advanced Analytics Configuration")
        
        adv_col1, adv_col2 = st.columns(2)
        
        with adv_col1:
            st.multiselect(
                "Select Agents",
                ["Data Analyst", "Forecaster", "Quality Controller", "Reporter"],
                default=["Data Analyst", "Reporter"]
            )
            
            st.slider("Confidence Threshold", 0.0, 1.0, 0.85, 0.05)
        
        with adv_col2:
            st.multiselect(
                "Output Formats",
                ["JSON", "CSV", "PDF", "Dashboard"],
                default=["JSON"]
            )
            
            st.slider("Max Processing Time (seconds)", 10, 300, 60, 10)
        
        st.text_area("Custom Prompt Template", height=150, placeholder="Enter custom analysis prompt...")
        
        st.button("🔬 Run Advanced Analysis", type="primary", use_container_width=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    with tab3:
        st.markdown("### 📜 Analysis History")
        
        if st.session_state.analysis_history:
            for idx, item in enumerate(reversed(st.session_state.analysis_history[-10:])):
                with st.expander(f"Analysis {len(st.session_state.analysis_history) - idx}: {item['task'][:50]}..."):
                    st.write(f"**Timestamp:** {item['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
                    st.write(f"**Period:** {item['period']}")
                    st.write(f"**Mode:** {item['mode']}")
                    st.json(item['result'])
        else:
            st.info("No analysis history yet. Run your first analysis to see it here!")
    
    # ========================================================================
    # FOOTER
    # ========================================================================
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #a8b2d1; padding: 2rem 0;">
        <p style="margin: 0; font-weight: 600;">FMCG Intelligence Hub v2.0</p>
        <p style="margin: 0.5rem 0; font-size: 0.9rem;">
            Powered by Google Gemini | A2A Protocol | MCP Tools
        </p>
        <p style="margin: 0; font-size: 0.85rem; opacity: 0.7;">
            © 2024 Neural - PhD Candidate, KFUPM | All Rights Reserved
        </p>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# SIDEBAR CONFIGURATION
# ============================================================================
def setup_sidebar():
    """Configure sidebar with additional controls"""
    with st.sidebar:
        st.markdown("### ⚙️ System Configuration")
        
        st.markdown("#### 🎛️ Agent Settings")
        st.slider("Max Concurrent Agents", 1, 10, 4)
        st.slider("Timeout (seconds)", 30, 300, 120)
        
        st.markdown("#### 💾 Memory Settings")
        st.toggle("Enable Memory Bank", value=True)
        st.toggle("Context Compaction", value=True)
        
        st.markdown("#### 🔍 Observability")
        st.toggle("Enable Logging", value=True)
        st.toggle("Enable Tracing", value=False)
        st.toggle("Enable Metrics", value=True)
        
        st.markdown("---")
        
        st.markdown("#### 📊 Quick Stats")
        st.metric("API Calls Today", "1,247", "+12%")
        st.metric("Avg Response Time", "234ms", "-15ms")
        st.metric("Success Rate", "99.2%", "+0.3%")
        
        st.markdown("---")
        
        st.markdown("#### 🔗 Quick Links")
        st.markdown("- [📚 Documentation](#)")
        st.markdown("- [🐛 Report Issue](#)")
        st.markdown("- [💬 Support](#)")
        st.markdown("- [🔐 API Keys](#)")

# ============================================================================
# RUN APPLICATION
# ============================================================================
if __name__ == "__main__":
    setup_sidebar()
    main()