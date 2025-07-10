# Import LetzAI generator
import sys
import os
sys.path.append(os.path.dirname(__file__))
from letzai_generator import LetzAIGenerator

# Node mappings
NODE_CLASS_MAPPINGS = {
    "LetzAI Generator": LetzAIGenerator,
}

# Optional display name mappings
NODE_DISPLAY_NAME_MAPPINGS = {
    "LetzAI Generator": "LetzAI Image Generator",
} 