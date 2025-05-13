try:
    from autotask.nodes import Node, register_node
    from autotask.api_keys import get_api_key
except ImportError:
    from stub import Node, register_node

import os
import base64
import requests
from typing import Dict, Any
from datetime import datetime
import re

ACCESS_TOKEN = get_api_key(provider="gitee.com", key_name="ACCESS_TOKEN")

@register_node
class GiteeImageUploader(Node):
    NAME = "Gitee Image Uploader"
    DESCRIPTION = "Upload images to Gitee repository and get the download URL"

    INPUTS = {
        "image_path": {
            "label": "Local Image Path",
            "description": "Path to the local image file to upload",
            "type": "STRING",
            "widget": "FILE",
            "required": True,
            "default": "",
            "placeholder": "Select an image file"
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
        "image_url": {
            "label": "Image URL",
            "description": "Direct download URL of the uploaded image",
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

    async def execute(self, node_inputs: Dict[str, Any], workflow_logger) -> Dict[str, Any]:
        try:
            image_path = node_inputs["image_path"]
            repo_url = node_inputs["repo_url"]

            # Parse repository information
            owner, repo = self._parse_repo_url(repo_url)
            target_dir = self._get_target_dir()
            
            workflow_logger.info(f"Uploading image to Gitee repository: {owner}/{repo}")
            workflow_logger.info(f"Target directory: {target_dir}")
            
            # Read and encode image
            with open(image_path, "rb") as f:
                content = f.read()
            b64_content = base64.b64encode(content).decode('utf-8')
            
            # Prepare API request
            filename = os.path.basename(image_path)
            api_url = f"https://gitee.com/api/v5/repos/{owner}/{repo}/contents/{target_dir}/{filename}"
            
            payload = {
                "access_token": ACCESS_TOKEN,
                "content": b64_content,
                "branch": "master",
                "message": f"Upload image: {filename}"
            }
            
            # Send request
            response = requests.post(api_url, json=payload)
            response.raise_for_status()
            result = response.json()
            
            workflow_logger.info(f"Successfully uploaded image: {filename}")
            
            return {
                "success": True,
                "image_url": result["content"]["download_url"]
            }

        except Exception as e:
            error_msg = f"Failed to upload image: {str(e)}"
            workflow_logger.error(error_msg)
            return {
                "success": False,
                "error_message": error_msg
            }






