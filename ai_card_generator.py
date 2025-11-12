# Reference: python_gemini_ai_integrations blueprint
import os
import json
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from google import genai
from google.genai import types


AI_INTEGRATIONS_GEMINI_API_KEY = os.environ.get("AI_INTEGRATIONS_GEMINI_API_KEY")
AI_INTEGRATIONS_GEMINI_BASE_URL = os.environ.get("AI_INTEGRATIONS_GEMINI_BASE_URL")

# Using Replit's AI Integrations service for Gemini
client = genai.Client(
    api_key=AI_INTEGRATIONS_GEMINI_API_KEY,
    http_options={
        'api_version': '',
        'base_url': AI_INTEGRATIONS_GEMINI_BASE_URL   
    }
)


def is_rate_limit_error(exception: BaseException) -> bool:
    """Check if the exception is a rate limit or quota violation error."""
    error_msg = str(exception)
    return (
        "429" in error_msg 
        or "RATELIMIT_EXCEEDED" in error_msg
        or "quota" in error_msg.lower() 
        or "rate limit" in error_msg.lower()
        or (hasattr(exception, 'status') and exception.status == 429)
    )


@retry(
    stop=stop_after_attempt(7),
    wait=wait_exponential(multiplier=1, min=2, max=128),
    retry=retry_if_exception(is_rate_limit_error),
    reraise=True
)
def analyze_single_image(image_url: str) -> str:
    """
    Step 2a: Image-to-Description (The "Eyes")
    Analyze a single image and extract detailed description including colors, mood, style, and typography.
    
    Args:
        image_url: URL of the image to analyze
    
    Returns:
        Detailed description of the image
    
    Raises:
        Exception: If analysis fails after retries
    """
    prompt = """You are an expert art descriptor. Describe the following image in detail as if for a blind person. 
Focus on:
- Color palette (with hex codes if possible)
- Mood and emotional tone
- Style (e.g., rustic, modern, minimalist, bohemian, classic, romantic)
- Key objects and motifs
- Textures and materials
- Any visible typography or text elements
- Overall composition and layout

Be specific and detailed in your description."""
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            prompt,
            types.Part.from_uri(
                file_uri=image_url,
                mime_type="image/jpeg"
            )
        ]
    )
    return response.text or ""


def analyze_images_batch(image_urls: List[str], progress_callback=None) -> List[str]:
    """
    Analyze multiple images concurrently with rate limiting and automatic retries.
    
    Args:
        image_urls: List of image URLs to analyze (will be sampled to top 10 for performance)
        progress_callback: Optional callback function for progress updates
    
    Returns:
        List of image descriptions
    
    Raises:
        Exception: If too many images fail analysis
    """
    # Sample top 10 images for performance (<30s target)
    sampled_urls = image_urls[:10]
    
    def process_image(i: int, url: str) -> tuple[int, str]:
        try:
            description = analyze_single_image(url)
            if progress_callback:
                # Calculate progress as percentage (0-40 for image analysis phase)
                progress_pct = int((i + 1) / len(sampled_urls) * 40)
                progress_callback(f"Analyzing image {i + 1}/{len(sampled_urls)}...", progress_pct, 100)
            return (i, description)
        except Exception as e:
            print(f"Error analyzing image {url}: {str(e)}")
            if progress_callback:
                progress_pct = int((i + 1) / len(sampled_urls) * 40)
                progress_callback(f"Analyzing image {i + 1}/{len(sampled_urls)}...", progress_pct, 100)
            raise
    
    descriptions: List[str] = [""] * len(sampled_urls)
    failed_count = 0
    
    # Use ThreadPoolExecutor with max_workers=2 to limit concurrency
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(process_image, i, url): i for i, url in enumerate(sampled_urls)}
        for future in as_completed(futures):
            try:
                idx, result = future.result()
                descriptions[idx] = result
            except Exception as e:
                failed_count += 1
                print(f"Failed to analyze image after retries: {str(e)}")
                if failed_count > len(sampled_urls) // 2:
                    raise Exception(f"Too many image analysis failures ({failed_count}/{len(sampled_urls)})")
    
    return descriptions


