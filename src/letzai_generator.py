import torch
import requests
import json
import time
import io
from PIL import Image
import numpy as np
from server import PromptServer
import comfy.utils
import comfy.model_management

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
            # Check for interruption before starting
            if comfy.model_management.processing_interrupted():
                raise Exception("Generation cancelled by user")
            
            # Send the generation request
            PromptServer.instance.send_sync("letzai.status", {"message": "Sending generation request..."})
            
            response = requests.post("https://api.letz.ai/images", 
                                   headers=headers, 
                                   json=post_data, 
                                   timeout=30)
            
            # Accept both 200 (OK) and 201 (Created) as successful responses
            if response.status_code not in [200, 201]:
                # Provide specific error messages based on status code
                if response.status_code == 400:
                    error_msg = "Bad Request - Check your parameters (width, height, quality, creativity, mode, version)"
                elif response.status_code == 401:
                    error_msg = "Unauthorized - Invalid API key. Please check your LetzAI API key"
                elif response.status_code == 403:
                    error_msg = "Forbidden - API key valid but access denied. Check your subscription status"
                elif response.status_code == 429:
                    error_msg = "Rate Limited - Too many requests. Please wait and try again"
                elif response.status_code == 500:
                    error_msg = "LetzAI Server Error - Please try again later"
                else:
                    error_msg = f"API request failed with HTTP status {response.status_code}"
                
                # Try to get more details from the API response
                try:
                    error_data = response.json()
                    if "message" in error_data:
                        error_msg += f" - {error_data['message']}"
                    elif "error" in error_data:
                        error_msg += f" - {error_data['error']}"
                except:
                    # If we can't parse JSON, include raw response
                    response_text = response.text[:200] if response.text else "No response body"
                    error_msg += f" - Response: {response_text}"
                
                raise Exception(error_msg)
            
            # Success! Log the response status
            PromptServer.instance.send_sync("letzai.status", {"message": f"✅ API responded successfully (HTTP {response.status_code})"})
            
            # Get the image ID from the response
            result = response.json()
            if "id" not in result:
                raise Exception("No image ID returned from API")
            
            image_id = result["id"]
            PromptServer.instance.send_sync("letzai.status", {"message": f"✅ Generation started (ID: {image_id[:8]}...)"})
            
            
            # Poll for completion
            image_url = self._poll_for_completion(image_id, api_key)
            
            # Download and convert the image
            image_tensor = self._download_and_convert_image(image_url)
            
            PromptServer.instance.send_sync("letzai.status", {"message": "Image generation completed!"})
            
            return (image_tensor,)
            
        except Exception as e:
            error_str = str(e)
            if "cancelled by user" in error_str:
                # User cancellation - send different message type
                PromptServer.instance.send_sync("letzai.status", {"message": "🛑 Generation cancelled by user"})
                raise Exception("Generation cancelled by user")
            else:
                # Other errors
                error_msg = f"LetzAI generation failed: {error_str}"
                PromptServer.instance.send_sync("letzai.error", {"message": error_msg})
                raise Exception(error_msg)
    
    def _poll_for_completion(self, image_id, api_key, max_wait_time=300):
        """Poll the API until image generation is complete"""
        
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        
        start_time = time.time()
        
        # Create progress bar (assuming 100 steps for percentage)
        pbar = comfy.utils.ProgressBar(100)
        last_progress = 0
        
        while True:
            # Check for ComfyUI interruption
            if comfy.model_management.processing_interrupted():
                self._interrupt_generation(image_id, api_key)
                raise Exception("Generation cancelled by user")
            
            if time.time() - start_time > max_wait_time:
                raise Exception("Image generation timed out")
            
            try:
                response = requests.get(f"https://api.letz.ai/images/{image_id}", 
                                      headers=headers, 
                                      timeout=30)
                
                if response.status_code != 200:
                    if response.status_code == 404:
                        raise Exception(f"Image not found - Generation may have been cancelled or expired")
                    elif response.status_code == 401:
                        raise Exception(f"Unauthorized - API key invalid or expired")
                    else:
                        raise Exception(f"Failed to check image status: HTTP {response.status_code}")
                
                data = response.json()
                status = data.get("status", "unknown")
                progress = data.get("progress", 0)
                
                # Update progress bar
                if progress > last_progress:
                    pbar.update(progress - last_progress)
                    last_progress = progress
                
                # Also send status message (keeping for compatibility)
                PromptServer.instance.send_sync("letzai.status", {
                    "message": f"Status: {status}, Progress: {progress}%"
                })
                
                if status == "ready":
                    # Ensure progress bar reaches 100%
                    if last_progress < 100:
                        pbar.update(100 - last_progress)
                    
                    # Return the original image URL
                    if "imageVersions" in data and "original" in data["imageVersions"]:
                        return data["imageVersions"]["original"]
                    else:
                        raise Exception("No image URL found in completed generation")
                
                elif status == "failed":
                    error_msg = data.get("progressMessage", "Generation failed")
                    raise Exception(f"Image generation failed: {error_msg}")
                
                elif status in ["new", "in progress", "generating"]:
                    # Wait before polling again
                    time.sleep(2)
                    continue
                
                else:
                    raise Exception(f"Unknown status: {status}")
                    
            except requests.RequestException as e:
                raise Exception(f"Network error while polling: {str(e)}")
    
    def _interrupt_generation(self, image_id, api_key):
        """Interrupt the LetzAI generation using the API"""
        
        try:
            headers = {
                "Authorization": f"Bearer {api_key}"
            }
            
            response = requests.put(f"https://api.letz.ai/images/{image_id}/interruption", 
                                  headers=headers, 
                                  timeout=10)
            
            if response.status_code == 204:
                PromptServer.instance.send_sync("letzai.status", {
                    "message": "✅ Generation cancelled successfully"
                })
            else:
                # Log but don't fail if interruption fails
                PromptServer.instance.send_sync("letzai.status", {
                    "message": f"⚠️ Could not cancel generation (HTTP {response.status_code})"
                })
                
        except Exception as e:
            # Log but don't fail if interruption fails
            PromptServer.instance.send_sync("letzai.status", {
                "message": f"⚠️ Could not cancel generation: {str(e)}"
            })
    
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