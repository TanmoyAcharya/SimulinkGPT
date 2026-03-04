"""
SimulinkGPT - Web Interface

Streamlit-based web interface for Simulink model analysis.
Simplified version - auto-initializes with transformers backend.
"""

import streamlit as st
import os
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from simulink_gpt import SimulinkGPT
from simulink_parser.parser import SimulinkParser
from knowledge_base.manager import KnowledgeBaseManager
from llm.inference import LLMInference


# Page configuration
st.set_page_config(
    page_title="SimulinkGPT",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session_state():
    """Initialize Streamlit session state."""
    if 'app' not in st.session_state:
        st.session_state.app = None
    if 'model_loaded' not in st.session_state:
        st.session_state.model_loaded = False
    if 'model_info' not in st.session_state:
        st.session_state.model_info = None
    if 'initialized' not in st.session_state:
        st.session_state.initialized = False


def main():
    """Main application function."""
    init_session_state()
    
    # Title and description
    st.title("🔧 SimulinkGPT")
    st.markdown("""
    **Open Source LLM for Simulink MATLAB Model Analysis**
    
    Debug, improve, and get guidelines for your Simulink models using AI.
    """)
    
    # Auto-initialize on first run
    if not st.session_state.initialized:
        with st.spinner("Initializing system..."):
            app = SimulinkGPT()
            app.initialize_parser()
            app.initialize_knowledge_base()
            
            # Use transformers backend by default
            app.config["model"]["backend"] = "transformers"
            app.config["model"]["name"] = "microsoft/Phi-3-mini-4k-instruct"
            app.initialize_llm()
            
            st.session_state.app = app
            st.session_state.initialized = True
        st.success("System initialized!")
    
    # Main content area
    st.header("📂 Load Your Simulink Model")
    
    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a .slx file",
        type=["slx"],
        help="Upload your Simulink model"
    )
    
    if uploaded_file:
        # Save uploaded file temporarily
        temp_path = f"./temp_{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        if st.button("Load Model", type="primary"):
            if st.session_state.app:
                with st.spinner("Loading model..."):
                    if st.session_state.app.load_model(temp_path):
                        st.session_state.model_loaded = True
                        st.session_state.model_info = st.session_state.app.get_model_info()
                        st.success("Model loaded successfully!")
                    else:
                        st.error("Failed to load model")
            else:
                st.warning("System not initialized")
        
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
    
    # Display loaded model info
    if st.session_state.model_loaded and st.session_state.model_info:
        info = st.session_state.model_info
        st.divider()
        st.header("📊 Model Information")
        col1, col2, col3 = st.columns(3)
        col1.metric("Name", info.get('name', 'N/A'))
        col2.metric("Blocks", info.get('block_count', 0))
        col3.metric("Signals", info.get('signal_count', 0))
        
        # Query section
        st.divider()
        st.header("💬 Ask About Your Model")
        
        query = st.text_area(
            "Your question:",
            placeholder="e.g., What issues can you find in this model? How can I improve performance?",
            height=100
        )
        
        # Query type selection
        query_type = st.radio(
            "Query type:",
            ["auto", "debug", "improve", "guidelines"],
            horizontal=True
        )
        
        # Submit button
        if st.button("Analyze", type="primary"):
            if query:
                if st.session_state.app:
                    with st.spinner("Analyzing..."):
                        task_type = None if query_type == "auto" else query_type
                        response = st.session_state.app.query(
                            query,
                            use_rag=True,
                            task_type=task_type
                        )
                        
                        st.markdown("### 📝 Analysis Results:")
                        st.markdown(response)
                else:
                    st.error("System not initialized")
            else:
                st.warning("Please enter a question")
        
        # Model structure display
        with st.expander("📋 View Model Structure"):
            if st.session_state.app and st.session_state.app.current_model:
                st.text(st.session_state.app.model_summary)
        
        # Analysis section
        with st.expander("🔎 View Model Analysis"):
            if st.session_state.app:
                analysis = st.session_state.app.analyze_model()
                st.json(analysis)
    else:
        st.info("Upload a Simulink (.slx) file to get started")


if __name__ == "__main__":
    main()
