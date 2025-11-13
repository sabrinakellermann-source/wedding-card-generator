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
    
    Downloads the image and sends it as base64 data to bypass Pinterest's robots.txt restrictions.
    
    Args:
        image_url: URL of the image to analyze
    
    Returns:
        Detailed description of the image
    
    Raises:
        Exception: If analysis fails after retries
    """
    print("[DEBUG v2.0] analyze_single_image called - using types.Part(inline_data=types.Blob()) API")
    import requests
    
    # Create a fresh Gemini client per request for thread safety
    thread_client = genai.Client(
        api_key=AI_INTEGRATIONS_GEMINI_API_KEY,
        http_options={
            'api_version': '',
            'base_url': AI_INTEGRATIONS_GEMINI_BASE_URL   
        }
    )
    
    # Download the image (bypasses Pinterest robots.txt blocking of Gemini)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(image_url, headers=headers, timeout=10)
    response.raise_for_status()
    
    # Determine MIME type from URL or content
    mime_type = "image/jpeg"
    if ".png" in image_url.lower():
        mime_type = "image/png"
    elif ".webp" in image_url.lower():
        mime_type = "image/webp"
    
    prompt = """You are an expert wedding design consultant analyzing a Pinterest inspiration image. Extract specific design elements:

COLORS (CRITICAL - Be Precise):
- Identify the 3-5 dominant colors in the image
- For each color, provide the exact hex code (e.g., #F5E6D3, #8B7355, #2C5F2D)
- Note if colors are warm/cool, muted/vibrant, pastel/saturated

STYLE & MOOD:
- Aesthetic category: modern minimalist, rustic boho, classic elegant, romantic vintage, or describe specifically
- Emotional tone: sophisticated, whimsical, intimate, grand, serene, joyful, etc.

VISUAL ELEMENTS:
- Key motifs: florals, geometric shapes, botanical elements, hearts, ribbons, etc.
- Typography style if visible: script/cursive, serif, sans-serif, ornate, simple
- Textures: watercolor, linen, gold foil, matte, glossy, hand-drawn

LAYOUT & COMPOSITION:
- Symmetrical or asymmetrical
- Minimalist (lots of white space) or decorated
- Centered or offset arrangement

Be extremely specific about colors - they are the most important element."""
    
    api_response = thread_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            prompt,
            types.Part(
                inline_data=types.Blob(
                    mime_type=mime_type,
                    data=response.content
                )
            )
        ]
    )
    return api_response.text or ""


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
                try:
                    # Calculate progress as percentage (0-40 for image analysis phase)
                    progress_pct = int((i + 1) / len(sampled_urls) * 40)
                    progress_callback(f"Analyzing image {i + 1}/{len(sampled_urls)}...", progress_pct, 100)
                except Exception:
                    # Silently ignore Streamlit NoSessionContext errors from worker threads
                    pass
            return (i, description)
        except Exception as e:
            import traceback
            error_details = f"Error analyzing image {url}: {type(e).__name__}: {str(e)}"
            print(error_details)
            print(f"Full traceback:\n{traceback.format_exc()}")
            if progress_callback:
                try:
                    progress_pct = int((i + 1) / len(sampled_urls) * 40)
                    progress_callback(f"Analyzing image {i + 1}/{len(sampled_urls)}...", progress_pct, 100)
                except Exception:
                    # Silently ignore Streamlit NoSessionContext errors from worker threads
                    pass
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
    
    prompt = f"""You are a design director at a premium wedding stationery company. Analyze these Pinterest board descriptions and create a precise design brief for a wedding invitation.

IMAGE DESCRIPTIONS FROM PINTEREST BOARD:
{combined_descriptions}

Create a structured design brief with these EXACT sections:

**AESTHETIC SUMMARY:**
Write 2-3 sentences capturing the overall visual style, mood, and wedding vibe.

**COLOR PALETTE (EXACTLY 5 HEX CODES):**
List exactly 5 hex codes that appear most frequently across these images. Choose:
- 1 background color (usually lightest/neutral: white, cream, blush, sage, etc.)
- 2-3 primary accent colors (the dominant aesthetic colors)
- 1-2 secondary/text colors (darker for readability)

Format: #HEXCODE - description
Example:
- #FFFFFF - Clean white background
- #D4AF37 - Warm gold accent
- #8B7355 - Earthy brown
- #F5E6D3 - Soft cream
- #2C2C2C - Charcoal text

**KEY MOTIFS (3-5 elements):**
List specific visual elements that appear repeatedly:
- florals, botanical, geometric, hearts, ribbons, watercolor, gold accents, etc.

**TYPOGRAPHY STYLE:**
Recommend 1-2 font combinations based on the aesthetic:
- "Script" for romantic/elegant/flowing styles
- "Serif" for classic/traditional/sophisticated styles
- "Sans-Serif" for modern/minimal/clean styles

Be extremely specific about colors - extract actual hex codes from the images."""
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    
    design_brief = response.text or ""
    print("\n" + "="*80)
    print("DESIGN BRIEF GENERATED:")
    print("="*80)
    print(design_brief)
    print("="*80 + "\n")
    
    return design_brief


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
    
    prompt = f"""You are a senior graphic designer at kartenmacherei.de creating a wedding invitation that PERFECTLY matches this Pinterest-inspired design brief.

===== DESIGN BRIEF (YOUR ONLY REFERENCE) =====
{design_brief}
===============================================

MANDATORY RULES - VIOLATIONS WILL BE REJECTED:

1. **COLORS - USE ONLY THESE 5 HEX CODES:**
   - Extract the exact 5 hex codes from the COLOR PALETTE section above
   - Use ZERO colors outside this palette
   - Background: Use the lightest color from the palette
   - Text: Use darker colors for readability
   - Decorative elements: Use accent colors from the palette
   - DO NOT use colors from the examples below (#FFFFFF, #2C2C2C, etc. are examples only)

2. **AESTHETIC MATCH:**
   - If brief says "rustic boho" → use warm earthy tones, organic spacing, script fonts
   - If brief says "modern minimal" → use lots of white space, sans-serif fonts, geometric decorative elements
   - If brief says "classic elegant" → use traditional serif fonts, symmetrical layout, refined decorative elements
   - If brief says "romantic vintage" → use soft colors, script fonts, floral decorative elements

3. **MOTIFS:**
   - Brief mentions "florals" → use floral-branch or leaf-accent decorative element
   - Brief mentions "geometric" → use geometric-border or dots-pattern
   - Brief mentions "hearts/romantic" → use heart-line decorative element

4. **TYPOGRAPHY:**
   - Brief recommends "Script" → Use "Script" font for couple names
   - Brief recommends "Serif" → Use "Serif" font for formal text
   - Brief recommends "Sans-Serif" → Use "Sans-Serif" for modern clean look

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
        print("\n" + "="*80)
        print("CARD DESIGN JSON GENERATED:")
        print("="*80)
        print(json.dumps(card_json, indent=2))
        print("="*80 + "\n")
        
        # Validate palette adherence (extract colors from brief and card JSON)
        import re
        brief_colors = set(re.findall(r'#[0-9A-Fa-f]{6}', design_brief))
        card_colors = set()
        
        # Extract all colors from the card JSON
        if 'card' in card_json and 'backgroundColor' in card_json['card']:
            card_colors.add(card_json['card']['backgroundColor'].upper())
        if 'elements' in card_json:
            for elem in card_json['elements']:
                if 'color' in elem:
                    card_colors.add(elem['color'].upper())
        
        # Normalize for comparison
        brief_colors = {c.upper() for c in brief_colors}
        
        # Check if card colors are subset of brief colors
        extra_colors = card_colors - brief_colors
        if extra_colors:
            print(f"\n⚠️ WARNING: Card uses colors not in brief palette!")
            print(f"Brief palette: {sorted(brief_colors)}")
            print(f"Card colors: {sorted(card_colors)}")
            print(f"Extra colors: {sorted(extra_colors)}\n")
        else:
            print(f"\n✅ VALIDATION PASSED: All {len(card_colors)} card colors match brief palette\n")
        
        return card_json
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {str(e)}")
        print(f"Response text: {response.text}")
        raise Exception("Failed to generate valid JSON card design")


def create_image_generation_prompt(design_brief: str, card_json: Dict[str, Any]) -> str:
    """
    Convert design brief and card JSON into an image generation prompt.
    
    Args:
        design_brief: The textual design brief
        card_json: The structured card design JSON
        
    Returns:
        Image generation prompt string
    """
    import re
    
    # Extract key information from brief
    colors = re.findall(r'#[0-9A-Fa-f]{6}', design_brief)
    
    # Extract text content from card JSON
    text_elements = []
    for elem in card_json.get('elements', []):
        if elem.get('type') == 'text':
            text_elements.append(elem.get('content', ''))
    
    sample_text = ' / '.join(text_elements[:3]) if text_elements else 'Wedding Invitation'
    
    prompt = f"""Create a beautiful wedding invitation card in A6 landscape format (148mm × 105mm).

AESTHETIC & STYLE:
{design_brief}

DESIGN REQUIREMENTS:
- Card dimensions: 148mm wide × 105mm tall (landscape orientation)
- Include the text: "{sample_text}"
- Match the color palette EXACTLY: {', '.join(colors[:5])}
- High-quality print design, 300 DPI
- Elegant, professional wedding stationery aesthetic
- DO NOT include any photo borders, frames, or mockup elements - just the flat card design
- The design should be print-ready, as if viewed from directly above

STYLE NOTES:
- If the brief mentions "watercolor florals" → include soft, delicate botanical watercolor illustrations
- If the brief mentions "Script" typography → use elegant flowing calligraphic fonts
- If the brief mentions "Serif" typography → use classic traditional fonts
- If the brief mentions "modern minimal" → use clean lines and lots of white space
- If the brief mentions "rustic boho" → use earthy organic elements
- If the brief mentions "classic elegant" → use refined traditional design

OUTPUT: A flat, print-ready wedding invitation card design (not a mockup, just the card itself)"""
    
    return prompt


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=64),
    retry=retry_if_exception(is_rate_limit_error),
    reraise=True
)
def generate_wedding_card_image(prompt: str) -> str:
    """
    Generate a wedding invitation image using Gemini 2.5 Flash Image (nano banana).
    
    Args:
        prompt: Image generation prompt describing the wedding invitation
        
    Returns:
        File path to the saved image
    """
    import base64
    from pathlib import Path
    from datetime import datetime
    
    print("[IMAGE GENERATION] Calling Gemini 2.5 Flash Image (nano banana)...")
    
    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"]
        )
    )
    
    if not response.candidates:
        raise ValueError("No candidates in response from image generation")
    
    candidate = response.candidates[0]
    if not candidate.content or not candidate.content.parts:
        raise ValueError("No content parts in image generation response")
    
    # Extract and aggregate all image parts from response (handles multi-part responses)
    all_image_bytes = []
    mime_type = "image/png"
    
    for part in candidate.content.parts:
        if hasattr(part, 'inline_data') and part.inline_data:
            mime_type = part.inline_data.mime_type or mime_type
            image_data = part.inline_data.data
            
            # Handle image data from Gemini
            # Based on testing: Gemini returns raw image bytes directly
            if isinstance(image_data, bytes):
                all_image_bytes.append(image_data)
                print(f"[IMAGE GENERATION] Received {len(image_data)} bytes from Gemini (raw image part)")
            elif isinstance(image_data, str):
                # If it's a string, it's base64-encoded - decode it
                decoded_bytes = base64.b64decode(image_data)
                all_image_bytes.append(decoded_bytes)
                print(f"[IMAGE GENERATION] Decoded base64 string ({len(image_data)} chars → {len(decoded_bytes)} bytes)")
            else:
                raise ValueError(f"Unexpected image data type: {type(image_data)}")
    
    if not all_image_bytes:
        raise ValueError("No image data found in Gemini response")
    
    # Concatenate all parts (handles multi-part streaming responses)
    image_bytes = b''.join(all_image_bytes)
    print(f"[IMAGE GENERATION] Aggregated {len(all_image_bytes)} part(s) → {len(image_bytes)} total bytes")
    
    # Determine file extension from MIME type - support PNG, JPEG, WebP
    mime_lower = mime_type.lower()
    if "png" in mime_lower:
        ext = "png"
    elif "jpeg" in mime_lower or "jpg" in mime_lower:
        ext = "jpg"
    elif "webp" in mime_lower:
        ext = "webp"
    else:
        # Unsupported format - try to detect from bytes or default to PNG
        print(f"[IMAGE GENERATION] ⚠️ Unsupported MIME type {mime_type}")
        if image_bytes.startswith(b'\x89PNG'):
            ext = "png"
        elif image_bytes.startswith(b'\xff\xd8\xff'):
            ext = "jpg"
        elif image_bytes.startswith(b'RIFF') and b'WEBP' in image_bytes[:20]:
            ext = "webp"
        else:
            raise ValueError(f"Unsupported image format: {mime_type} and unable to detect from bytes")
    
    # Save image to file
    output_dir = Path("generated_wedding_cards")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"wedding_card_{timestamp}.{ext}"
    
    output_path.write_bytes(image_bytes)
    
    # Validate the saved image using PIL and convert WebP to PNG if needed
    try:
        from PIL import Image
        with Image.open(output_path) as img:
            img.verify()  # Verify it's a valid image
        
        # If it's WebP, convert to PNG for better Streamlit compatibility
        if ext == "webp":
            print(f"[IMAGE GENERATION] Converting WebP to PNG for better compatibility...")
            with Image.open(output_path) as img:
                img.load()  # Load after verify (verify invalidates the image)
                png_path = output_path.with_suffix('.png')
                img.save(png_path, 'PNG')
            output_path.unlink()  # Delete the WebP file
            output_path = png_path
            print(f"[IMAGE GENERATION] ✅ Converted to PNG: {output_path}")
        
        print(f"[IMAGE GENERATION] ✅ Saved and validated AI-generated image: {output_path} ({len(image_bytes)} bytes)")
        return str(output_path)
    except Exception as validation_error:
        # Image is corrupted - delete it and raise error
        output_path.unlink(missing_ok=True)
        print(f"[IMAGE GENERATION] ❌ Image validation failed: {validation_error}")
        raise ValueError(f"Generated image failed validation: {validation_error}")


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
        Complete card design as JSON object with AI-generated image path
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
        progress_callback("Creating design brief...", 40, 100)
    
    design_brief = synthesize_design_brief(descriptions)
    
    # Step 2c: Brief-to-Card JSON (for validation - no metadata yet)
    if progress_callback:
        progress_callback("Generating design structure...", 60, 100)
    
    card_design = generate_card_design_json(design_brief)
    
    # Step 2d: RENDER FINAL CARD WITH AI IMAGE GENERATION (nano banana)
    if progress_callback:
        progress_callback("Rendering your beautiful wedding invitation with AI...", 80, 100)
    
    # Create image generation prompt from the design brief
    image_prompt = create_image_generation_prompt(design_brief, card_design)
    
    print("\n" + "="*80)
    print("IMAGE GENERATION PROMPT:")
    print("="*80)
    print(image_prompt)
    print("="*80 + "\n")
    
    # Generate the actual wedding invitation image
    generated_image_path = None
    image_generation_error = None
    
    try:
        generated_image_path = generate_wedding_card_image(image_prompt)
    except Exception as e:
        print(f"⚠️ Image generation failed: {str(e)}")
        print("Falling back to JSON-only output")
        image_generation_error = str(e)
    
    # Create result with metadata (separate from validated card design)
    result = {
        "card": card_design.get("card"),
        "elements": card_design.get("elements"),
        # Metadata fields (not part of schema validation)
        "_design_brief": design_brief,
        "_source_images_count": len(image_urls),
        "_image_generation_prompt": image_prompt,
        "_rendering_method": "ai_generated",
        "_generated_image_path": generated_image_path,
    }
    
    if image_generation_error:
        result["_image_generation_error"] = image_generation_error
    
    if progress_callback:
        progress_callback("Complete!", 100, 100)
    
    return result
