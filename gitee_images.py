try:
    from autotask.nodes import Node, register_node
    from autotask.api_keys import get_api_key
except ImportError:
    from stub import Node, register_node

import os
import base64
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import re

ACCESS_TOKEN = get_api_key(provider="gitee.com", key_name="ACCESS_TOKEN")

@register_node
class GiteeImageUploader(Node):
    NAME = "Gitee Image Uploader"
    DESCRIPTION = "Upload multiple images (up to 8) to Gitee repository and get their download URLs"
    CATEGORY = "Image Processing"
    MAINTAINER = "AutoTask Team"
    ICON = "📤"

    INPUTS = {
        "img1": {
            "label": "Image 1",
            "description": "First image file to upload",
            "type": "STRING",
            "widget": "FILE",
            "required": True,
            "default": "",
            "placeholder": "Select first image file"
        },
        "img2": {
            "label": "Image 2",
            "description": "Second image file to upload",
            "type": "STRING",
            "widget": "FILE",
            "required": False,
            "default": "",
            "placeholder": "Select second image file"
        },
        "img3": {
            "label": "Image 3",
            "description": "Third image file to upload",
            "type": "STRING",
            "widget": "FILE",
            "required": False,
            "default": "",
            "placeholder": "Select third image file"
        },
        "img4": {
            "label": "Image 4",
            "description": "Fourth image file to upload",
            "type": "STRING",
            "widget": "FILE",
            "required": False,
            "default": "",
            "placeholder": "Select fourth image file"
        },
        "img5": {
            "label": "Image 5",
            "description": "Fifth image file to upload",
            "type": "STRING",
            "widget": "FILE",
            "required": False,
            "default": "",
            "placeholder": "Select fifth image file"
        },
        "img6": {
            "label": "Image 6",
            "description": "Sixth image file to upload",
            "type": "STRING",
            "widget": "FILE",
            "required": False,
            "default": "",
            "placeholder": "Select sixth image file"
        },
        "img7": {
            "label": "Image 7",
            "description": "Seventh image file to upload",
            "type": "STRING",
            "widget": "FILE",
            "required": False,
            "default": "",
            "placeholder": "Select seventh image file"
        },
        "img8": {
            "label": "Image 8",
            "description": "Eighth image file to upload",
            "type": "STRING",
            "widget": "FILE",
            "required": False,
            "default": "",
            "placeholder": "Select eighth image file"
        },
        "repo_url": {
            "label": "Repository URL",
            "description": "Gitee repository URL",
            "type": "STRING",
            "required": True,
            "default": "",
            "placeholder": "e.g. gitee.com/username/repo"
        }
    }

    OUTPUTS = {
        "url1": {
            "label": "Image 1 URL",
            "description": "Download URL of the first uploaded image",
            "type": "STRING",
            "default": ""
        },
        "url2": {
            "label": "Image 2 URL",
            "description": "Download URL of the second uploaded image",
            "type": "STRING",
            "default": ""
        },
        "url3": {
            "label": "Image 3 URL",
            "description": "Download URL of the third uploaded image",
            "type": "STRING",
            "default": ""
        },
        "url4": {
            "label": "Image 4 URL",
            "description": "Download URL of the fourth uploaded image",
            "type": "STRING",
            "default": ""
        },
        "url5": {
            "label": "Image 5 URL",
            "description": "Download URL of the fifth uploaded image",
            "type": "STRING",
            "default": ""
        },
        "url6": {
            "label": "Image 6 URL",
            "description": "Download URL of the sixth uploaded image",
            "type": "STRING",
            "default": ""
        },
        "url7": {
            "label": "Image 7 URL",
            "description": "Download URL of the seventh uploaded image",
            "type": "STRING",
            "default": ""
        },
        "url8": {
            "label": "Image 8 URL",
            "description": "Download URL of the eighth uploaded image",
            "type": "STRING",
            "default": ""
        },
        "success": {
            "label": "Success",
            "description": "Whether all operations were successful",
            "type": "BOOLEAN",
            "default": False
        },
        "error_message": {
            "label": "Error Message",
            "description": "Error message if any operation failed",
            "type": "STRING",
            "default": ""
        }
    }

    def _parse_repo_url(self, repo_url: str) -> tuple[str, str]:
        """Extract owner and repo from any format of Gitee URL."""
        # Remove leading/trailing whitespace and slashes
        url = repo_url.strip().strip('/')
        
        # Case 1: Simple format (owner/repo)
        if '/' in url and not any(x in url for x in [':', '@', 'gitee.com']):
            parts = url.split('/')
            if len(parts) >= 2:
                return parts[0], parts[1]
        
        # Case 2: SSH format (git@gitee.com:owner/repo.git)
        ssh_match = re.match(r'^git@gitee\.com:([^/]+)/([^/]+?)(\.git)?$', url)
        if ssh_match:
            return ssh_match.group(1), ssh_match.group(2)
        
        # Case 3: HTTPS or git protocol (https://gitee.com/owner/repo or git://gitee.com/owner/repo)
        https_match = re.match(r'^(https?://|git://)?gitee\.com/([^/]+)/([^/]+?)(\.git)?$', url)
        if https_match:
            return https_match.group(2), https_match.group(3)
            
        raise ValueError("Invalid repository URL format. Supported formats: owner/repo, https://gitee.com/owner/repo, git@gitee.com:owner/repo")

    def _get_target_dir(self) -> str:
        """Generate target directory path based on current date."""
        now = datetime.now()
        return f"images/{now.year}/{now.month:02d}/{now.day:02d}"

    def _get_valid_image_paths(self, node_inputs: Dict[str, str]) -> List[Tuple[int, str]]:
        """Get all valid image paths from inputs with their indices."""
        valid_images = []
        for i in range(1, 9):
            img_key = f"img{i}"
            if img_key in node_inputs and node_inputs[img_key]:
                valid_images.append((i, node_inputs[img_key]))
        return valid_images

    def _get_timestamped_filename(self, original_filename: str) -> str:
        """Add timestamp to filename while preserving extension."""
        name, ext = os.path.splitext(original_filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{name}_{timestamp}{ext}"

    async def _upload_single_image(self, session: aiohttp.ClientSession, image_path: str, owner: str, repo: str, 
                                 target_dir: str, index: int, workflow_logger) -> Dict[str, Any]:
        """Upload a single image to Gitee and return its URL."""
        try:
            # Read and encode image
            with open(image_path, "rb") as f:
                content = f.read()
            b64_content = base64.b64encode(content).decode('utf-8')
            
            # Get original filename and create timestamped version
            original_filename = os.path.basename(image_path)
            filename = self._get_timestamped_filename(original_filename)
            
            # Prepare API request
            api_url = f"https://gitee.com/api/v5/repos/{owner}/{repo}/contents/{target_dir}/{filename}"
            
            payload = {
                "access_token": ACCESS_TOKEN,
                "content": b64_content,
                "branch": "master",
                "message": f"Upload image: {filename} (original: {original_filename})"
            }
            
            # Send request using aiohttp session
            async with session.post(api_url, json=payload) as response:
                response_text = await response.text()
                # Accept both 200 (OK) and 201 (Created) status codes
                if response.status not in [200, 201]:
                    raise ValueError(f"API request failed with status {response.status}: {response_text}")
                
                result = await response.json()
                if "content" not in result or "download_url" not in result["content"]:
                    raise ValueError(f"Invalid API response format: {response_text}")
            
            workflow_logger.info(f"Successfully uploaded image {index}: {filename}")
            return {
                "index": index,
                "success": True,
                "url": result["content"]["download_url"]
            }
        except Exception as e:
            error_msg = f"Failed to upload image {index} ({os.path.basename(image_path)}): {str(e)}"
            workflow_logger.error(error_msg)
            return {
                "index": index,
                "success": False,
                "error_message": error_msg
            }

    async def execute(self, node_inputs: Dict[str, str], workflow_logger) -> Dict[str, Any]:
        try:
            image_paths = self._get_valid_image_paths(node_inputs)
            if not image_paths:
                raise ValueError("At least one image path must be provided")

            repo_url = node_inputs["repo_url"]
            owner, repo = self._parse_repo_url(repo_url)
            target_dir = self._get_target_dir()
            
            workflow_logger.info(f"Uploading {len(image_paths)} images to Gitee repository: {owner}/{repo}")
            workflow_logger.info(f"Target directory: {target_dir}")

            # Initialize results dictionary with empty values
            results = {f"url{i}": "" for i in range(1, 9)}
            results.update({"success": True, "error_message": ""})

            # Create aiohttp session for connection pooling
            async with aiohttp.ClientSession() as session:
                # Upload images sequentially
                for index, image_path in image_paths:
                    result = await self._upload_single_image(session, image_path, owner, repo, target_dir, index, workflow_logger)
                    
                    if result["success"]:
                        results[f"url{result['index']}"] = result["url"]
                    else:
                        results["success"] = False
                        results["error_message"] = result["error_message"]
                        break

            if results["success"]:
                workflow_logger.info("All images uploaded successfully")

            return results

        except Exception as e:
            error_msg = f"Failed to process images: {str(e)}"
            workflow_logger.error(error_msg)
            return {
                "success": False,
                "error_message": error_msg,
                **{f"url{i}": "" for i in range(1, 9)}
            }






