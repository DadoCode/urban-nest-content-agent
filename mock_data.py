"""
Local mock data for the Urban Nest Estates content agent (V1 prototype).

This is FAKE data for testing only. No real property or guest information
is stored here. When the agent generates content about a specific property,
it must only use the facts present in that property's record below.
"""

BRAND = {
    "name": "Urban Nest Estates",
    "what_we_do": (
        "Urban Nest Estates manages professionally furnished short-let "
        "apartments in London, for both leisure travellers "
        "and corporate/relocation guests."
    ),
    "tone_of_voice": (
        "Warm, professional, and confident — like a knowledgeable local "
        "friend, not a corporate hotel chain. Avoid hype and excessive "
        "exclamation marks."
    ),
    "target_audiences": [
        "Leisure travellers wanting a 'home away from home'",
        "Corporate travellers and relocating professionals needing 1-6 month stays",
        "Landlords considering short-let management",
    ],
    "cities": ["London"],
    "instagram_handle": "@urbannestestates",
    "hashtags_core": ["#UrbanNestEstates", "#ShortLets", "#LondonApartments"],
    "website": "urbannestestates.co.uk",
}

# Fictional mock properties — placeholder data for prototype testing only.
PROPERTIES = [
    {
        "id": "ldn-01",
        "name": "Riverside Loft",
        "city": "London",
        "area": "Shoreditch",
        "bedrooms": 1,
        "sleeps": 2,
        "type": "loft apartment",
        "standout_features": [
            "exposed brick walls",
            "floor-to-ceiling windows",
            "5-minute walk to Shoreditch High Street station",
        ],
        "ideal_for": ["couples", "short leisure breaks", "creative professionals"],
    },
    {
        "id": "ldn-02",
        "name": "Canary Wharf Executive Suite",
        "city": "London",
        "area": "Canary Wharf",
        "bedrooms": 2,
        "sleeps": 4,
        "type": "high-rise apartment",
        "standout_features": [
            "dedicated work desk in each bedroom",
            "on-site gym access",
            "10-minute walk to Canary Wharf financial district",
        ],
        "ideal_for": ["corporate stays", "relocation", "business travellers"],
    },
    {
        "id": "ldn-03",
        "name": "Kensington Garden Flat",
        "city": "London",
        "area": "Kensington",
        "bedrooms": 2,
        "sleeps": 4,
        "type": "garden-level flat",
        "standout_features": [
            "private courtyard garden",
            "quiet residential street",
            "15-minute walk to Hyde Park",
        ],
        "ideal_for": ["families", "longer leisure stays", "quiet getaways"],
    },
]

# Content type catalogue for the weekly planner.
# "requires_property" flags whether this type should be paired with one
# property record from PROPERTIES.
# "bucket" is soft content-mix guidance (see CONTENT_MIX_GUIDANCE below) —
# it is NOT a hard rule the planner must satisfy every week.
CONTENT_TYPES = [
    {
        "key": "property_showcase",
        "label": "Property Showcase",
        "requires_property": True,
        "typical_formats": ["Carousel", "Reel concept"],
        "bucket": "property",
    },
    {
        "key": "neighbourhood",
        "label": "Neighbourhood / London content",
        "requires_property": False,
        "typical_formats": ["Carousel", "Reel concept", "Story"],
        "bucket": "place_lifestyle",
    },
    {
        "key": "travel_tips",
        "label": "Travel tips",
        "requires_property": False,
        "typical_formats": ["Carousel", "Normal post"],
        "bucket": "place_lifestyle",
    },
    {
        "key": "shortlet_vs_hotel",
        "label": "Short-let vs hotel content",
        "requires_property": False,
        "typical_formats": ["Carousel", "Reel concept"],
        "bucket": "educational_brand",
    },
    {
        "key": "corporate_longstay",
        "label": "Corporate / long-stay content",
        "requires_property": False,
        "typical_formats": ["Normal post", "Carousel"],
        "bucket": "educational_brand",
    },
    {
        "key": "landlord_facing",
        "label": "Property-management / landlord-facing content",
        "requires_property": False,
        "typical_formats": ["Normal post", "Carousel"],
        "bucket": "educational_brand",
    },
    {
        "key": "reviews",
        "label": "Reviews",
        "requires_property": False,
        "typical_formats": ["Story", "Normal post"],
        "bucket": "educational_brand",
    },
    {
        "key": "seasonal",
        "label": "Seasonal content",
        "requires_property": False,
        "typical_formats": ["Reel concept", "Carousel", "Story"],
        "bucket": "place_lifestyle",
    },
    {
        "key": "offers",
        "label": "Offers",
        "requires_property": False,
        "typical_formats": ["Normal post", "Story"],
        "bucket": "educational_brand",
    },
    {
        "key": "brand_lifestyle",
        "label": "Brand / lifestyle content",
        "requires_property": False,
        "typical_formats": ["Reel concept", "Normal post"],
        "bucket": "place_lifestyle",
    },
]

# Soft guidance for the planner (and for Claude, when it makes the call) about
# what a healthy week's content mix can look like. This is guidance, not a
# formula the planner is required to satisfy every single week.
CONTENT_MIX_GUIDANCE = (
    "A healthy week often combines content from more than one bucket: "
    "'property' (property showcases), 'place_lifestyle' (neighbourhood, travel tips, "
    "seasonal, brand/lifestyle), and 'educational_brand' (short-let vs hotel, "
    "corporate/long-stay, landlord-facing, reviews, offers). This is a guideline, "
    "not a fixed formula — it's fine to deviate from it when there's a good reason."
)