@retry(
    stop=stop_after_attempt(7),
    wait=wait_exponential(multiplier=1, min=2, max=128),
    retry=retry_if_exception(is_rate_limit_error),
    reraise=True
)
def synthesize_design_brief(image_descriptions: List[str]) -> str:
    """
    Step 2b: Description-to-Brief (The "Synthesizer")
    Synthesize multiple image descriptions into a cohesive design brief.
    
    Args:
        image_descriptions: List of detailed image descriptions
    
    Returns:
        A cohesive design brief for wedding invitation
    """
    combined_descriptions = "\n\n---\n\n".join([
        f"Image {i+1}: {desc}" 
        for i, desc in enumerate(image_descriptions) if desc
    ])
    
    prompt = f"""You are a design director. Read the following collection of image descriptions from a Pinterest wedding inspiration board and synthesize them into a single, coherent design brief for a wedding invitation.

IMAGE DESCRIPTIONS:
{combined_descriptions}

Your output should include:
1. A short paragraph (3-4 sentences) summarizing the overall aesthetic and mood
2. A list of 3-5 key motifs or visual elements that should be incorporated
3. A primary color palette of exactly 5 hex codes that best represent this wedding vision
4. Typography recommendations (e.g., elegant script, modern sans-serif, classic serif)

Be specific and design-focused. This brief will be used to create an actual wedding invitation."""
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    
    return response.text or ""


