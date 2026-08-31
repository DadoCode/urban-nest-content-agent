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
        "apartments in London and Manchester, for both leisure travellers "
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
    "cities": ["London", "Manchester"],
    "instagram_handle": "@urbannestestates",
    "hashtags_core": ["#UrbanNestEstates", "#ShortLets", "#LondonApartments", "#ManchesterApartments"],
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
        "id": "mcr-01",
        "name": "Northern Quarter Studio",
        "city": "Manchester",
        "area": "Northern Quarter",
        "bedrooms": 0,
        "sleeps": 2,
        "type": "studio apartment",
        "standout_features": [
            "walking distance to independent cafes and record shops",
            "compact, self-catering kitchen",
            "pet-friendly",
        ],
        "ideal_for": ["solo travellers", "weekend trips", "pet owners"],
    },
    {
        "id": "mcr-02",
        "name": "Deansgate Family Apartment",
        "city": "Manchester",
        "area": "Deansgate",
        "bedrooms": 3,
        "sleeps": 6,
        "type": "apartment",
        "standout_features": [
            "washing machine and full kitchen",
            "2-minute walk to tram stop",
            "close to Manchester Central Library and museums",
        ],
        "ideal_for": ["families", "longer stays", "groups"],
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
CONTENT_TYPES = [
    {
        "key": "property_showcase",
        "label": "Property Showcase",
        "requires_property": True,
        "typical_formats": ["Carousel", "Reel concept"],
    },
    {
        "key": "neighbourhood",
        "label": "Neighbourhood / London / Manchester content",
        "requires_property": False,
        "typical_formats": ["Carousel", "Reel concept", "Story"],
    },
    {
        "key": "travel_tips",
        "label": "Travel tips",
        "requires_property": False,
        "typical_formats": ["Carousel", "Normal post"],
    },
    {
        "key": "shortlet_vs_hotel",
        "label": "Short-let vs hotel content",
        "requires_property": False,
        "typical_formats": ["Carousel", "Reel concept"],
    },
    {
        "key": "corporate_longstay",
        "label": "Corporate / long-stay content",
        "requires_property": False,
        "typical_formats": ["Normal post", "Carousel"],
    },
    {
        "key": "landlord_facing",
        "label": "Property-management / landlord-facing content",
        "requires_property": False,
        "typical_formats": ["Normal post", "Carousel"],
    },
    {
        "key": "reviews",
        "label": "Reviews",
        "requires_property": False,
        "typical_formats": ["Story", "Normal post"],
    },
    {
        "key": "seasonal",
        "label": "Seasonal content",
        "requires_property": False,
        "typical_formats": ["Reel concept", "Carousel", "Story"],
    },
    {
        "key": "offers",
        "label": "Offers",
        "requires_property": False,
        "typical_formats": ["Normal post", "Story"],
    },
    {
        "key": "brand_lifestyle",
        "label": "Brand / lifestyle content",
        "requires_property": False,
        "typical_formats": ["Reel concept", "Normal post"],
    },
]
