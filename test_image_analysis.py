#!/usr/bin/env python3
"""Quick test script to debug image analysis"""

import sys
sys.path.insert(0, '.')

from ai_card_generator import analyze_single_image

# Test with one of the failing Pinterest images
test_url = "https://i.pinimg.com/originals/8f/5e/5a/8f5e5a7a6f607dfd2ad9f374d4485916.jpg"

print(f"Testing image analysis with: {test_url}")
print("-" * 60)

try:
    result = analyze_single_image(test_url)
    print("SUCCESS!")
    print(f"Result: {result[:200]}...")
except Exception as e:
    print(f"FAILED with error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
