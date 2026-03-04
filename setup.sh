#!/bin/bash
# Setup script for SimulinkGPT

echo "=== SimulinkGPT Setup ==="
echo ""

# Check Python version
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate  # Linux/Mac
# For Windows, use: venv\Scripts\activate

# Install requirements
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create models directory
if [ ! -d "models" ]; then
    mkdir models
fi

# Create logs directory
if [ ! -d "logs" ]; then
    mkdir logs
fi

echo ""
echo "=== Setup Complete! ==="
echo ""
echo "Next steps:"
echo "1. Download a GGUF model to ./models/"
echo "   Recommended: Qwen2.5-0.5B-Instruct-Q4_K_M.gguf"
echo ""
echo "2. Run the web interface:"
echo "   streamlit run app.py"
echo ""
echo "3. Or use CLI:"
echo "   python -m src.simulink_gpt load --model your_model.slx"
echo ""
