#!/usr/bin/env python3
"""Debug Yggdrasil router integration issues"""

import sys
import os
import traceback
import logging
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_yggdrasil_imports():
    """Test if Yggdrasil modules can be imported"""
    print("=" * 60)
    print("Testing Yggdrasil Imports")
    print("=" * 60)
    
    modules_to_test = [
        'yggdrasil.router',
        'yggdrasil.integration.norse_saga',  # This is the cognition module
        'yggdrasil.config',
        'yggdrasil.ravens'
    ]
    
    all_imports_ok = True
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"✓ {module_name}: Import successful")
        except ImportError as e:
            print(f"❌ {module_name}: Import failed - {e}")
            all_imports_ok = False
        except Exception as e:
            print(f"⚠ {module_name}: Import error - {e}")
            all_imports_ok = False
    
    return all_imports_ok

def test_router_creation():
    """Test if router can be created"""
    print("\n" + "=" * 60)
    print("Testing Router Creation")
    print("=" * 60)
    
    try:
        from yggdrasil.router import create_yggdrasil_router, AICallType
        
        # Create a simple LLM callable for testing
        def test_llm_callable(system: str, prompt: str) -> str:
            return f"Test response to: {prompt[:50]}..."
        
        # Try to create router
        router = create_yggdrasil_router(
            llm_callable=test_llm_callable,
            data_path="data",
            comprehensive_logger=None,
            wyrd_system=None,
            enhanced_memory=None,
            prompt_builder=None,
            yggdrasil_cognition=None
        )
        
        print(f"✓ Router created successfully: {router}")
        
        # Test router methods
        if hasattr(router, 'route_call'):
            print("✓ Router has route_call method")
        else:
            print("❌ Router missing route_call method")
            
        if hasattr(router, 'route'):
            print("✓ Router has route method")
        else:
            print("❌ Router missing route method")
            
        return True
        
    except Exception as e:
        print(f"❌ Router creation failed: {e}")
        traceback.print_exc()
        return False

def test_router_functionality():
    """Test router functionality"""
    print("\n" + "=" * 60)
    print("Testing Router Functionality")
    print("=" * 60)
    
    try:
        from yggdrasil.router import create_yggdrasil_router, AICallType
        
        # Create a simple LLM callable
        def test_llm_callable(system: str, prompt: str) -> str:
            return f"Test AI response for: {prompt}"
        
        # Create router
        router = create_yggdrasil_router(
            llm_callable=test_llm_callable,
            data_path="data",
            comprehensive_logger=None,
            wyrd_system=None,
            enhanced_memory=None,
            prompt_builder=None,
            yggdrasil_cognition=None
        )
        
        # Test route_call method
        print("Testing route_call method...")
        try:
            result = router.route_call(
                call_type=AICallType.NARRATION,
                prompt="Test prompt",
                game_state={},
                involved_npcs=[],
                system_prompt="Test system prompt"
            )
            print(f"✓ route_call returned: {type(result)}")
            if hasattr(result, 'content'):
                print(f"  Content: {result.content[:100]}...")
            else:
                print(f"  Result: {result}")
        except Exception as e:
            print(f"❌ route_call failed: {e}")
            traceback.print_exc()
            return False
        
        # Test route method (if it exists)
        if hasattr(router, 'route'):
            print("\nTesting route method...")
            try:
                from dataclasses import dataclass
                from typing import List
                
                # Create simple message class
                @dataclass
                class Message:
                    role: str
                    content: str
                
                messages = [
                    Message(role="system", content="Test system"),
                    Message(role="user", content="Test user message")
                ]
                
                result = router.route(
                    messages=messages,
                    call_type=AICallType.NARRATION,
                    game_state={},
                    use_prompt_builder=False,
                    prompt_builder=None,
                    yggdrasil_cognition=None
                )
                print(f"✓ route returned: {type(result)}")
                if hasattr(result, 'content'):
                    print(f"  Content: {result.content[:100]}...")
                else:
                    print(f"  Result: {result}")
            except Exception as e:
                print(f"❌ route failed: {e}")
                traceback.print_exc()
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Router functionality test failed: {e}")
        traceback.print_exc()
        return False

def test_prompt_builder_integration():
    """Test prompt builder integration"""
    print("\n" + "=" * 60)
    print("Testing Prompt Builder Integration")
    print("=" * 60)
    
    try:
        # Try to import prompt builder
        from ai.prompt_builder import PromptBuilder
        
        print("✓ PromptBuilder imported successfully")
        
        # Create a simple prompt builder
        pb = PromptBuilder(data_path="data")
        print(f"✓ PromptBuilder created: {pb}")
        
        # Check if it has Yggdrasil methods
        if hasattr(pb, 'connect_yggdrasil'):
            print("✓ PromptBuilder has connect_yggdrasil method")
        else:
            print("⚠ PromptBuilder missing connect_yggdrasil method")
            
        if hasattr(pb, 'build_with_yggdrasil'):
            print("✓ PromptBuilder has build_with_yggdrasil method")
        else:
            print("⚠ PromptBuilder missing build_with_yggdrasil method")
            
        return True
        
    except Exception as e:
        print(f"❌ Prompt builder test failed: {e}")
        traceback.print_exc()
        return False

def test_full_integration():
    """Test full integration with config"""
    print("\n" + "=" * 60)
    print("Testing Full Integration")
    print("=" * 60)
    
    try:
        import yaml
        from pathlib import Path
        
        # Load config
        config_path = Path("config.yaml")
        if not config_path.exists():
            print("❌ config.yaml not found")
            return False
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
            
        print("✓ Config loaded")
        
        # Test engine creation
        from core.engine import create_engine
        
        try:
            engine = create_engine("config.yaml")
            print("✓ Engine created")
            
            # Check router initialization
            if hasattr(engine, 'ai_router'):
                print(f"✓ Engine has ai_router: {engine.ai_router}")
            else:
                print("❌ Engine missing ai_router attribute")
                
            # Check if router was initialized
            if engine.ai_router:
                print("✓ Router was initialized")
            else:
                print("⚠ Router was not initialized (might be expected if dependencies missing)")
                
            return True
            
        except Exception as e:
            print(f"❌ Engine creation failed: {e}")
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Full integration test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("Yggdrasil Router Integration Debugger")
    print("=" * 60)
    
    tests = [
        ("Imports", test_yggdrasil_imports),
        ("Router Creation", test_router_creation),
        ("Router Functionality", test_router_functionality),
        ("Prompt Builder", test_prompt_builder_integration),
        ("Full Integration", test_full_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✓ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if success:
            passed += 1
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All tests passed! Router integration should work.")
    else:
        print("\n⚠ Some tests failed. Check the errors above.")
        print("\nRecommended fixes:")
        print("1. Check if all Yggdrasil modules are installed")
        print("2. Verify data directory structure")
        print("3. Check for missing dependencies")
        print("4. Look for import errors in the tracebacks above")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)