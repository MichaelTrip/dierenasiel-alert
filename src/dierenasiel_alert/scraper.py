from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Iterable, List, Optional
from urllib.parse import urlencode, urljoin

from playwright.sync_api import sync_playwright
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


_playwright_instance = None
_playwright_browser = None


def _get_browser():
    global _playwright_instance, _playwright_browser
    if _playwright_browser is None:
        _playwright_instance = sync_playwright().start()
        _playwright_browser = _playwright_instance.chromium.launch(headless=True)
    return _playwright_browser


def fetch_html(url: str, *, timeout: int = 30, retries: int = 3) -> str:
    browser = _get_browser()
    last_error: Exception | None = None

    for attempt in range(retries):
        page = browser.new_page()
        try:
            # DOMContentLoaded is less brittle than networkidle on modern pages.
            page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
            page.wait_for_selector("body", timeout=min(5000, timeout * 1000))
            # Wait until either animal cards are rendered or an explicit no-results
            # message is visible, to avoid parsing too early on JS-heavy pages.
            page.wait_for_function(
                """
                () => {
                    const hasResults = document.querySelector('article a[href*="/asieldier/"]') !== null;
                    const text = (document.body && document.body.innerText ? document.body.innerText : '').toLowerCase();
                    const hasNoResults = /geen\s+.*gevonden|no\s+results|geen\s+resultaten/.test(text);
                    return hasResults || hasNoResults;
                }
                """,
                timeout=min(12000, timeout * 1000),
            )
            return page.content()
        except Exception as e:
            last_error = e
            if attempt == retries - 1:
                raise
            # Back off slightly for transient DNS/network hiccups in containers.
            time.sleep(1.0 * (attempt + 1))
        finally:
            page.close()

    # Defensive fallback; loop should return or raise before this.
    raise RuntimeError(f"Failed to fetch {url}: {last_error}")


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
    
    # Find all article cards that contain an animal detail link
    results: dict[str, AnimalEntry] = {}

    id_re = re.compile(rf"/asieldier/{re.escape(animal_type)}/(\d+)-([a-z0-9\-]+)", re.IGNORECASE)

    for article in soup.find_all('article'):
        # Find the main animal link
        a = article.find('a', href=lambda h: h and f'/asieldier/{animal_type}/' in h)
        if not a:
            continue

        href = a.get("href")
        href_abs = urljoin(base, href)

        m = id_re.search(href_abs)
        if not m:
            continue
        animal_id, slug = m.group(1), m.group(2)

        # Name from the h3 heading inside the card
        h3 = article.find('h3')
        display_name = h3.get_text(strip=True) if h3 else slug.replace("-", " ").title()

        # Location: the div with the map-pin SVG (flex + items-center + text-sm + text-black,
        # but NOT font-bold which identifies the gender/date row)
        location = None
        for div in article.find_all('div'):
            classes = ' '.join(div.get('class', []))
            if ('flex' in classes and 'items-center' in classes
                    and 'text-sm' in classes and 'text-black' in classes
                    and 'font-bold' not in classes):
                loc_text = div.get_text(strip=True)
                if loc_text:
                    location = loc_text
                    break

        # Extract photo URL from the first picture tag
        photo_url = None
        picture = article.find('picture')
        if picture:
            img = picture.find('img')
            if img and img.get('src'):
                photo_url = img.get('src')

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

        # On some runs the JS results grid renders late; retry first page once
        # before deciding that there are no results.
        if page == 1 and not animals:
            try:
                html = fetch_html(url, timeout=timeout, retries=2)
                animals = parse_animals(
                    html,
                    animal_type=animal_type,
                    base=get_base_url(animal_type),
                    site=site,
                    availability=availability,
                )
            except Exception:
                pass
        
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
