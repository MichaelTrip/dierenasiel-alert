from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup


# Animal type mappings
ANIMAL_TYPES = {
    "katten": "cats",
    "honden": "dogs",
    "vogels": "birds",
    "konijnen-en-knagers": "rabbits-and-rodents",
}

# Valid distance options for location-based search
VALID_DISTANCES = ["10km", "25km", "50km", None]

# Default to cats for backwards compatibility
BASE_URL = "https://ikzoekbaas.dierenbescherming.nl/zoek-asieldieren/katten"


def get_base_url(animal_type: str = "katten") -> str:
    """Get base URL for a specific animal type."""
    if animal_type not in ANIMAL_TYPES:
        raise ValueError(f"Invalid animal type '{animal_type}'. Must be one of: {', '.join(ANIMAL_TYPES.keys())}")
    return f"https://ikzoekbaas.dierenbescherming.nl/zoek-asieldieren/{animal_type}"


def get_animal_path_fragment(animal_type: str = "katten") -> str:
    """Get URL path fragment for a specific animal type."""
    if animal_type not in ANIMAL_TYPES:
        raise ValueError(f"Invalid animal type '{animal_type}'. Must be one of: {', '.join(ANIMAL_TYPES.keys())}")
    return f"/asieldier/{animal_type}/"


@dataclass(frozen=True)
class AnimalEntry:
    id: str
    name: str
    url: str
    animal_type: str = "katten"
    site: Optional[str] = None
    availability: Optional[str] = None
    location: Optional[str] = None
    photo_url: Optional[str] = None


# Alias for backwards compatibility
CatEntry = AnimalEntry


def build_search_url(
    animal_type: str = "katten",
    *,
    availability: str = "available",
    site: Optional[str] = None,
    order: str = "aflopend",
    location: Optional[str] = None,
    distance: Optional[str] = None,
    page: Optional[int] = None,
    extra_params: Optional[dict] = None,
) -> str:
    """Build search URL for given animal type and filters.
    
    Args:
        animal_type: Type of animal to search for
        availability: Availability filter (available, reserved, unavailable)
        site: Shelter site code (mutually exclusive with location)
        order: Sort order (aflopend or oplopend)
        location: Postal code for location-based search
        distance: Distance filter (10km, 25km, 50km, or None for all)
        page: Page number for pagination
        extra_params: Additional URL parameters
    
    Returns:
        Complete search URL with query parameters
    """
    base_url = get_base_url(animal_type)
    params = {
        "animalAvailability": availability,
        "volgorde": order,
    }
    
    # Location-based search OR site-based search (mutually exclusive)
    if location:
        params["location"] = location
        if distance:
            if distance not in ["10km", "25km", "50km"]:
                raise ValueError(f"Invalid distance '{distance}'. Must be one of: 10km, 25km, 50km")
            params["distance"] = distance
        # Don't include site when searching by location
    elif site:
        params["site"] = site
    
    # Add pagination
    if page and page > 1:
        params["page"] = str(page)
    
    if extra_params:
        params.update(extra_params)
    
    return f"{base_url}?{urlencode(params)}"


