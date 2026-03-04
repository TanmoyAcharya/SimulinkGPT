"""
SimulinkGPT - Main Application

Integrates all components: parser, knowledge base, and LLM inference.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import modules
from simulink_parser.parser import SimulinkParser
from simulink_parser.models import SimulinkModel
from knowledge_base.manager import KnowledgeBaseManager
from llm.inference import LLMInference, create_inference_engine
from llm.prompts import get_template, detect_task_type


class SimulinkGPT:
    """
    Main application class for SimulinkGPT.
    
    Integrates:
    - Simulink model parsing
    - RAG knowledge base
    - LLM inference
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize SimulinkGPT.
        
        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        
        # Initialize components
        self.parser: Optional[SimulinkParser] = None
        self.knowledge_base: Optional[KnowledgeBaseManager] = None
        self.llm: Optional[LLMInference] = None
        
        # Current model data
        self.current_model: Optional[SimulinkModel] = None
        self.model_summary: str = ""
        
        logger.info("SimulinkGPT initialized")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            import yaml
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from {config_path}")
            return config
        except ImportError:
            logger.warning("PyYAML not available, using defaults")
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
        
        return {
            "model": {
                "name": "meta-llama/Llama-3.2-1B-Instruct",
                "max_tokens": 2048,
                "temperature": 0.7
            },
            "rag": {
                "knowledge_base_path": "./knowledge_base",
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2"
            },
            "simulink": {
                "use_xml_parsing": True
            }
        }
    
    def initialize_parser(self, matlab_path: Optional[str] = None) -> bool:
        """Initialize the Simulink parser."""
        try:
            matlab_path = matlab_path or self.config.get("simulink", {}).get("matlab_path")
            self.parser = SimulinkParser(matlab_path=matlab_path)
            logger.info("Simulink parser initialized")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize parser: {e}")
            return False
    
    def initialize_knowledge_base(self) -> bool:
        """Initialize the knowledge base."""
        try:
            kb_config = self.config.get("rag", {})
            self.knowledge_base = KnowledgeBaseManager(
                vector_store_path=kb_config.get("knowledge_base_path", "./knowledge_base/vector_store"),
                embedding_model=kb_config.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")
            )
            
            # Load documents
            kb_path = kb_config.get("knowledge_base_path", "./knowledge_base")
            if os.path.exists(kb_path):
                # Try to load existing vector store first
                doc_count = self.knowledge_base.load()
                if doc_count == 0:
                    # Load from markdown files
                    doc_count = self.knowledge_base.load_documents_from_directory(kb_path)
                    if doc_count > 0:
                        self.knowledge_base.save()
            
            logger.info(f"Knowledge base initialized with {len(self.knowledge_base.documents)} documents")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize knowledge base: {e}")
            return False
    
    def initialize_llm(self) -> bool:
        """Initialize the LLM inference engine."""
        try:
            model_config = self.config.get("model", {})
            self.llm = create_inference_engine(model_config)
            
            # Try to initialize
            if not self.llm.initialize():
                logger.warning("LLM initialization failed - will use fallback mode")
                return False
            
            logger.info("LLM initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            return False
    
    def load_model(self, slx_file: str) -> bool:
        """
        Load and parse a Simulink model.
        
        Args:
            slx_file: Path to .slx file
            
        Returns:
            True if successful
        """
        if not self.parser:
            self.initialize_parser()
        
        try:
            logger.info(f"Loading model: {slx_file}")
            self.current_model = self.parser.parse(slx_file)
            self.model_summary = self.current_model.to_text_summary()
            
            logger.info(f"Loaded model with {len(self.current_model.blocks)} blocks")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False
    
    def query(
        self,
        user_query: str,
        use_rag: bool = True,
        task_type: Optional[str] = None
    ) -> str:
        """
        Process a user query about the loaded model.
        
        Args:
            user_query: The user's question
            use_rag: Whether to use RAG context
            task_type: Specific task type (debug/improve/guidelines/general)
            
        Returns:
            Generated response
        """
        # Validate we have a model loaded
        if not self.current_model:
            return "Error: No Simulink model loaded. Please load a model first."
        
        # Detect task type if not specified
        if not task_type:
            task_type = detect_task_type(user_query)
        
        # Get the appropriate prompt template
        template = get_template(task_type)
        
        # Build context from RAG
        context = ""
        if use_rag and self.knowledge_base:
            context = self.knowledge_base.build_context_from_retrieval(
                query=user_query,
                top_k=5,
                max_context_length=1500
            )
        
        # Format the prompt
        prompt = template.format(
            model_summary=self.model_summary,
            query=user_query,
            context=context
        )
        
        # Generate response
        if self.llm and self.llm.is_initialized():
            response = self.llm.generate(prompt)
        else:
            response = self._fallback_response(user_query, context, task_type)
        
        return response
    
    def _fallback_response(
        self,
        query: str,
        context: str,
        task_type: str
    ) -> str:
        """Generate a fallback response without LLM."""
        response_parts = [
            "## Response (Fallback Mode - LLM Not Available)",
            "",
            f"**Task Type:** {task_type}",
            "",
            "### Model Summary:",
            self.model_summary[:500] + "..." if len(self.model_summary) > 500 else self.model_summary,
            "",
            "### Knowledge Base Context:",
            context[:500] + "..." if len(context) > 500 else context,
            "",
            "### Note:",
            "The LLM is not currently available. To enable full responses:",
            "1. Download a GGUF model file to the ./models directory",
            "2. Or configure an OpenAI-compatible API",
            "3. Or use the transformers backend with a HuggingFace model"
        ]
        
        return "\n".join(response_parts)
    
    def analyze_model(self) -> Dict[str, Any]:
        """
        Perform basic analysis on the loaded model.
        
        Returns:
            Analysis results
        """
        if not self.current_model:
            return {"error": "No model loaded"}
        
        return self.parser.analyze_model_structure(self.current_model)
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model."""
        if not self.current_model:
            return {"error": "No model loaded"}
        
        return {
            "name": self.current_model.name,
            "file_path": self.current_model.file_path,
            "block_count": len(self.current_model.blocks),
            "signal_count": len(self.current_model.signals),
            "subsystem_count": len(self.current_model.subsystems),
            "configuration": self.current_model.configuration
        }
    
    def export_model_json(self, output_path: str) -> bool:
        """Export the current model to JSON."""
        if not self.current_model:
            return False
        
        try:
            self.parser.save_json(self.current_model, output_path)
            return True
        except Exception as e:
            logger.error(f"Failed to export model: {e}")
            return False


def main():
    """Main entry point for CLI usage."""
    parser = argparse.ArgumentParser(description="SimulinkGPT - LLM for Simulink Analysis")
    parser.add_argument("command", choices=["load", "query", "analyze", "info"],
                        help="Command to execute")
    parser.add_argument("--model", "-m", type=str, help="Path to .slx file")
    parser.add_argument("--query", "-q", type=str, help="Query to process")
    parser.add_argument("--config", "-c", type=str, default="config.yaml",
                        help="Path to config file")
    
    args = parser.parse_args()
    
    # Initialize application
    app = SimulinkGPT(config_path=args.config)
    
    if args.command == "load":
        if not args.model:
            print("Error: --model required for load command")
            sys.exit(1)
        
        app.initialize_parser()
        if app.load_model(args.model):
            print(f"Successfully loaded: {args.model}")
            print(app.get_model_info())
        else:
            print("Failed to load model")
            sys.exit(1)
    
    elif args.command == "query":
        if not args.model or not args.query:
            print("Error: --model and --query required for query command")
            sys.exit(1)
        
        # Initialize all components
        app.initialize_parser()
        app.initialize_knowledge_base()
        app.initialize_llm()
        
        # Load model and query
        if not app.load_model(args.model):
            print("Failed to load model")
            sys.exit(1)
        
        response = app.query(args.query)
        print(response)
    
    elif args.command == "analyze":
        if not args.model:
            print("Error: --model required for analyze command")
            sys.exit(1)
        
        app.initialize_parser()
        if app.load_model(args.model):
            analysis = app.analyze_model()
            print(json.dumps(analysis, indent=2))
        else:
            print("Failed to load model")
            sys.exit(1)
    
    elif args.command == "info":
        if not args.model:
            print("Error: --model required for info command")
            sys.exit(1)
        
        app.initialize_parser()
        if app.load_model(args.model):
            info = app.get_model_info()
            print(json.dumps(info, indent=2))
        else:
            print("Failed to load model")
            sys.exit(1)


if __name__ == "__main__":
    main()
