import torch
import requests
import json
import time
import io
from PIL import Image
import numpy as np
from server import PromptServer

class LetzAIGenerator:
    CATEGORY = "LetzAI"
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "api_key": ("STRING", {"multiline": False, "placeholder": "Enter your LetzAI API key"}),
                "prompt": ("STRING", {"multiline": True, "placeholder": "Enter your prompt here"}),
                "width": ("INT", {"default": 1600, "min": 520, "max": 2160, "step": 8}),
                "height": ("INT", {"default": 1600, "min": 520, "max": 2160, "step": 8}),
                "quality": ("INT", {"default": 2, "min": 1, "max": 5, "step": 1}),
                "creativity": ("INT", {"default": 2, "min": 1, "max": 5, "step": 1}),
                "mode": (["default", "sigma", "turbo"], {"default": "default"}),
                "version": ([2, 3], {"default": 3}),
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff}),
                "has_watermark": ("BOOLEAN", {"default": True}),
            }
        }
    
    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    FUNCTION = "generate_image"
    OUTPUT_NODE = True
    
    def generate_image(self, api_key, prompt, width, height, quality, creativity, mode, version, seed, has_watermark):
        """Generate an image using the LetzAI API"""
        
        if not api_key.strip():
            raise ValueError("API key is required")
        
        if not prompt.strip():
            raise ValueError("Prompt is required")
        
        # Prepare the request data
        post_data = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "quality": quality,
            "creativity": creativity,
            "mode": mode,
            "systemVersion": version,
            "hasWatermark": has_watermark
        }
        
        # Add seed to prompt if provided (since LetzAI doesn't have direct seed support)
        if seed > 0:
            post_data["prompt"] = f"{prompt} [seed:{seed}]"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        try:
            # Send the generation request
            PromptServer.instance.send_sync("letzai.status", {"message": "Sending generation request..."})
            
            response = requests.post("https://api.letz.ai/images", 
                                   headers=headers, 
                                   json=post_data, 
                                   timeout=30)
            
            if response.status_code != 200:
                error_msg = f"API request failed with status {response.status_code}"
                try:
                    error_data = response.json()
                    if "message" in error_data:
                        error_msg += f": {error_data['message']}"
                except:
                    error_msg += f": {response.text}"
                raise Exception(error_msg)
            
            # Get the image ID from the response
            result = response.json()
            if "id" not in result:
                raise Exception("No image ID returned from API")
            
            image_id = result["id"]
            
            # Poll for completion
            image_url = self._poll_for_completion(image_id, api_key)
            
            # Download and convert the image
            image_tensor = self._download_and_convert_image(image_url)
            
            PromptServer.instance.send_sync("letzai.status", {"message": "Image generation completed!"})
            
            return (image_tensor,)
            
        except Exception as e:
            error_msg = f"LetzAI generation failed: {str(e)}"
            PromptServer.instance.send_sync("letzai.error", {"message": error_msg})
            raise Exception(error_msg)
    
    def _poll_for_completion(self, image_id, api_key, max_wait_time=300):
        """Poll the API until image generation is complete"""
        
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        start_time = time.time()
        
        while True:
            if time.time() - start_time > max_wait_time:
                raise Exception("Image generation timed out")
            
            try:
                response = requests.get(f"https://api.letz.ai/images/{image_id}", 
                                      headers=headers, 
                                      timeout=30)
                
                if response.status_code != 200:
                    raise Exception(f"Failed to check image status: {response.status_code}")
                
                data = response.json()
                status = data.get("status", "unknown")
                progress = data.get("progress", 0)
                
                PromptServer.instance.send_sync("letzai.status", {
                    "message": f"Status: {status}, Progress: {progress}%"
                })
                
                if status == "ready":
                    # Return the original image URL
                    if "imageVersions" in data and "original" in data["imageVersions"]:
                        return data["imageVersions"]["original"]
                    else:
                        raise Exception("No image URL found in completed generation")
                
                elif status == "failed":
                    error_msg = data.get("progressMessage", "Generation failed")
                    raise Exception(f"Image generation failed: {error_msg}")
                
                elif status in ["new", "in progress"]:
                    # Wait before polling again
                    time.sleep(2)
                    continue
                
                else:
                    raise Exception(f"Unknown status: {status}")
                    
            except requests.RequestException as e:
                raise Exception(f"Network error while polling: {str(e)}")
    
    def _download_and_convert_image(self, image_url):
        """Download image from URL and convert to ComfyUI tensor format"""
        
        try:
            response = requests.get(image_url, timeout=60)
            response.raise_for_status()
            
            # Open image with PIL
            image = Image.open(io.BytesIO(response.content))
            
            # Convert to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            # Convert to numpy array
            image_array = np.array(image).astype(np.float32) / 255.0
            
            # Convert to tensor with shape [1, H, W, C] (batch of 1)
            image_tensor = torch.from_numpy(image_array).unsqueeze(0)
            
            return image_tensor
            
        except Exception as e:
            raise Exception(f"Failed to download or convert image: {str(e)}")
    
    @classmethod
    def IS_CHANGED(cls, **kwargs):
        # Always consider this node as changed since we're generating new images
        return float("nan") 