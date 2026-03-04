# SimulinkGPT 🛠️

<p align="center">
  <strong>Open Source LLM for Simulink MATLAB Model Analysis</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#architecture">Architecture</a> •
  <a href="#installation">Installation</a> •
  <a href="#usage">Usage</a> •
  <a href="#configuration">Configuration</a> •
  <a href="#roadmap">Roadmap</a>
</p>

---

## ✅ Is It Possible?

**YES!** Building an LLM-powered tool for Simulink model analysis is absolutely achievable. This project provides a complete, open-source implementation using:

- **RAG (Retrieval-Augmented Generation)** for domain-specific knowledge
- **Model parsing** to understand Simulink model structure
- **Multiple LLM backends** (llama.cpp, transformers, OpenAI API)
- Works on **consumer GPUs** (4-8GB VRAM)

---

## Features

### 🔍 Model Analysis
- Parse Simulink (.slx) files and extract block/signal structure
- Identify potential issues and errors
- Analyze model configuration and solver settings

### 💡 Intelligent Assistance
- **Debug**: Find and explain issues in your models
- **Improve**: Get suggestions for performance optimization
- **Guidelines**: Best practices for Simulink modeling

### 🌐 Multiple Interfaces
- **Web UI**: Streamlit-based interactive interface
- **CLI**: Command-line tool for automation
- **API**: Programmatic access for integration

### 🔧 Flexible Architecture
- Support for multiple LLM backends
- Extensible knowledge base
- Customizable prompts

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface                          │
│              (Streamlit / CLI / API)                        │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                    SimulinkGPT Core                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │   Parser    │  │  RAG/KB     │  │    LLM Engine   │    │
│  │  (.slx)     │  │  (ChromaDB) │  │  (llama.cpp)   │    │
│  └─────────────┘  └─────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### Components

| Component | Description |
|-----------|-------------|
| **Parser** | Extracts structure from .slx files (XML parsing or MATLAB Engine) |
| **Knowledge Base** | RAG system with Simulink documentation & best practices |
| **LLM Engine** | Multiple backends: llama.cpp, transformers, OpenAI |

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/SimulinkGPT.git
cd SimulinkGPT
```

### 2. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install requirements
pip install -r requirements.txt
```

### 3. Download an LLM Model

#### Option A: GGUF Models (Recommended for CPU/Consumer GPU)
```bash
# Create models directory
mkdir models
cd models

# Download a small model (e.g., Qwen2.5-0.5B)
# Visit https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF
# Download the Q4_K_M.gguf file
```

#### Option B: HuggingFace Transformers
```python
# The app will automatically download on first use
# Make sure you have enough disk space (2-4GB)
```

### 4. (Optional) MATLAB Integration

For full model parsing, install MATLAB Engine for Python:
```bash
# From MATLAB installation directory
cd matlabroot/extern/engines/python
python setup.py install
```

---

## Usage

### Web Interface

```bash
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

### Command Line Interface

```bash
# Load and analyze a model
python -m src.simulink_gpt load --model your_model.slx

# Query about a model
python -m src.simulink_gpt query --model your_model.slx --query "What issues are in this model?"

# Get model info
python -m src.simulink_gpt info --model your_model.slx
```

### Programmatic Usage

```python
from src.simulink_gpt import SimulinkGPT

# Initialize
app = SimulinkGPT()
app.initialize_parser()
app.initialize_knowledge_base()
app.initialize_llm()

# Load model
app.load_model("your_model.slx")

# Query
response = app.query("What can be improved in this model?")
print(response)
```

---

## Configuration

Edit `config.yaml` to customize:

```yaml
model:
  name: "meta-llama/Llama-3.2-1B-Instruct"
  backend: "llama.cpp"
  quantization: "q4_K_M"
  max_tokens: 2048

rag:
  vector_db: "chroma"
  embedding_model: "sentence-transformers/all-MiniLM-L6-v2"

simulink:
  use_xml_parsing: true
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `model.name` | HuggingFace model name | Llama-3.2-1B |
| `model.backend` | Inference backend | llama.cpp |
| `model.quantization` | GGUF quantization | q4_K_M |
| `rag.vector_db` | Vector database | chroma |
| `simulink.use_xml_parsing` | Parse without MATLAB | true |

---

## Knowledge Base

The knowledge base includes:

- **Debugging Guide**: Common Simulink errors and solutions
- **Best Practices**: Model architecture, configuration, optimization
- **Block Reference**: Common block usage guidelines

### Adding Custom Knowledge

Add markdown files to `knowledge_base/`:
```bash
echo "# My Custom Topic" > knowledge_base/custom.md
# The system will automatically index new documents
```

---

## Troubleshooting

### "Model not found" error
- Download a GGUF model and place in `./models/`
- Or change `backend` to "transformers" for HuggingFace download

### "No NVIDIA GPU found"
- The system works on CPU, though slower
- Or use quantized GGUF models (q4_0, q4_K_M)

### MATLAB Engine errors
- Use XML parsing mode (no MATLAB required)
- Set `simulink.use_xml_parsing: true` in config

---

## Roadmap

- [ ] Add more Simulink block type handlers
- [ ] Implement algebraic loop detection
- [ ] Add code generation analysis
- [ ] Support for Stateflow models
- [ ] Fine-tuned Simulink-specific model
- [ ] Plugin system for custom analyses

---

## Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

## Acknowledgments

- [llama.cpp](https://github.com/ggerganov/llama.cpp) - Efficient inference
- [LangChain](https://github.com/hwchase17/langchain) - RAG framework
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [MATLAB](https://www.mathworks.com/) - Simulink