def fetch_html(url: str, *, timeout: int = 20) -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        )
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def parse_animals(
    html: str, 
    *, 
    animal_type: str = "katten",
    base: Optional[str] = None, 
    site: Optional[str] = None, 
    availability: Optional[str] = None
) -> List[AnimalEntry]:
    """Parse animal entries from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    
    if base is None:
        base = get_base_url(animal_type)
    
    # Find article cards with data-v-2f76df55 attribute (more reliable)
    articles = soup.find_all('article', attrs={"data-v-2f76df55": True})
    results: dict[str, AnimalEntry] = {}

    id_re = re.compile(rf"/asieldier/{re.escape(animal_type)}/(\d+)-([a-z0-9\-]+)", re.IGNORECASE)

    for article in articles:
        # Find the main link
        a = article.find('a', href=True)
        if not a:
            continue
        
        href = a.get("href")
        if not href:
            continue
        href_abs = urljoin(base, href)

        m = id_re.search(href_abs)
        if not m:
            continue
        animal_id, slug = m.group(1), m.group(2)

        # Extract location from the article
        location = None
        location_divs = article.find_all('div', class_=['flex', 'items-center'])
        for div in location_divs:
            text = div.get_text(strip=True)
            # Location is typically a city name without dates or bullets
            if text and '•' not in text and not any(char.isdigit() for char in text):
                location = text
                break
        
        # Extract photo URL
        photo_url = None
        picture = article.find('picture', attrs={"data-v-2f76df55": True})
        if picture:
            img = picture.find('img')
            if img and img.get('src'):
                photo_url = img.get('src')
        
        # Derive name from slug
        slug_name = slug.replace("-", " ").title()
        
        # Try to get better name from article text
        text_divs = article.find_all('div', class_='flex')
        display_name = slug_name
        for div in text_divs:
            text = div.get_text(strip=True)
            # Look for text that looks like a name (short, has letters, no dates)
            if text and len(text) < 50 and any(c.isalpha() for c in text) and '•' not in text:
                # Skip if it contains common non-name words
                if not any(word in text.lower() for word in ['koppel', 'mannelijk', 'vrouwelijk']):
                    continue
                # Extract name part (usually before bullet or date)
                parts = text.split('•')[0].split('Mannelijk')[0].split('Vrouwelijk')[0]
                if parts and len(parts.strip()) > 2:
                    display_name = parts.strip()
                    break

        if animal_id not in results:
            results[animal_id] = AnimalEntry(
                id=animal_id,
                name=display_name,
                url=href_abs,
                animal_type=animal_type,
                site=site,
                availability=availability,
                location=location,
                photo_url=photo_url,
            )

    return list(results.values())


def has_next_page(html: str) -> bool:
    """Check if there's a next page in pagination."""
    soup = BeautifulSoup(html, "html.parser")
    # Look for pagination "next" button or link
    # Common patterns: <a class="next">, <a>Volgende</a>, etc.
    next_links = soup.find_all("a", string=re.compile(r"volgende|next|›|»", re.IGNORECASE))
    if next_links:
        return True
    
    # Also check for numbered pagination links
    pagination = soup.find_all("a", href=re.compile(r"[?&]page=\d+"))
    if pagination:
        # If there are page links, check if any have a higher page number
        return True
    
    return False


# Alias for backwards compatibility
parse_cats = parse_animals


def scrape_animals(
    *,
    animal_type: str = "katten",
    availability: str = "available",
    site: Optional[str] = None,
    order: str = "aflopend",
    location: Optional[str] = None,
    distance: Optional[str] = None,
    max_pages: int = 10,
    extra_params: Optional[dict] = None,
    timeout: int = 20,
) -> List[AnimalEntry]:
    """Fetch and parse the list of animals per the given filters.
    
    Automatically handles pagination to scrape all available pages.

    Args:
        animal_type: Type of animal (katten, honden, vogels, konijnen-en-knagers)
        availability: Filter by availability status
        site: Shelter site code (mutually exclusive with location)
        order: Sort order (aflopend or oplopend)
        location: Postal code for location-based search
        distance: Distance filter (10km, 25km, 50km, or None)
        max_pages: Maximum number of pages to scrape (safety limit)
        extra_params: Additional URL parameters
        timeout: Request timeout in seconds

    Returns:
        List of AnimalEntry with unique IDs from all pages.
    """
    all_animals: dict[str, AnimalEntry] = {}
    page = 1
    
    # Default to site if neither site nor location is provided
    if not site and not location:
        site = "deKuipershoek"
    
    while page <= max_pages:
        url = build_search_url(
            animal_type=animal_type,
            availability=availability, 
            site=site, 
            order=order,
            location=location,
            distance=distance,
            page=page if page > 1 else None,
            extra_params=extra_params
        )
        
        try:
            html = fetch_html(url, timeout=timeout)
        except Exception as e:
            if page == 1:
                # If first page fails, re-raise
                raise
            # If subsequent page fails, just stop pagination
            break
        
        animals = parse_animals(
            html, 
            animal_type=animal_type,
            base=get_base_url(animal_type), 
            site=site, 
            availability=availability
        )
        
        # If no animals found on this page, we've reached the end
        if not animals:
            break
        
        # Add to results (using dict to deduplicate by ID)
        for animal in animals:
            all_animals[animal.id] = animal
        
        # Check if there's a next page
        if not has_next_page(html):
            break
        
        page += 1
        
        # Add a polite delay between page requests (skip on first iteration)
        if page > 1:
            time.sleep(1.0)
    
    return list(all_animals.values())


# Alias for backwards compatibility
def scrape_cats(**kwargs) -> List[AnimalEntry]:
    """Legacy function - use scrape_animals instead."""
    kwargs.setdefault('animal_type', 'katten')
    return scrape_animals(**kwargs)
