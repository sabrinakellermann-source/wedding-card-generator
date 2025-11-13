import requests
from bs4 import BeautifulSoup
from typing import List
import time

# Minimum number of images required for meaningful aesthetic analysis
MIN_REQUIRED_IMAGES = 5


def extract_pinterest_images(board_url: str, max_images: int = 30) -> List[str]:
    """
    Extract image URLs from a public Pinterest board.
    
    NOTE: Pinterest uses heavy JavaScript and bot detection which makes automated
    scraping unreliable. This function attempts basic extraction but may not work
    consistently. For reliable results, use the manual image URL input option.
    
    Args:
        board_url: URL of the public Pinterest board
        max_images: Maximum number of images to extract (default: 30)
    
    Returns:
        List of image URLs
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
        
        # Try to find images in meta tags first
        meta_images = soup.find_all('meta', property='og:image')
        for meta in meta_images[:max_images]:
            img_url = meta.get('content')
            if img_url and img_url not in image_urls:
                image_urls.append(img_url)
        
        # Try to find images in img tags
        img_tags = soup.find_all('img')
        for img in img_tags:
            src = img.get('src') or img.get('data-src')
            if not src:
                srcset = img.get('srcset')
                if srcset and isinstance(srcset, str):
                    src = srcset.split(',')[0].split(' ')[0]
            
            if src and isinstance(src, str) and ('pinimg.com' in src or 'pinterest.com' in src):
                # Get the highest quality version
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
        
        # Try extracting from page scripts
        if len(image_urls) < 5:
            import re
            script_tags = soup.find_all('script')
            for script in script_tags:
                script_content = script.string
                if script_content and 'pinimg.com' in script_content:
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
        
        if len(validated_urls) < MIN_REQUIRED_IMAGES:
            raise Exception(
                f"Pinterest board scraping is unreliable due to bot detection and JavaScript rendering. "
                f"Found only {len(validated_urls)} images (need at least {MIN_REQUIRED_IMAGES}). "
                f"Please use the 'Manual Image URLs' option instead: "
                f"copy image URLs from your Pinterest board and paste them below."
            )
        
        return validated_urls
    
    except requests.RequestException as e:
        raise Exception(
            f"Failed to access Pinterest board: {str(e)}. "
            f"Pinterest blocks automated access. Please use the 'Manual Image URLs' option instead."
        )
    except Exception as e:
        if "unreliable" in str(e) or "Manual Image URLs" in str(e):
            raise  # Re-raise our custom message
        raise Exception(
            f"Pinterest board scraping failed: {str(e)}. "
            f"Please use the 'Manual Image URLs' option for reliable results."
        )


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
