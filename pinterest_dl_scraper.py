"""
Pinterest board scraper using pinterest-dl library.
Fetches images from any public Pinterest board without authentication.
"""

from typing import List
from pinterest_dl import PinterestDL


class PinterestDLError(Exception):
    """Custom exception for pinterest-dl scraping errors"""
    pass


def extract_pinterest_board_images(board_url: str, max_images: int = 30) -> List[str]:
    """
    Extract image URLs from a public Pinterest board using pinterest-dl.
    
    This uses reverse-engineered Pinterest API, so it may break if Pinterest
    changes their internal API. However, it works without authentication and
    can access any public board.
    
    Args:
        board_url: Full URL of the Pinterest board
        max_images: Maximum number of images to fetch (default: 30)
    
    Returns:
        List of image URLs (original resolution)
    
    Raises:
        PinterestDLError: If scraping fails or board is inaccessible
    """
    try:
        # Initialize pinterest-dl with API mode (faster, no browser needed)
        dl = PinterestDL.with_api(
            timeout=10,
            verbose=False,
            ensure_alt=True
        )
        
        # Scrape the board
        pins = dl.scrape(
            url=board_url,
            num=max_images,
            min_resolution=(200, 200)
        )
        
        # Extract image URLs from pins
        image_urls = []
        for pin in pins:
            # pinterest-dl returns Pin objects with 'image' attribute
            if hasattr(pin, 'image') and pin.image:
                image_urls.append(pin.image)
            elif isinstance(pin, dict) and 'image' in pin:
                image_urls.append(pin['image'])
        
        if not image_urls:
            raise PinterestDLError(
                f"No images found on this Pinterest board. "
                f"Please check the URL and ensure the board is public and contains images."
            )
        
        return image_urls
        
    except Exception as e:
        error_msg = str(e).lower()
        
        # Provide helpful error messages
        if 'timeout' in error_msg or 'timed out' in error_msg:
            raise PinterestDLError(
                "Pinterest request timed out. The board may be too large or Pinterest is slow. "
                "Please try again or use a smaller board."
            )
        elif 'not found' in error_msg or '404' in error_msg:
            raise PinterestDLError(
                "Pinterest board not found. Please check the URL and ensure it's a valid board URL."
            )
        elif 'private' in error_msg or 'secret' in error_msg:
            raise PinterestDLError(
                "This appears to be a private or secret board. "
                "Only public boards can be accessed without authentication."
            )
        else:
            raise PinterestDLError(
                f"Failed to scrape Pinterest board: {str(e)}. "
                f"Pinterest may have changed their API or the board may be inaccessible."
            )
