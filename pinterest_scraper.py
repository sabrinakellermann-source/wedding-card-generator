import requests
from bs4 import BeautifulSoup
from typing import List
import time


def extract_pinterest_images(board_url: str, max_images: int = 30) -> List[str]:
    """
    Extract image URLs from a public Pinterest board.
    
    Args:
        board_url: URL of the public Pinterest board
        max_images: Maximum number of images to extract (default: 30)
    
    Returns:
        List of image URLs
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        response = requests.get(board_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        image_urls = []
        
        # Pinterest uses multiple image formats and structures
        # Try to find images in meta tags first (most reliable)
        meta_images = soup.find_all('meta', property='og:image')
        for meta in meta_images[:max_images]:
            img_url = meta.get('content')
            if img_url and img_url not in image_urls:
                image_urls.append(img_url)
        
        # Try to find images in img tags with Pinterest-specific patterns
        img_tags = soup.find_all('img')
        for img in img_tags:
            # Get srcset or src
            src = img.get('src') or img.get('data-src') or img.get('srcset', '').split(',')[0].split(' ')[0]
            
            if src and ('pinimg.com' in src or 'pinterest.com' in src):
                # Get the highest quality version
                # Pinterest uses different size formats: originals/, 736x/, 564x/, etc.
                if '/236x/' in src:
                    src = src.replace('/236x/', '/originals/')
                elif '/474x/' in src:
                    src = src.replace('/474x/', '/originals/')
                elif '/564x/' in src:
                    src = src.replace('/564x/', '/originals/')
                    
                if src not in image_urls:
                    image_urls.append(src)
                    
            if len(image_urls) >= max_images:
                break
        
        # If we didn't find enough images, try script tags with JSON data
        if len(image_urls) < 5:
            script_tags = soup.find_all('script', {'id': 'initial-state'})
            for script in script_tags:
                script_content = script.string
                if script_content and 'pinimg.com' in script_content:
                    # Simple extraction of image URLs from JSON
                    import re
                    pattern = r'https://i\.pinimg\.com/[^"\'}\s]+'
                    found_urls = re.findall(pattern, script_content)
                    for url in found_urls:
                        if '/originals/' in url or '/736x/' in url or '/564x/' in url:
                            clean_url = url.replace('/236x/', '/originals/').replace('/474x/', '/originals/').replace('/564x/', '/originals/')
                            if clean_url not in image_urls:
                                image_urls.append(clean_url)
                                if len(image_urls) >= max_images:
                                    break
        
        # Clean and validate URLs
        validated_urls = []
        for url in image_urls[:max_images]:
            if url.startswith('http') and ('pinimg.com' in url or 'pinterest.com' in url):
                validated_urls.append(url)
        
        return validated_urls
    
    except requests.RequestException as e:
        raise Exception(f"Failed to fetch Pinterest board: {str(e)}")
    except Exception as e:
        raise Exception(f"Error parsing Pinterest board: {str(e)}")


def validate_pinterest_url(url: str) -> bool:
    """
    Validate if the URL is a valid Pinterest board URL.
    
    Args:
        url: URL to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not url:
        return False
    
    # Check if URL contains pinterest.com and likely board patterns
    valid_patterns = [
        'pinterest.com/',
        'pinterest.de/',
        'pinterest.co.uk/',
    ]
    
    return any(pattern in url.lower() for pattern in valid_patterns)
