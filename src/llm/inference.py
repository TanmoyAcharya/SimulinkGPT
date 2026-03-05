"""
LLM Inference Module

Handles loading and running language model inference.
Supports multiple backends: llama.cpp, transformers, and OpenAI-compatible APIs.
"""

import os
import logging
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class LLMInference:
    """
    Language Model inference handler.
    
    Supports multiple inference backends:
    - llama.cpp (GGUF models) - recommended for local CPU/GPU
    - transformers (HuggingFace models)
    - OpenAI-compatible API
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        model_name: str = "meta-llama/Llama-3.2-1B-Instruct",
        backend: str = "llama.cpp",  # Options: llama.cpp, transformers, openai
        quantization: str = "q4_K_M",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        top_p: float = 0.9,
        top_k: int = 40,
        context_window: int = 4096,
        n_gpu_layers: int = 0,  # For llama.cpp GPU acceleration
        verbose: bool = False
    ):
        """
        Initialize the LLM inference engine.
        
        Args:
            model_path: Path to local model file (GGUF for llama.cpp)
            model_name: HuggingFace model name
            backend: Inference backend to use
            quantization: Quantization method (for GGUF)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter
            top_k: Top-k sampling parameter
            context_window: Maximum context length
            n_gpu_layers: Number of layers to offload to GPU
            verbose: Enable verbose logging
        """
        self.model_path = model_path
        self.model_name = model_name
        self.backend = backend
        self.quantization = quantization
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.top_k = top_k
        self.context_window = context_window
        self.n_gpu_layers = n_gpu_layers
        self.verbose = verbose
        
        self.model = None
        self.tokenizer = None
        self._initialized = False
    
    def initialize(self) -> bool:
        """
        Initialize the model and tokenizer.
        
        Returns:
            True if initialization successful
        """
        if self._initialized:
            return True
        
        try:
            if self.backend == "llama.cpp":
                return self._init_llama_cpp()
            elif self.backend == "transformers":
                return self._init_transformers()
            elif self.backend == "openai":
                return self._init_openai()
            else:
                logger.error(f"Unknown backend: {self.backend}")
                return False
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            return False
    
    def _init_llama_cpp(self) -> bool:
        """Initialize using llama.cpp (GGUF models)."""
        try:
            from llama_cpp import Llama
            
            # Determine model path
            model_file = self._get_model_file()
            
            if not os.path.exists(model_file):
                logger.warning(f"Model not found: {model_file}")
                logger.info("Please download a GGUF model first")
                return False
            
            # Initialize model
            self.model = Llama(
                model_path=model_file,
                n_ctx=self.context_window,
                n_gpu_layers=self.n_gpu_layers,
                n_threads=4,
                verbose=self.verbose
            )
            
            self._initialized = True
            logger.info(f"Initialized llama.cpp model: {model_file}")
            return True
            
        except ImportError:
            logger.error("llama-cpp-python not installed. Run: pip install llama-cpp-python")
            return False
        except Exception as e:
            logger.error(f"Error initializing llama.cpp: {e}")
            return False
    
    def _init_transformers(self) -> bool:
        """Initialize using HuggingFace transformers."""
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            logger.info(f"Loading model: {self.model_name}")
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            # Determine device - use CPU for stability
            device = "cpu"
            
            # Load model - use newer API without device_map for CPU-only
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=torch.float16,
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            self.model.to(device)
            
            self._initialized = True
            logger.info(f"Initialized transformers model on {device}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing transformers: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _init_openai(self) -> bool:
        """Initialize for OpenAI-compatible API."""
        # No model loading needed, will use API directly
        self._initialized = True
        logger.info("Initialized OpenAI-compatible API backend")
        return True
    
    def _get_model_file(self) -> str:
        """Get the path to the model file."""
        if self.model_path:
            return self.model_path
        
        # Try to find in models directory
        models_dir = "./models"
        if os.path.exists(models_dir):
            for f in os.listdir(models_dir):
                if f.endswith(".gguf"):
                    return os.path.join(models_dir, f)
        
        return os.path.join(models_dir, f"model-{self.quantization}.gguf")
    
    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        stop: Optional[List[str]] = None,
        **kwargs
    ) -> str:
        """
        Generate text from prompt.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate (overrides default)
            temperature: Sampling temperature (overrides default)
            top_p: Nucleus sampling (overrides default)
            top_k: Top-k sampling (overrides default)
            stop: Stop sequences
            **kwargs: Additional generation parameters
            
        Returns:
            Generated text
        """
        if not self._initialized:
            if not self.initialize():
                return "Error: Failed to initialize model"
        
        # Use defaults if not provided
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature
        top_p = top_p if top_p is not None else self.top_p
        top_k = top_k if top_k is not None else self.top_k
        stop = stop or []
        
        try:
            if self.backend == "llama.cpp":
                return self._generate_llama(prompt, max_tokens, temperature, top_p, top_k, stop)
            elif self.backend == "transformers":
                return self._generate_transformers(prompt, max_tokens, temperature, top_p)
            elif self.backend == "openai":
                return self._generate_openai(prompt, max_tokens, temperature, top_p)
            else:
                return "Error: Unknown backend"
        except Exception as e:
            logger.error(f"Generation error: {e}")
            import traceback
            traceback.print_exc()
            return f"Error during generation: {str(e)}"
    
    def _generate_llama(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
        top_k: int,
        stop: List[str]
    ) -> str:
        """Generate using llama.cpp."""
        response = self.model(
            prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            stop=stop,
            echo=False
        )
        
        return response['choices'][0]['text'].strip()
    
    def _generate_transformers(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float
    ) -> str:
        """Generate using transformers."""
        import torch
        
        # Prepare input
        inputs = self.tokenizer(prompt, return_tensors="pt")
        
        # Move to CPU since we loaded on CPU
        inputs = {k: v for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        # Decode only the new tokens
        generated = outputs[0][inputs.input_ids.shape[1]:]
        return self.tokenizer.decode(generated, skip_special_tokens=True).strip()
    
    def _generate_openai(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float
    ) -> str:
        """Generate using OpenAI-compatible API."""
        import requests
        
        api_key = os.getenv("OPENAI_API_KEY", "")
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p
        }
        
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"API Error: {response.status_code} - {response.text}"
    
    def is_initialized(self) -> bool:
        """Check if model is initialized."""
        return self._initialized
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded model."""
        return {
            "backend": self.backend,
            "model_name": self.model_name,
            "model_path": self.model_path,
            "quantization": self.quantization,
            "max_tokens": self.max_tokens,
            "context_window": self.context_window,
            "initialized": self._initialized
        }


def create_inference_engine(
    config: Dict[str, Any]
) -> LLMInference:
    """
    Create an LLM inference engine from configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        LLMInference instance
    """
    return LLMInference(
        model_path=config.get("model_path"),
        model_name=config.get("name", "meta-llama/Llama-3.2-1B-Instruct"),
        backend=config.get("backend", "llama.cpp"),
        quantization=config.get("quantization", "q4_K_M"),
        max_tokens=config.get("max_tokens", 2048),
        temperature=config.get("temperature", 0.7),
        top_p=config.get("top_p", 0.9),
        top_k=config.get("top_k", 40),
        context_window=config.get("context_window", 4096)
    )
