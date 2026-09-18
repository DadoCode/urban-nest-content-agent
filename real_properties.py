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
    {
        "id": "shaldon-mansions",
        "name": "Shaldon Mansions",
        "city": "London",
        "area": "West End",
        "bedrooms": 3,
        "sleeps": 6,
        "type": "design-led apartment",
        "standout_features": [
            "king-size bed dressed in 400-thread-count linen in the principal suite",
            "marble bathrooms with brushed gold fittings",
            "1-minute walk to Tottenham Court Road, 3 minutes to Oxford Circus",
        ],
        "ideal_for": ["families", "business travellers", "theatre trips", "extended stays"],
        "source_url": "https://urbannestestates.co.uk/home-shaldon-mansions",
    },
    {
        "id": "forest-gate",
        "name": "Forest Gate",
        "city": "London",
        "area": "Forest Gate",
        "bedrooms": 5,
        "sleeps": 8,
        "type": "full house",
        "standout_features": [
            "private garden with glass doors from the living room",
            "sage green feature wall in the living area",
            "short walk to the Elizabeth line, with direct trains to Liverpool Street and Heathrow",
        ],
        "ideal_for": ["larger families", "groups up to 8", "project and contractor teams", "longer stays"],
        "source_url": "https://urbannestestates.co.uk/home-forest-gate",
    },
    {
        "id": "miles-edgware",
        "name": "Miles Edgware",
        "city": "London",
        "area": "Marylebone",
        "bedrooms": 2,
        "sleeps": 4,
        "type": "period mansion block apartment",
        "standout_features": [
            "two minutes to four tube lines (Central, Circle, District, Hammersmith & City)",
            "open-plan living and kitchen with period features",
            "steps from the Edgware Road restaurant strip",
        ],
        "ideal_for": ["families", "business travellers", "extended stays"],
        "source_url": "https://urbannestestates.co.uk/home-miles-edgware-1",
    },
    {
        "id": "crested-court",
        "name": "Crested Court",
        "city": "London",
        "area": "Hendon Waterside",
        "bedrooms": 1,
        "sleeps": 4,
        "type": "modern apartment",
        "standout_features": [
            "private balcony, shared courtyard garden, and a roof terrace",
            "complimentary gym access",
            "5-minute walk to Hendon Thameslink, 18 minutes direct to King's Cross",
        ],
        "ideal_for": ["couples", "solo travellers", "guests wanting gym access"],
        "source_url": "https://urbannestestates.co.uk/home-crested-court",
    },
]
