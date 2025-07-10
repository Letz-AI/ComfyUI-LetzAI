#!/usr/bin/env python3
"""
Simple test script to verify ComfyUI node structure
"""

import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_node_structure():
    """Test that nodes have correct structure"""
    
    try:
        # Test Image Selector
        from nodes import ImageSelector
        print("✓ ImageSelector imported successfully")
        
        # Check required attributes
        assert hasattr(ImageSelector, 'INPUT_TYPES'), "ImageSelector missing INPUT_TYPES"
        assert hasattr(ImageSelector, 'RETURN_TYPES'), "ImageSelector missing RETURN_TYPES"
        assert hasattr(ImageSelector, 'FUNCTION'), "ImageSelector missing FUNCTION"
        assert hasattr(ImageSelector, 'CATEGORY'), "ImageSelector missing CATEGORY"
        print("✓ ImageSelector has all required attributes")
        
        # Test LetzAI Generator
        from letzai_generator import LetzAIGenerator
        print("✓ LetzAIGenerator imported successfully")
        
        # Check required attributes
        assert hasattr(LetzAIGenerator, 'INPUT_TYPES'), "LetzAIGenerator missing INPUT_TYPES"
        assert hasattr(LetzAIGenerator, 'RETURN_TYPES'), "LetzAIGenerator missing RETURN_TYPES"
        assert hasattr(LetzAIGenerator, 'FUNCTION'), "LetzAIGenerator missing FUNCTION"
        assert hasattr(LetzAIGenerator, 'CATEGORY'), "LetzAIGenerator missing CATEGORY"
        print("✓ LetzAIGenerator has all required attributes")
        
        # Test node mappings
        from nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
        print("✓ Node mappings imported successfully")
        
        assert "Image Selector" in NODE_CLASS_MAPPINGS, "Image Selector not in NODE_CLASS_MAPPINGS"
        assert "LetzAI Generator" in NODE_CLASS_MAPPINGS, "LetzAI Generator not in NODE_CLASS_MAPPINGS"
        print("✓ All nodes registered in NODE_CLASS_MAPPINGS")
        
        print("\n🎉 All tests passed! Node structure is correct.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_node_structure()
    sys.exit(0 if success else 1) 