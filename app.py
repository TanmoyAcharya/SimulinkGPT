"""
SimulinkGPT - Web Interface

Streamlit-based web interface for Simulink model analysis.
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


def main():
    """Main application function."""
    init_session_state()
    
    # Title and description
    st.title("🔧 SimulinkGPT")
    st.markdown("""
    **Open Source LLM for Simulink MATLAB Model Analysis**
    
    Debug, improve, and get guidelines for your Simulink models using AI.
    """)
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Model backend selection
        backend = st.selectbox(
            "LLM Backend",
            ["transformers", "llama.cpp", "openai"],
            index=0,
            help="Choose the inference backend"
        )
        
        # Model selection
        if backend == "llama.cpp":
            model_path = st.text_input(
                "Model Path (GGUF)",
                value="./models/model-q4_K_M.gguf",
                help="Path to GGUF model file"
            )
        else:
            model_path = st.text_input(
                "Model Name",
                value="microsoft/Phi-3-mini-4k-instruct",
                help="HuggingFace model name"
            )
        
        # Initialize button
        if st.button("🚀 Initialize System", type="primary"):
            with st.spinner("Initializing..."):
                app = SimulinkGPT()
                
                # Initialize components
                app.initialize_parser()
                app.initialize_knowledge_base()
                
                # Try to initialize LLM
                app.config["model"]["backend"] = backend
                app.config["model"]["model_path"] = model_path
                app.initialize_llm()
                
                st.session_state.app = app
                st.success("System initialized!")
        
        st.divider()
        
        # Model loading section
        st.header("📂 Load Model")
        
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
            
            if st.button("📋 Load Model", type="primary"):
                if st.session_state.app:
                    with st.spinner("Loading model..."):
                        if st.session_state.app.load_model(temp_path):
                            st.session_state.model_loaded = True
                            st.session_state.model_info = st.session_state.app.get_model_info()
                            st.success("Model loaded successfully!")
                        else:
                            st.error("Failed to load model")
                else:
                    st.warning("Please initialize the system first")
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        # Display loaded model info
        if st.session_state.model_loaded and st.session_state.model_info:
            st.divider()
            st.header("📊 Model Info")
            info = st.session_state.model_info
            st.write(f"**Name:** {info.get('name', 'N/A')}")
            st.write(f"**Blocks:** {info.get('block_count', 0)}")
            st.write(f"**Signals:** {info.get('signal_count', 0)}")
            st.write(f"**Subsystems:** {info.get('subsystem_count', 0)}")
    
    # Main content area
    if not st.session_state.model_loaded:
        st.info("👈 Please load a Simulink model to get started")
        
        # Show demo/example
        with st.expander("See example usage"):
            st.markdown("""
            ### Example Workflow:
            
            1. **Initialize System**: Click "Initialize System" in the sidebar
            2. **Load Model**: Upload your .slx file
            3. **Ask Questions**: Query about debugging, improvements, or guidelines
            
            ### Example Queries:
            - "What are the potential issues in this model?"
            - "How can I improve the simulation performance?"
            - "What are the best practices for this type of model?"
            """)
    else:
        # Query input
        st.header("💬 Ask about your model")
        
        query = st.text_area(
            "Your question:",
            placeholder="e.g., What issues can you find in this model?",
            height=100
        )
        
        # Query type selection
        query_type = st.radio(
            "Query type:",
            ["auto", "debug", "improve", "guidelines"],
            horizontal=True,
            help="Auto-detects or explicitly sets the query type"
        )
        
        # Submit button
        if st.button("🔍 Analyze", type="primary"):
            if query:
                if st.session_state.app:
                    with st.spinner("Analyzing..."):
                        # Determine task type
                        task_type = None if query_type == "auto" else query_type
                        
                        # Get response
                        response = st.session_state.app.query(
                            query,
                            use_rag=True,
                            task_type=task_type
                        )
                        
                        # Display response
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


if __name__ == "__main__":
    main()
