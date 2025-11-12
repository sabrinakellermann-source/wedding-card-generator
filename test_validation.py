"""Test script to verify schema validation is working correctly"""
from card_schema import validate_card_design

# Test 1: Valid design
print("Test 1: Valid design...")
valid_design = {
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
        }
    ]
}

try:
    validate_card_design(valid_design)
    print("✓ Valid design passed validation\n")
except Exception as e:
    print(f"✗ Valid design failed: {e}\n")

# Test 2: Invalid font size (too large)
print("Test 2: Invalid font size (too large)...")
invalid_font_size = {
    "card": {
        "width": 148,
        "height": 105,
        "backgroundColor": "#F5F3F0"
    },
    "elements": [
        {
            "type": "text",
            "content": "Test",
            "font": "Serif",
            "fontSize": 100,  # Invalid: too large
            "color": "#4A4A4A",
            "position": {"x": 10, "y": 15}
        },
        {
            "type": "text",
            "content": "Test 2",
            "font": "Serif",
            "fontSize": 24,
            "color": "#4A4A4A",
            "position": {"x": 10, "y": 40}
        }
    ]
}

try:
    validate_card_design(invalid_font_size)
    print("✗ Invalid font size PASSED validation (SHOULD HAVE FAILED)\n")
except Exception as e:
    print(f"✓ Invalid font size correctly rejected: {e}\n")

# Test 3: Invalid font name
print("Test 3: Invalid font name...")
invalid_font_name = {
    "card": {
        "width": 148,
        "height": 105,
        "backgroundColor": "#F5F3F0"
    },
    "elements": [
        {
            "type": "text",
            "content": "Test",
            "font": "Comic-Sans",  # Invalid: not in allowed list
            "fontSize": 24,
            "color": "#4A4A4A",
            "position": {"x": 10, "y": 15}
        },
        {
            "type": "text",
            "content": "Test 2",
            "font": "Serif",
            "fontSize": 24,
            "color": "#4A4A4A",
            "position": {"x": 10, "y": 40}
        }
    ]
}

try:
    validate_card_design(invalid_font_name)
    print("✗ Invalid font name PASSED validation (SHOULD HAVE FAILED)\n")
except Exception as e:
    print(f"✓ Invalid font name correctly rejected: {e}\n")

# Test 4: Only 1 text element (should fail, need 2-5)
print("Test 4: Only 1 text element...")
too_few_text = {
    "card": {
        "width": 148,
        "height": 105,
        "backgroundColor": "#F5F3F0"
    },
    "elements": [
        {
            "type": "text",
            "content": "Test",
            "font": "Serif",
            "fontSize": 24,
            "color": "#4A4A4A",
            "position": {"x": 10, "y": 15}
        }
    ]
}

try:
    validate_card_design(too_few_text)
    print("✗ Too few text elements PASSED validation (SHOULD HAVE FAILED)\n")
except Exception as e:
    print(f"✓ Too few text elements correctly rejected: {e}\n")

# Test 5: Invalid color format
print("Test 5: Invalid color format...")
invalid_color = {
    "card": {
        "width": 148,
        "height": 105,
        "backgroundColor": "#F5F3F0"
    },
    "elements": [
        {
            "type": "text",
            "content": "Test",
            "font": "Serif",
            "fontSize": 24,
            "color": "red",  # Invalid: should be hex
            "position": {"x": 10, "y": 15}
        },
        {
            "type": "text",
            "content": "Test 2",
            "font": "Serif",
            "fontSize": 24,
            "color": "#4A4A4A",
            "position": {"x": 10, "y": 40}
        }
    ]
}

try:
    validate_card_design(invalid_color)
    print("✗ Invalid color PASSED validation (SHOULD HAVE FAILED)\n")
except Exception as e:
    print(f"✓ Invalid color correctly rejected: {e}\n")

print("Validation tests complete!")
