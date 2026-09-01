"""
Real Urban Nest Estates properties.

Facts are sourced from the property's own page on urbannestestates.co.uk —
never invented. Each property's "id" matches its folder under
assets/private/<id>/, which holds real (gitignored, never committed) photos
and a metadata.json describing them. This is the list the weekly content
plan actually uses.
"""

PROPERTIES = [
    {
        "id": "draycott",
        "name": "Draycott Avenue",
        "city": "London",
        "area": "Chelsea",
        "bedrooms": 1,
        "sleeps": 4,
        "type": "split-level maisonette",
        "standout_features": [
            "bright living area with a carved mantelpiece",
            "quiet double bedroom with an upholstered headboard",
            "5-minute walk to Sloane Square station",
        ],
        "ideal_for": ["couples", "families", "professionals", "guests travelling with pets"],
        "source_url": "https://urbannestestates.co.uk/home-draycott-avenue",
    },
    {
        "id": "pw",
        "name": "Eider Apartments",
        "city": "London",
        "area": "Hendon Waterside",
        "bedrooms": 1,
        "sleeps": 5,
        "type": "modern apartment",
        "standout_features": [
            "private balcony overlooking the waterside development",
            "shared terrace garden with views over Welsh Harp Reservoir",
            "complimentary gym access",
        ],
        "ideal_for": ["couples", "solo travellers", "guests wanting a peaceful lakeside stay"],
        "source_url": "https://urbannestestates.co.uk/home-eider-apartments",
    },
    {
        "id": "lascar-wharf",
        "name": "Lascar Wharf",
        "city": "London",
        "area": "Limehouse",
        "bedrooms": 2,
        "sleeps": 6,
        "type": "apartment",
        "standout_features": [
            "private wraparound balcony with views toward Canary Wharf and the docklands",
            "approximately 100 square metres with an open-plan living and dining area",
            "5-minute walk to Limehouse DLR",
        ],
        "ideal_for": ["families", "business travellers near Canary Wharf", "guests relocating to the area"],
        "source_url": "https://urbannestestates.co.uk/home-lascar-wharf",
    },
]
