import requests
from bs4 import BeautifulSoup
from typing import List
import time

# Minimum number of images required for meaningful aesthetic analysis
MIN_REQUIRED_IMAGES = 5


def extract_pinterest_images(board_url: str, max_images: int = 30) -> List[str]:
    """
    Extract image URLs from a public Pinterest board using Playwright for JavaScript rendering.
    
    Args:
        board_url: URL of the public Pinterest board
        max_images: Maximum number of images to extract (default: 30)
    
    Returns:
        List of image URLs
    """
    try:
        from playwright.sync_api import sync_playwright
        import re
        
        image_urls = []
        
        with sync_playwright() as p:
            # Launch browser in headless mode
            browser = p.chromium.launch(headless=True)
            
            # Create context with realistic user agent
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = context.new_page()
            
            # Navigate to Pinterest board
            page.goto(board_url, wait_until='networkidle', timeout=30000)
            
            # Wait for images to load
            page.wait_for_timeout(3000)
            
            # Scroll down a few times to trigger lazy loading
            for _ in range(3):
                page.evaluate('window.scrollBy(0, window.innerHeight)')
                page.wait_for_timeout(1000)
            
            # Extract all image URLs from the page
            # Pinterest loads images with srcset and data-src attributes
            img_elements = page.query_selector_all('img')
            
            for img in img_elements:
                # Try different attributes where Pinterest stores image URLs
                src = img.get_attribute('src') or img.get_attribute('data-src')
                srcset = img.get_attribute('srcset')
                
                # Extract URL from srcset if available
                if srcset:
                    # srcset format: "url1 1x, url2 2x"
                    urls_in_srcset = re.findall(r'(https://[^\s,]+)', srcset)
                    for url in urls_in_srcset:
                        if 'pinimg.com' in url and url not in image_urls:
                            # Get highest quality version
                            clean_url = url.replace('/236x/', '/originals/').replace('/474x/', '/originals/').replace('/564x/', '/originals/')
                            image_urls.append(clean_url)
                
                # Try src attribute
                if src and 'pinimg.com' in src and src not in image_urls:
                    clean_url = src.replace('/236x/', '/originals/').replace('/474x/', '/originals/').replace('/564x/', '/originals/')
                    image_urls.append(clean_url)
                
                if len(image_urls) >= max_images:
                    break
            
            # Also try extracting from page content/scripts
            if len(image_urls) < 5:
                content = page.content()
                pattern = r'https://i\.pinimg\.com/[^"\'}\s]+'
                found_urls = re.findall(pattern, content)
                for url in found_urls:
                    if ('/originals/' in url or '/736x/' in url or '/564x/' in url) and url not in image_urls:
                        clean_url = url.replace('/236x/', '/originals/').replace('/474x/', '/originals/').replace('/564x/', '/originals/')
                        image_urls.append(clean_url)
                        if len(image_urls) >= max_images:
                            break
            
            browser.close()
        
        # Clean and validate URLs
        validated_urls = []
        for url in image_urls[:max_images]:
            if url.startswith('http') and 'pinimg.com' in url:
                validated_urls.append(url)
        
        return validated_urls
    
    except ImportError:
        raise Exception("Playwright not installed. Please install with: pip install playwright && playwright install chromium")
    except Exception as e:
        raise Exception(f"Error extracting Pinterest images: {str(e)}")


def validate_pinterest_url(url: str) -> bool:
    """
    Validate if the URL is a valid Pinterest board URL.
    Only accepts actual board URLs, not search results, pins, or other pages.
    
    Args:
        url: URL to validate
    
    Returns:
        True if valid board URL, False otherwise
    """
    if not url:
        return False
    
    # Normalize: strip whitespace and ensure https
    url = url.strip()
    if not url.startswith('http'):
        return False
    
    import re
    from urllib.parse import urlparse
    
    # Allowlist of legitimate Pinterest TLDs to prevent SSRF attacks
    # Includes both single-label (com, de) and multi-label TLDs (com.au, co.uk, co.kr)
    allowed_tlds = [
        # Single-label TLDs
        'com', 'ca', 'de', 'fr', 'es', 'it', 'jp', 'ru', 'br', 'at', 'ch',
        'cl', 'cz', 'dk', 'fi', 'hk', 'hu', 'id', 'ie', 'in', 'nl', 'no',
        'nz', 'ph', 'pl', 'pt', 'ro', 'se', 'sg', 'th', 'tw', 'vn', 'za',
        'ae', 'be', 'gr', 'kr',
        # Multi-label TLDs
        'com.au', 'com.mx', 'com.br', 'co.uk', 'co.kr', 'co.jp', 'co.nz',
        'co.in', 'co.za', 'com.ar', 'com.co', 'com.ec', 'com.pe', 'com.ph',
        'com.sg', 'com.tw', 'com.vn', 'com.hk'
    ]
    
    # Parse URL to extract components
    parsed = urlparse(url)
    hostname = parsed.hostname
    path = parsed.path
    
    if not hostname or not path:
        return False
    
    # Validate hostname: must be pinterest.{tld} or {locale}.pinterest.{tld}
    # Examples:
    # - pinterest.com, www.pinterest.com
    # - pinterest.com.au, www.pinterest.com.au
    # - in.pinterest.com, br.pinterest.com, es.pinterest.com, tr.pinterest.com
    # - pinterest.co.kr, www.pinterest.co.kr
    # Reject:
    # - pinterest.attacker.com (not in TLD allowlist)
    # - evil.subdomain.pinterest.com (too many levels)
    parts = hostname.split('.')
    
    # Check if hostname contains 'pinterest'
    pinterest_found = False
    tld = None
    
    for i, part in enumerate(parts):
        if part == 'pinterest':
            # Extract TLD after 'pinterest'
            tld = '.'.join(parts[i+1:])
            if tld in allowed_tlds:
                pinterest_found = True
                # Validate prefix structure (if any)
                # Allow: no prefix, 'www', or 2-3 letter locale codes (matching ISO country codes)
                if i == 0:
                    # Direct pinterest.{tld} - valid
                    pass
                elif i == 1:
                    # Single prefix: {locale}.pinterest.{tld}
                    locale = parts[0]
                    # Allow 'www' or 2-3 letter locale codes (ISO country codes)
                    if not (locale == 'www' or (len(locale) in [2, 3] and locale.isalpha())):
                        return False
                else:
                    # Too many subdomain levels - reject to prevent SSRF
                    return False
            break
    
    if not pinterest_found or not tld:
        return False
    
    # Validate path structure: /{username}/{board-name}/ (with optional trailing slash)
    # Reject search URLs, pin URLs, query strings
    path_pattern = r'^/[^/]+/[^/]+/?$'
    if not re.match(path_pattern, path):
        return False
    
    # Reject obvious non-board paths
    reject_patterns = ['/search/', '/pin/', '/ideas/', '?']
    if any(pattern in url for pattern in reject_patterns):
        return False
    
    return True
