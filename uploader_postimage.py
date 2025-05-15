try:
    from autotask.nodes import Node, register_node
except ImportError:
    from stub import Node, register_node

import os
import asyncio
from typing import Dict, Any, List, Tuple
from playwright.async_api import async_playwright, Browser, Page
import re

@register_node
class PostImageUploader(Node):
    NAME = "PostImage Uploader"
    DESCRIPTION = "Upload multiple images (up to 8) to PostImage and get their download URLs"
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
            "type": "STRING",
            "default": "false"
        },
        "error_message": {
            "label": "Error Message",
            "description": "Error message if any operation failed",
            "type": "STRING",
            "default": ""
        }
    }

    def _get_valid_image_paths(self, node_inputs: Dict[str, str]) -> List[Tuple[int, str]]:
        """Get all valid image paths from inputs with their indices."""
        valid_images = []
        for i in range(1, 9):
            img_key = f"img{i}"
            if img_key in node_inputs and node_inputs[img_key]:
                valid_images.append((i, node_inputs[img_key]))
        return valid_images

    async def _upload_images(self, page: Page, image_paths: List[Tuple[int, str]], workflow_logger) -> Dict[str, Any]:
        """Upload multiple images at once using Playwright and return their URLs."""
        try:
            # Navigate to the upload page
            await page.goto('https://postimages.org/')
            
            # Wait for the upload form to be ready
            await page.wait_for_selector('#ddupload', timeout=30000)
            
            # Find the hidden file input (it's added dynamically by their JS)
            # Wait a bit for JS to initialize
            await page.wait_for_timeout(2000)
            
            # The site creates a hidden file input, we need to make it visible to interact with it
            await page.evaluate("""() => {
                const input = document.querySelector('input[type="file"]');
                if (input) {
                    input.style.visibility = 'visible';
                    input.style.position = 'fixed';
                    input.style.top = '0';
                    input.style.left = '0';
                    input.style.width = '100px';
                    input.style.height = '100px';
                }
            }""")
            
            # Now wait for and use the file input
            file_input = await page.wait_for_selector('input[type="file"]', timeout=30000)
            await file_input.set_input_files([path for _, path in image_paths])
            
            # Wait for upload to complete by checking for the share form
            await page.wait_for_selector('form.share', timeout=120000)  # Increased timeout for multiple files
            
            # Select direct link option
            await page.select_option('#embed_box', 'code_direct')
            
            # Wait for textarea to update with direct links
            await page.wait_for_timeout(1000)  # Brief pause for content update
            
            # Get the direct URLs from the textarea
            code_box = await page.wait_for_selector('#code_box')
            text_content = await code_box.input_value()
            
            # Extract all direct URLs - should be in format https://i.postimg.cc/xxx/filename.ext
            direct_urls = re.findall(r'https://i\.postimg\.cc/\w+/[^\s\n]+', text_content)
            
            if not direct_urls or len(direct_urls) != len(image_paths):
                raise ValueError(f"Expected {len(image_paths)} URLs but found {len(direct_urls)}")
            
            # Create results dictionary
            results = {
                "success": "true",
                "error_message": "",
                **{f"url{i}": "" for i in range(1, 9)}
            }
            
            # Map URLs to their corresponding indices
            for (index, path), url in zip(image_paths, direct_urls):
                if not url.endswith('?dl=1'):
                    url += '?dl=1'
                results[f"url{index}"] = url
                workflow_logger.info(f"Successfully uploaded image {index}: {os.path.basename(path)}")
            
            return results
            
        except Exception as e:
            error_msg = f"Failed to upload images: {str(e)}"
            workflow_logger.error(error_msg)
            return {
                "success": "false",
                "error_message": error_msg,
                **{f"url{i}": "" for i in range(1, 9)}
            }

    async def execute(self, node_inputs: Dict[str, str], workflow_logger) -> Dict[str, Any]:
        try:
            image_paths = self._get_valid_image_paths(node_inputs)
            if not image_paths:
                raise ValueError("At least one image path must be provided")
            
            workflow_logger.info(f"Uploading {len(image_paths)} images to PostImage")

            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                results = await self._upload_images(page, image_paths, workflow_logger)
                await browser.close()

            return results

        except Exception as e:
            error_msg = f"Failed to process images: {str(e)}"
            workflow_logger.error(error_msg)
            return {
                "success": "false",
                "error_message": error_msg,
                **{f"url{i}": "" for i in range(1, 9)}
            }
