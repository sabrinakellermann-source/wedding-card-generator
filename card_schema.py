from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, field_validator


class Position(BaseModel):
    """Position in millimeters from top-left corner"""
    x: float = Field(..., ge=0, le=200)
    y: float = Field(..., ge=0, le=200)


class Size(BaseModel):
    """Size in millimeters"""
    width: float = Field(..., gt=0, le=100)
    height: float = Field(..., gt=0, le=100)


class CardDimensions(BaseModel):
    """Card dimensions and background - enforces A6 landscape format"""
    width: float = Field(148, description="Card width in mm (A6 landscape)", ge=148, le=148)
    height: float = Field(105, description="Card height in mm (A6 landscape)", ge=105, le=105)
    backgroundColor: str = Field(..., pattern=r'^#[0-9A-Fa-f]{6}$')


class TextElement(BaseModel):
    """Text element on the card"""
    type: str = Field("text", pattern=r'^text$')
    content: str = Field(..., min_length=1, max_length=200)
    font: str = Field(..., pattern=r'^(Serif|Sans-Serif|Script)$')
    fontSize: int = Field(..., ge=12, le=40, description="Font size in points (12-40 for readability)")
    color: str = Field(..., pattern=r'^#[0-9A-Fa-f]{6}$')
    position: Position


class DecorativeElement(BaseModel):
    """Decorative element on the card"""
    type: str = Field("decorative", pattern=r'^decorative$')
    content: str = Field(
        ..., 
        pattern=r'^(floral-branch|heart-line|geometric-border|leaf-accent|dots-pattern)$'
    )
    position: Position
    size: Size
    color: str = Field(..., pattern=r'^#[0-9A-Fa-f]{6}$')


class ImageElement(BaseModel):
    """Image element on the card (legacy support)"""
    type: str = Field("image", pattern=r'^image$')
    src: str
    position: Position
    size: Size


class CardDesign(BaseModel):
    """Complete wedding card design schema with enforced element validation"""
    card: CardDimensions
    elements: List[Union[TextElement, DecorativeElement, ImageElement]] = Field(..., min_length=1, max_length=10)
    
    @field_validator('elements')
    @classmethod
    def validate_elements(cls, v):
        """Validate that elements are of correct types and counts"""
        if not v:
            raise ValueError("Card must have at least one element")
        
        text_count = sum(1 for el in v if isinstance(el, (dict, TextElement)) and (el.get('type') if isinstance(el, dict) else el.type) == 'text')
        decorative_count = sum(1 for el in v if isinstance(el, (dict, DecorativeElement)) and (el.get('type') if isinstance(el, dict) else el.type) == 'decorative')
        
        if text_count < 2:
            raise ValueError("Card must have at least 2 text elements")
        if text_count > 5:
            raise ValueError("Card must have at most 5 text elements")
        if decorative_count > 2:
            raise ValueError("Card must have at most 2 decorative elements")
        
        return v


def validate_card_design(card_json: Dict[str, Any]) -> bool:
    """
    Validate a card design JSON against the schema with full field-level enforcement.
    
    Args:
        card_json: Card design as dictionary
    
    Returns:
        True if valid
    
    Raises:
        ValueError: If validation fails
    """
    try:
        # Remove internal metadata fields before validation
        clean_json = {k: v for k, v in card_json.items() if not k.startswith('_')}
        
        # Parse and validate each element individually to enforce field constraints
        validated_elements = []
        elements = clean_json.get('elements', [])
        
        for i, element in enumerate(elements):
            elem_type = element.get('type')
            
            if elem_type == 'text':
                validated_elements.append(TextElement(**element))
            elif elem_type == 'decorative':
                validated_elements.append(DecorativeElement(**element))
            elif elem_type == 'image':
                validated_elements.append(ImageElement(**element))
            else:
                raise ValueError(f"Unknown element type at index {i}: {elem_type}")
        
        # Now validate the complete card design with parsed elements
        card_data = {
            'card': clean_json.get('card'),
            'elements': validated_elements
        }
        CardDesign(**card_data)
        
        return True
        
    except Exception as e:
        raise ValueError(f"Card design validation failed: {str(e)}")


def get_schema_example() -> Dict[str, Any]:
    """
    Get an example card design that conforms to the schema.
    
    Returns:
        Example card design JSON
    """
    return {
        "card": {
            "width": 148,
            "height": 105,
            "backgroundColor": "#F5F3F0"
        },
        "elements": [
            {
                "type": "text",
                "content": "Einladung zur Hochzeit",
                "font": "Serif",
                "fontSize": 24,
                "color": "#4A4A4A",
                "position": {"x": 10, "y": 15}
            },
            {
                "type": "text",
                "content": "Anna & Markus",
                "font": "Script",
                "fontSize": 36,
                "color": "#C5A48A",
                "position": {"x": 10, "y": 40}
            },
            {
                "type": "decorative",
                "content": "heart-line",
                "position": {"x": 60, "y": 75},
                "size": {"width": 25, "height": 8},
                "color": "#C5A48A"
            }
        ]
    }
