from api.server import _normalize_region, _region_coords

# Test cases
test_cases = [
    ("null", "", "Should return Unknown"),
    ("", "KEEA", "Should return KEEA"),
    ("", "Ankaful", "Should return KEEA"),
    ("KEEA", "", "Should return KEEA"),
    ("", "null", "Should return Unknown"),
]

print("=== NORMALIZE REGION TESTS ===")
for region, city, expected in test_cases:
    result = _normalize_region(region, city)
    print(f"{region!r}, {city!r} -> {result!r} ({expected})")

print("\n=== COORDINATES TESTS ===")
test_regions = ["KEEA", "Unknown", "null", "Greater Accra"]
for region in test_regions:
    coords = _region_coords(region)
    print(f"{region}: {coords}")
