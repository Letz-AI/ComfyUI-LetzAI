import torch
from server import PromptServer

# Import LetzAI generator
import sys
import os
sys.path.append(os.path.dirname(__file__))
from letzai_generator import LetzAIGenerator

class ImageSelector:
    CATEGORY = "example"
    
    @classmethod    
    def INPUT_TYPES(s):
        return { 
            "required": { 
                "images": ("IMAGE",), 
                "mode": (["brightest", "reddest", "greenest", "bluest"],)
            } 
        }
    
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "choose_image"
    
    def choose_image(self, images, mode):
        batch_size = images.shape[0]
        brightness = list(torch.mean(image.flatten()).item() for image in images)
        
        if (mode=="brightest"):
            scores = brightness
        else:
            channel = 0 if mode=="reddest" else (1 if mode=="greenest" else 2)
            absolute = list(torch.mean(image[:,:,channel].flatten()).item() for image in images)
            scores = list( absolute[i]/(brightness[i]+1e-8) for i in range(batch_size) )
        
        best = scores.index(max(scores))
        result = images[best].unsqueeze(0)
        
        # Send message to frontend
        PromptServer.instance.send_sync("example.imageselector.textmessage", {"message":f"Picked image {best+1}"})
        
        return (result,)

# Node mappings
NODE_CLASS_MAPPINGS = {
    "Image Selector": ImageSelector,
    "LetzAI Generator": LetzAIGenerator,
}

# Optional display name mappings
NODE_DISPLAY_NAME_MAPPINGS = {
    "Image Selector": "Image Selector",
    "LetzAI Generator": "LetzAI Image Generator",
} 