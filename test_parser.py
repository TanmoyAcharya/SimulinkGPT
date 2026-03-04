"""Test script for SimulinkGPT components."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("=== Testing SimulinkGPT Components ===\n")

# Test 1: Import all modules
print("1. Testing imports...")
try:
    from simulink_parser.parser import SimulinkParser
    from simulink_parser.models import SimulinkBlock, SimulinkSignal, SimulinkModel
    print("   [OK] Parser modules imported successfully")
except Exception as e:
    print(f"   [FAIL] Failed to import parser: {e}")
    sys.exit(1)

try:
    from knowledge_base.manager import KnowledgeBaseManager
    from knowledge_base.manager import KnowledgeDocument
    print("   [OK] Knowledge base modules imported successfully")
except Exception as e:
    print(f"   [FAIL] Failed to import knowledge base: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from llm.inference import LLMInference
    from llm.prompts import get_template, detect_task_type
    print("   [OK] LLM modules imported successfully")
except Exception as e:
    print(f"   [FAIL] Failed to import LLM modules: {e}")
    sys.exit(1)

try:
    from simulink_gpt import SimulinkGPT
    print("   [OK] Main app imported successfully")
except Exception as e:
    print(f"   [FAIL] Failed to import main app: {e}")
    sys.exit(1)

# Test 2: Create a mock Simulink model
print("\n2. Testing model creation...")
try:
    # Create sample blocks
    blocks = [
        SimulinkBlock(
            name="Constant",
            block_type="Constant",
            path="model/Constant",
            parameters={"Value": "1"},
            ports={"outputs": ["1"]}
        ),
        SimulinkBlock(
            name="Gain",
            block_type="Gain",
            path="model/Gain",
            parameters={"Gain": "2"},
            ports={"inputs": ["1"], "outputs": ["1"]}
        ),
        SimulinkBlock(
            name="Scope",
            block_type="Scope",
            path="model/Scope",
            ports={"inputs": ["1"]}
        )
    ]
    
    # Create sample signals
    signals = [
        SimulinkSignal(
            name="signal1",
            source_block="model/Constant",
            source_port="1",
            target_block="model/Gain",
            target_port="1"
        ),
        SimulinkSignal(
            name="signal2",
            source_block="model/Gain",
            source_port="1",
            target_block="model/Scope",
            target_port="1"
        )
    ]
    
    # Create model
    model = SimulinkModel(
        name="test_model",
        file_path="./test_model.slx",
        blocks=blocks,
        signals=signals,
        subsystems=[],
        configuration={"solver": "ode45"}
    )
    
    print(f"   [OK] Created test model with {len(model.blocks)} blocks and {len(model.signals)} signals")
    
    # Test text summary
    summary = model.to_text_summary()
    print(f"   [OK] Generated model summary ({len(summary)} chars)")
    
except Exception as e:
    print(f"   [FAIL] Failed to create model: {e}")
    sys.exit(1)

# Test 3: Test parser (without actual SLX file)
print("\n3. Testing parser initialization...")
try:
    parser = SimulinkParser()
    print(f"   [OK] Parser initialized (MATLAB available: {parser._matlab_available})")
except Exception as e:
    print(f"   [FAIL] Failed to initialize parser: {e}")

# Test 4: Test knowledge base (without vector store)
print("\n4. Testing knowledge base...")
try:
    # Create a test document
    doc = KnowledgeDocument(
        content="This is a test document about Simulink debugging.",
        source="test.md",
        title="Test Document",
        doc_type="test"
    )
    
    print(f"   [OK] Created test document: {doc.title}")
    
    # Test retrieval fallback
    kb_manager = KnowledgeBaseManager()
    kb_manager.add_document(doc)
    
    results = kb_manager.retrieve("debugging", top_k=1)
    print(f"   [OK] Knowledge base retrieval works (found {len(results)} results)")
    
except Exception as e:
    print(f"   [FAIL] Knowledge base test failed: {e}")

# Test 5: Test prompt templates
print("\n5. Testing prompt templates...")
try:
    template = get_template("debug")
    print(f"   [OK] Got debug template")
    
    task_type = detect_task_type("What errors are in this model?")
    print(f"   [OK] Task detection: '{task_type}'")
    
    task_type = detect_task_type("How can I improve performance?")
    print(f"   [OK] Task detection: '{task_type}'")
    
except Exception as e:
    print(f"   [FAIL] Prompt template test failed: {e}")

# Test 6: Test main application
print("\n6. Testing main application...")
try:
    app = SimulinkGPT()
    print(f"   [OK] SimulinkGPT initialized")
    
    # Initialize components
    app.initialize_parser()
    print(f"   [OK] Parser initialized")
    
    app.initialize_knowledge_base()
    print(f"   [OK] Knowledge base initialized ({len(app.knowledge_base.documents)} docs)")
    
    # Load test model
    app.current_model = model
    app.model_summary = model.to_text_summary()
    print(f"   [OK] Test model loaded into app")
    
    # Test query with fallback (no LLM)
    response = app.query("What issues are in this model?", use_rag=False)
    print(f"   [OK] Query works (response length: {len(response)} chars)")
    print(f"\n   Sample response:\n{response[:300]}...")
    
except Exception as e:
    print(f"   [FAIL] Main app test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n=== All Tests Complete! ===")