@retry(
    stop=stop_after_attempt(7),
    wait=wait_exponential(multiplier=1, min=2, max=128),
    retry=retry_if_exception(is_rate_limit_error),
    reraise=True
)
def generate_card_design_json(design_brief: str) -> Dict[str, Any]:
    """
    Step 2c: Brief-to-Card (The "Designer")
    Generate a structured JSON design based on the design brief.
    
    Args:
        design_brief: The synthesized design brief
    
    Returns:
        Structured JSON object representing the card design
    """
    
    # Few-shot examples of kartenmacherei.de style cards
    example_cards = """
EXAMPLE 1 - Modern Minimalist:
{
  "card": {
    "width": 148,
    "height": 105,
    "backgroundColor": "#FFFFFF"
  },
  "elements": [
    {
      "type": "text",
      "content": "Einladung zur Hochzeit",
      "font": "Sans-Serif",
      "fontSize": 18,
      "color": "#2C2C2C",
      "position": {"x": 15, "y": 20}
    },
    {
      "type": "text",
      "content": "Emma & Lukas",
      "font": "Serif",
      "fontSize": 32,
      "color": "#000000",
      "position": {"x": 15, "y": 45}
    },
    {
      "type": "text",
      "content": "14. September 2025",
      "font": "Sans-Serif",
      "fontSize": 14,
      "color": "#666666",
      "position": {"x": 15, "y": 75}
    }
  ]
}

EXAMPLE 2 - Romantic Boho:
{
  "card": {
    "width": 148,
    "height": 105,
    "backgroundColor": "#F9F5F0"
  },
  "elements": [
    {
      "type": "text",
      "content": "Save the Date",
      "font": "Script",
      "fontSize": 22,
      "color": "#8B7355",
      "position": {"x": 20, "y": 25}
    },
    {
      "type": "text",
      "content": "Sophie & Maximilian",
      "font": "Script",
      "fontSize": 28,
      "color": "#D4AF37",
      "position": {"x": 20, "y": 50}
    },
    {
      "type": "decorative",
      "content": "floral-branch",
      "position": {"x": 110, "y": 15},
      "size": {"width": 30, "height": 40},
      "color": "#C9A88E"
    }
  ]
}

EXAMPLE 3 - Classic Elegant:
{
  "card": {
    "width": 148,
    "height": 105,
    "backgroundColor": "#FAF8F3"
  },
  "elements": [
    {
      "type": "text",
      "content": "Wir heiraten",
      "font": "Serif",
      "fontSize": 16,
      "color": "#4A4A4A",
      "position": {"x": 25, "y": 18}
    },
    {
      "type": "text",
      "content": "Anna & Markus",
      "font": "Script",
      "fontSize": 36,
      "color": "#2C3E50",
      "position": {"x": 25, "y": 45}
    },
    {
      "type": "decorative",
      "content": "heart-line",
      "position": {"x": 60, "y": 75},
      "size": {"width": 25, "height": 8},
      "color": "#C5A48A"
    },
    {
      "type": "text",
      "content": "20.06.2025",
      "font": "Serif",
      "fontSize": 14,
      "color": "#4A4A4A",
      "position": {"x": 52, "y": 88}
    }
  ]
}
"""
    
    prompt = f"""You are a senior graphic designer at kartenmacherei.de, a premium German wedding stationery company.

YOUR TASK:
Create a new wedding invitation design that captures the aesthetic described in the design brief below. Your output MUST be a single, valid JSON object that follows our exact schema.

DESIGN BRIEF TO FOLLOW:
{design_brief}

CRITICAL INSTRUCTIONS - READ CAREFULLY:
1. COLORS: You MUST use ONLY the 5 hex color codes listed in the design brief's color palette. Do not use colors from the examples below.
2. MOTIFS: Incorporate the key motifs and visual elements mentioned in the design brief using our available decorative elements.
3. TYPOGRAPHY: Match the font choices to the typography style described in the design brief (elegant script → "Script", modern → "Sans-Serif", classic → "Serif").
4. MOOD: The overall aesthetic (background color, spacing, element arrangement) should reflect the mood described in the design brief.
5. EXAMPLES ARE FORMAT ONLY: The examples below show the correct JSON structure, but DO NOT copy their colors, text, or specific design choices.

AVAILABLE FONTS:
- "Serif": Classic, elegant, timeless
- "Sans-Serif": Modern, clean, minimal
- "Script": Romantic, flowing, handwritten feel

AVAILABLE DECORATIVE ELEMENTS (use these to represent the brief's motifs):
- "floral-branch": Delicate botanical accent
- "heart-line": Simple romantic divider
- "geometric-border": Modern minimal frame
- "leaf-accent": Natural organic detail
- "dots-pattern": Subtle decorative dots

OUTPUT REQUIREMENTS:
1. Your ENTIRE response must be ONLY the JSON object - no additional text before or after
2. Card dimensions: width=148mm, height=105mm (A6 landscape format)
3. Include 2-5 text elements (e.g., "Save the Date", couple names, date, location)
4. May include 0-2 decorative elements that match the brief's motifs
5. All positions in millimeters from top-left corner
6. All colors MUST come from the design brief's 5-color palette
7. Font sizes: 12-40 for readability
8. Choose background color from the brief's palette (usually the lightest or most neutral color)

FORMAT REFERENCE EXAMPLES (structure only - create your own content based on the brief):
{example_cards}

Now generate the JSON wedding invitation design that brings the design brief to life:"""
    
    response = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json"
        )
    )
    
    try:
        card_json = json.loads(response.text or "{}")
        return card_json
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {str(e)}")
        print(f"Response text: {response.text}")
        raise Exception("Failed to generate valid JSON card design")


def generate_wedding_card_from_pinterest(
    image_urls: List[str], 
    progress_callback=None
) -> Dict[str, Any]:
    """
    Complete pipeline to generate a wedding card design from Pinterest images.
    
    Args:
        image_urls: List of Pinterest image URLs
        progress_callback: Optional callback for progress updates
    
    Returns:
        Complete card design as JSON object
    """
    # Step 1: Analyze images (already done via pinterest_scraper)
    
    # Step 2a: Image-to-Description
    if progress_callback:
        progress_callback("Analyzing images...", 0, 100)
    
    descriptions = analyze_images_batch(
        image_urls, 
        progress_callback
    )
    
    # Step 2b: Description-to-Brief
    if progress_callback:
        progress_callback("Creating design brief...", 50, 100)
    
    design_brief = synthesize_design_brief(descriptions)
    
    # Step 2c: Brief-to-Card
    if progress_callback:
        progress_callback("Generating card design...", 75, 100)
    
    card_design = generate_card_design_json(design_brief)
    
    # Add the design brief to the output for reference
    card_design["_design_brief"] = design_brief
    card_design["_source_images_count"] = len(image_urls)
    
    if progress_callback:
        progress_callback("Complete!", 100, 100)
    
    return card_design
