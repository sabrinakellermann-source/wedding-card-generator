"""
Apify Pinterest board scraper integration.
Uses Apify's Pinterest Scraper to reliably fetch images from any public Pinterest board.
"""

import os
from typing import List
from apify_client import ApifyClient


class ApifyPinterestError(Exception):
    """Custom exception for Apify Pinterest scraping errors"""
    pass


def extract_pinterest_board_images_apify(board_url: str, max_images: int = 30) -> List[str]:
    """
    Extract image URLs from a public Pinterest board using Apify's Pinterest Scraper.
    
    This uses Apify's professional scraping service which handles JavaScript rendering
    and bot detection, making it much more reliable than BeautifulSoup scraping.
    
    Args:
        board_url: Full URL of the Pinterest board
        max_images: Maximum number of images to fetch (default: 30)
    
    Returns:
        List of image URLs (original resolution)
    
    Raises:
        ApifyPinterestError: If scraping fails or API key is missing
    """
    # Get Apify API token from environment
    api_token = os.getenv('APIFY_API_TOKEN')
    if not api_token:
        raise ApifyPinterestError(
            "Apify API token not found. Please configure your Apify API key in the Secrets."
        )
    
    try:
        # Initialize Apify client
        client = ApifyClient(api_token)
        
        # Use danielmilevski9's Pinterest Scraper (best general-purpose scraper)
        # Actor ID: danielmilevski9/pinterest-crawler
        actor_input = {
            "startUrls": [{"url": board_url}],
            "resultsLimit": max_images,
            "proxy": {
                "useApifyProxy": True,
                "apifyProxyGroups": ["RESIDENTIAL"]
            }
        }
        
        # Run the actor and wait for it to finish
        run = client.actor("danielmilevski9/pinterest-crawler").call(run_input=actor_input)
        
        # Fetch results from the dataset
        dataset_items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        
        if not dataset_items:
            raise ApifyPinterestError(
                f"No pins found on this Pinterest board. "
                f"Please check the URL and ensure the board is public and contains images."
            )
        
        # Extract image URLs from the results
        image_urls = []
        for item in dataset_items:
            # Try different possible image URL fields
            img_url = None
            
            # Common field names in Apify Pinterest scrapers
            if 'image' in item and item['image']:
                img_url = item['image']
            elif 'imageUrl' in item and item['imageUrl']:
                img_url = item['imageUrl']
            elif 'images' in item and item['images']:
                # Sometimes images is a dict with different sizes
                if isinstance(item['images'], dict):
                    # Try to get original or largest size
                    img_url = item['images'].get('orig') or item['images'].get('original') or item['images'].get('1200x')
                elif isinstance(item['images'], list) and len(item['images']) > 0:
                    img_url = item['images'][0]
            
            if img_url and isinstance(img_url, str):
                # Ensure we get high quality images
                if '/236x/' in img_url:
                    img_url = img_url.replace('/236x/', '/originals/')
                elif '/474x/' in img_url:
                    img_url = img_url.replace('/474x/', '/originals/')
                elif '/564x/' in img_url:
                    img_url = img_url.replace('/564x/', '/originals/')
                
                image_urls.append(img_url)
            
            if len(image_urls) >= max_images:
                break
        
        if not image_urls:
            raise ApifyPinterestError(
                f"Could not extract image URLs from the scraped data. "
                f"The board structure may have changed or the scraper needs updating."
            )
        
        return image_urls
        
    except ApifyPinterestError:
        raise  # Re-raise our custom errors
    except Exception as e:
        error_msg = str(e).lower()
        
        # Provide helpful error messages based on common issues
        if 'token' in error_msg or 'authentication' in error_msg:
            raise ApifyPinterestError(
                f"Apify authentication failed. Please check your APIFY_API_TOKEN in Secrets."
            )
        elif 'timeout' in error_msg:
            raise ApifyPinterestError(
                f"Apify scraping timed out. The board may be very large. Please try again."
            )
        elif 'not found' in error_msg or '404' in error_msg:
            raise ApifyPinterestError(
                f"Pinterest board not found. Please check the URL and ensure it's a valid board URL."
            )
        else:
            raise ApifyPinterestError(
                f"Apify scraping failed: {str(e)}. Please try again or contact support."
            )
