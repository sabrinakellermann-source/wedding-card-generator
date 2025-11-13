"""
Pinterest API integration for fetching board pins and images.
Uses OAuth 2.0 authentication with Pinterest API v5.
"""

import os
import requests
from typing import List, Dict, Optional
from urllib.parse import urlparse, quote


class PinterestAPIError(Exception):
    """Custom exception for Pinterest API errors"""
    pass


class PinterestAPI:
    """
    Pinterest API v5 client for fetching board pins and images.
    Requires Pinterest App credentials (App ID and App Secret).
    """
    
    def __init__(self):
        self.app_id = os.getenv('PINTEREST_APP_ID')
        self.app_secret = os.getenv('PINTEREST_APP_SECRET')
        
        if not self.app_id or not self.app_secret:
            raise PinterestAPIError(
                "Pinterest API credentials not found. "
                "Please set PINTEREST_APP_ID and PINTEREST_APP_SECRET environment variables."
            )
        
        self.base_url = "https://api.pinterest.com/v5"
        self.access_token: Optional[str] = None
    
    def get_oauth_url(self, redirect_uri: str, state: str = "random_state") -> str:
        """
        Generate OAuth authorization URL for user to grant access.
        
        Args:
            redirect_uri: The URI to redirect to after authorization
            state: Random string for CSRF protection
        
        Returns:
            Authorization URL for user to visit
        """
        scopes = "boards:read,pins:read,user_accounts:read"
        auth_url = (
            f"https://www.pinterest.com/oauth/?"
            f"client_id={self.app_id}&"
            f"redirect_uri={quote(redirect_uri)}&"
            f"response_type=code&"
            f"scope={scopes}&"
            f"state={state}"
        )
        return auth_url
    
    def exchange_code_for_token(self, code: str, redirect_uri: str) -> str:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect URI used in authorization
        
        Returns:
            Access token
        """
        token_url = f"{self.base_url}/oauth/token"
        
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'redirect_uri': redirect_uri
        }
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            response = requests.post(token_url, data=data, headers=headers, timeout=10)
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            return self.access_token
            
        except requests.RequestException as e:
            raise PinterestAPIError(f"Failed to exchange code for token: {str(e)}")
    
    def set_access_token(self, token: str):
        """Set the access token manually (for stored tokens)"""
        self.access_token = token
    
    def parse_board_id_from_url(self, board_url: str) -> str:
        """
        Extract board ID (username/board_name) from Pinterest board URL.
        
        Args:
            board_url: Full Pinterest board URL
        
        Returns:
            Board ID in format "username/board_name"
        """
        # Example URL: https://www.pinterest.com/username/board-name/
        parsed = urlparse(board_url)
        path_parts = [p for p in parsed.path.split('/') if p]
        
        if len(path_parts) < 2:
            raise PinterestAPIError(
                f"Invalid Pinterest board URL format. Expected format: "
                f"https://pinterest.com/username/board-name/"
            )
        
        # Board ID is username/board_name
        username = path_parts[0]
        board_name = path_parts[1]
        
        return f"{username}/{board_name}"
    
    def get_board_pins(self, board_id: str, page_size: int = 100) -> List[Dict]:
        """
        Fetch pins from a Pinterest board.
        
        Args:
            board_id: Board identifier in format "username/board_name"
            page_size: Number of pins to fetch (max 100)
        
        Returns:
            List of pin objects with image URLs and metadata
        """
        if not self.access_token:
            raise PinterestAPIError(
                "Access token not set. Please authenticate first using OAuth flow."
            )
        
        endpoint = f"{self.base_url}/boards/{board_id}/pins/"
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        params = {
            'page_size': min(page_size, 100)
        }
        
        all_pins = []
        bookmark = None
        
        try:
            while True:
                if bookmark:
                    params['bookmark'] = bookmark
                
                response = requests.get(endpoint, headers=headers, params=params, timeout=15)
                
                # Handle specific error cases
                if response.status_code == 401:
                    raise PinterestAPIError(
                        "Authentication failed. Access token may be expired or invalid. "
                        "Please re-authenticate."
                    )
                elif response.status_code == 403:
                    raise PinterestAPIError(
                        "Access forbidden. You may not have permission to access this board. "
                        "Ensure the board is owned by the authenticated account or is a shared group board."
                    )
                elif response.status_code == 404:
                    raise PinterestAPIError(
                        f"Board not found: {board_id}. Please check the board URL and ensure it exists."
                    )
                
                response.raise_for_status()
                
                data = response.json()
                items = data.get('items', [])
                all_pins.extend(items)
                
                # Check for next page
                bookmark = data.get('bookmark')
                if not bookmark or len(all_pins) >= page_size:
                    break
            
            return all_pins[:page_size]
            
        except requests.RequestException as e:
            raise PinterestAPIError(f"Failed to fetch board pins: {str(e)}")
    
    def extract_image_urls(self, pins: List[Dict], quality: str = 'original') -> List[str]:
        """
        Extract image URLs from pin objects.
        
        Args:
            pins: List of pin objects from get_board_pins()
            quality: Image quality to extract ('original', '1200x', '600x', '400x300', '150x150')
        
        Returns:
            List of image URLs
        """
        image_urls = []
        
        for pin in pins:
            try:
                # Navigate to images in media object
                media = pin.get('media', {})
                images = media.get('images', {})
                
                # Try to get requested quality, fallback to original
                image_data = images.get(quality) or images.get('original')
                
                if image_data and 'url' in image_data:
                    image_urls.append(image_data['url'])
                    
            except (KeyError, TypeError):
                # Skip pins with missing or malformed image data
                continue
        
        return image_urls
    
    def get_images_from_board_url(self, board_url: str, max_images: int = 30) -> List[str]:
        """
        Convenience method: Get image URLs directly from a Pinterest board URL.
        
        Args:
            board_url: Full Pinterest board URL
            max_images: Maximum number of images to fetch
        
        Returns:
            List of image URLs
        """
        board_id = self.parse_board_id_from_url(board_url)
        pins = self.get_board_pins(board_id, page_size=max_images)
        return self.extract_image_urls(pins, quality='original')


def get_pinterest_images_via_api(board_url: str, access_token: str, max_images: int = 30) -> List[str]:
    """
    Helper function to fetch Pinterest board images using the API.
    
    Args:
        board_url: Pinterest board URL
        access_token: Pinterest OAuth access token
        max_images: Maximum number of images to fetch
    
    Returns:
        List of image URLs
    """
    api = PinterestAPI()
    api.set_access_token(access_token)
    return api.get_images_from_board_url(board_url, max_images)
