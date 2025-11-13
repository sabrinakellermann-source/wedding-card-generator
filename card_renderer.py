from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Any
import io


def mm_to_pixels(mm: float, dpi: int = 300) -> int:
    """Convert millimeters to pixels at given DPI"""
    return int((mm / 25.4) * dpi)


def get_font_for_type(font_type: str, size_mm: float, dpi: int = 300) -> ImageFont.FreeTypeFont:
    """
    Get appropriate font for the given type.
    Falls back to default font if specific font not available.
    """
    # Convert point size to pixels (1 pt = 1/72 inch)
    size_px = int((size_mm / 25.4) * dpi * (1/72) * size_mm * 2)
    
    # Map font types to system fonts
    font_paths = {
        'Script': ['/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf',
                   '/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf'],
        'Serif': ['/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf',
                  '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf'],
        'Sans-Serif': ['/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
                       '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
    }
    
    # Try to load the appropriate font
    for font_path in font_paths.get(font_type, font_paths['Serif']):
        try:
            return ImageFont.truetype(font_path, size_px)
        except:
            continue
    
    # Ultimate fallback
    try:
        return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', size_px)
    except:
        return ImageFont.load_default()


def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def render_text_element(
    draw: ImageDraw.Draw, 
    element: Dict[str, Any], 
    dpi: int = 300
) -> None:
    """Render a text element on the card"""
    content = element.get('content', '')
    font_type = element.get('font', 'Serif')
    font_size = element.get('fontSize', 16)
    color = element.get('color', '#000000')
    position = element.get('position', {'x': 0, 'y': 0})
    
    x_px = mm_to_pixels(position['x'], dpi)
    y_px = mm_to_pixels(position['y'], dpi)
    
    font = get_font_for_type(font_type, font_size, dpi)
    rgb_color = hex_to_rgb(color)
    
    draw.text((x_px, y_px), content, fill=rgb_color, font=font)


def render_decorative_element(
    draw: ImageDraw.Draw, 
    element: Dict[str, Any], 
    dpi: int = 300
) -> None:
    """Render a decorative element on the card"""
    content = element.get('content', '')
    position = element.get('position', {'x': 0, 'y': 0})
    size = element.get('size', {'width': 10, 'height': 10})
    color = element.get('color', '#000000')
    
    x_px = mm_to_pixels(position['x'], dpi)
    y_px = mm_to_pixels(position['y'], dpi)
    width_px = mm_to_pixels(size['width'], dpi)
    height_px = mm_to_pixels(size['height'], dpi)
    
    rgb_color = hex_to_rgb(color)
    
    if content == 'heart-line':
        y_center = y_px + height_px // 2
        draw.line([(x_px, y_center), (x_px + width_px, y_center)], fill=rgb_color, width=2)
        heart_size = height_px
        heart_x = x_px + width_px // 2 - heart_size // 2
        draw.ellipse(
            [heart_x, y_px, heart_x + heart_size, y_px + heart_size],
            outline=rgb_color,
            width=2
        )
    
    elif content == 'floral-branch':
        # Draw elegant curved branch
        branch_x = x_px + width_px // 2
        points = []
        for i in range(10):
            t = i / 9.0
            curve_x = branch_x + int(width_px * 0.2 * (t - 0.5))
            curve_y = y_px + int(height_px * t)
            points.append((curve_x, curve_y))
        
        # Draw smooth branch curve
        for i in range(len(points) - 1):
            draw.line([points[i], points[i + 1]], fill=rgb_color, width=3)
        
        # Draw leaves along the branch
        num_leaves = 5
        for i in range(num_leaves):
            t = (i + 0.5) / num_leaves
            leaf_y = y_px + int(height_px * t)
            leaf_x = branch_x + int(width_px * 0.2 * (t - 0.5))
            
            # Left leaf
            left_pts = [
                (leaf_x, leaf_y),
                (leaf_x - int(width_px * 0.15), leaf_y - int(height_px * 0.04)),
                (leaf_x - int(width_px * 0.1), leaf_y)
            ]
            draw.polygon(left_pts, fill=rgb_color)
            
            # Right leaf
            right_pts = [
                (leaf_x, leaf_y),
                (leaf_x + int(width_px * 0.15), leaf_y + int(height_px * 0.04)),
                (leaf_x + int(width_px * 0.1), leaf_y)
            ]
            draw.polygon(right_pts, fill=rgb_color)
    
    elif content == 'geometric-border':
        draw.rectangle(
            [x_px, y_px, x_px + width_px, y_px + height_px],
            outline=rgb_color,
            width=2
        )
    
    elif content == 'leaf-accent':
        points = [
            (x_px + width_px // 2, y_px),
            (x_px + width_px, y_px + height_px // 2),
            (x_px + width_px // 2, y_px + height_px),
            (x_px, y_px + height_px // 2)
        ]
        draw.polygon(points, outline=rgb_color, width=2)
    
    elif content == 'dots-pattern':
        dot_size = 3
        spacing = 10
        for i in range(int(width_px // spacing)):
            dot_x = x_px + i * spacing
            draw.ellipse(
                [dot_x, y_px, dot_x + dot_size, y_px + dot_size],
                fill=rgb_color
            )


def render_card_design(card_json: Dict[str, Any], dpi: int = 300) -> Image.Image:
    """
    Render a card design JSON to a PIL Image.
    
    Args:
        card_json: Card design as dictionary
        dpi: Dots per inch for rendering (default: 300)
    
    Returns:
        PIL Image of the rendered card
    """
    card_info = card_json.get('card', {})
    width_mm = card_info.get('width', 148)
    height_mm = card_info.get('height', 105)
    bg_color = card_info.get('backgroundColor', '#FFFFFF')
    
    width_px = mm_to_pixels(width_mm, dpi)
    height_px = mm_to_pixels(height_mm, dpi)
    
    bg_rgb = hex_to_rgb(bg_color)
    
    image = Image.new('RGB', (width_px, height_px), bg_rgb)
    draw = ImageDraw.Draw(image)
    
    elements = card_json.get('elements', [])
    for element in elements:
        elem_type = element.get('type')
        
        if elem_type == 'text':
            render_text_element(draw, element, dpi)
        elif elem_type == 'decorative':
            render_decorative_element(draw, element, dpi)
    
    return image


def render_card_to_bytes(card_json: Dict[str, Any], format: str = 'PNG') -> bytes:
    """
    Render card design to image bytes.
    
    Args:
        card_json: Card design as dictionary
        format: Image format (PNG, JPEG, etc.)
    
    Returns:
        Image bytes
    """
    image = render_card_design(card_json)
    
    img_bytes = io.BytesIO()
    image.save(img_bytes, format=format)
    img_bytes.seek(0)
    
    return img_bytes.getvalue()
