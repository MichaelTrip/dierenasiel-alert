from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Optional

from .scraper import ANIMAL_TYPES, scrape_animals
from .store import DEFAULT_STORE, StoreKey, load_seen, save_seen
from .notify import notify_console, notify_desktop, notify_telegram
from .report import generate_pdf_report


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="dierenasiel-alert",
        description="Monitor ikzoekbaas for new available animals at a given shelter",
    )
    
    # Subcommands
    subparsers = p.add_subparsers(dest="command", help="Available commands")
    
    # Monitor command (default behavior)
    monitor_parser = subparsers.add_parser("monitor", help="Monitor for new animals")
    monitor_parser.add_argument(
        "--animal-type",
        default="katten",
        choices=list(ANIMAL_TYPES.keys()),
        help=f"Type of animal to monitor ({', '.join(ANIMAL_TYPES.keys())})",
    )
    monitor_parser.add_argument(
        "--site", 
        default=None, 
        help="Shelter site code (e.g. deKuipershoek). Mutually exclusive with --location"
    )
    monitor_parser.add_argument(
        "--location",
        default=None,
        help="Postal code for location-based search (e.g. 7323PM). Mutually exclusive with --site",
    )
    monitor_parser.add_argument(
        "--distance",
        default=None,
        choices=["10km", "25km", "50km"],
        help="Distance filter for location-based search (only used with --location)",
    )
    monitor_parser.add_argument(
        "--availability",
        default="available",
        choices=["available", "reserved", "unavailable"],
        help="Filter by availability",
    )
    monitor_parser.add_argument(
        "--order",
        default="aflopend",
        choices=["aflopend", "oplopend"],
        help="Sort order: aflopend (descending) or oplopend (ascending)",
    )
    monitor_parser.add_argument(
        "--interval",
        type=int,
        default=0,
        help="Polling interval in seconds (0 = run once and exit)",
    )
    monitor_parser.add_argument(
        "--store",
        type=Path,
        default=DEFAULT_STORE,
        help=f"Path to persistence file (default: {DEFAULT_STORE})",
    )
    monitor_parser.add_argument(
        "--telegram",
        action="store_true",
        help="Enable Telegram notifications",
    )
    monitor_parser.add_argument(
        "--telegram-token",
        help="Telegram bot token (or set TELEGRAM_BOT_TOKEN env var)",
    )
    monitor_parser.add_argument(
        "--telegram-chat-id",
        help="Telegram chat ID (or set TELEGRAM_CHAT_ID env var)",
    )
    
    # List command
    list_parser = subparsers.add_parser("list", help="List currently available animals")
    list_parser.add_argument(
        "--animal-type",
        default="katten",
        choices=list(ANIMAL_TYPES.keys()),
        help=f"Type of animal to list ({', '.join(ANIMAL_TYPES.keys())})",
    )
    list_parser.add_argument(
        "--site", 
        default=None, 
        help="Shelter site code (e.g. deKuipershoek). Mutually exclusive with --location"
    )
    list_parser.add_argument(
        "--location",
        default=None,
        help="Postal code for location-based search (e.g. 7323PM). Mutually exclusive with --site",
    )
    list_parser.add_argument(
        "--distance",
        default=None,
        choices=["10km", "25km", "50km"],
        help="Distance filter for location-based search (only used with --location)",
    )
    list_parser.add_argument(
        "--availability",
        default="available",
        choices=["available", "reserved", "unavailable"],
        help="Filter by availability",
    )
    list_parser.add_argument(
        "--order",
        default="aflopend",
        choices=["aflopend", "oplopend"],
        help="Sort order: aflopend (descending) or oplopend (ascending)",
    )
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate PDF report with animal photos")
    report_parser.add_argument(
        "--animal-type",
        default="katten",
        choices=list(ANIMAL_TYPES.keys()),
        help=f"Type of animal to report ({', '.join(ANIMAL_TYPES.keys())})",
    )
    report_parser.add_argument(
        "--site", 
        default=None, 
        help="Shelter site code (e.g. deKuipershoek). Mutually exclusive with --location"
    )
    report_parser.add_argument(
        "--location",
        default=None,
        help="Postal code for location-based search (e.g. 7323PM). Mutually exclusive with --site",
    )
    report_parser.add_argument(
        "--distance",
        default=None,
        choices=["10km", "25km", "50km"],
        help="Distance filter for location-based search (only used with --location)",
    )
    report_parser.add_argument(
        "--availability",
        default="available",
        choices=["available", "reserved", "unavailable"],
        help="Filter by availability",
    )
    report_parser.add_argument(
        "--order",
        default="aflopend",
        choices=["aflopend", "oplopend"],
        help="Sort order: aflopend (descending) or oplopend (ascending)",
    )
    report_parser.add_argument(
        "--output",
        type=Path,
        default=Path("animals_report.pdf"),
        help="Output PDF file path (default: animals_report.pdf)",
    )
    report_parser.add_argument(
        "--title",
        default=None,
        help="Report title (default: auto-generated based on search parameters)",
    )
    
    args = p.parse_args(argv)
    
    # Default to monitor if no command specified
    if not args.command:
        args.command = "monitor"
        # Set default values for monitor command
        if not hasattr(args, 'animal_type'):
            args.animal_type = "katten"
        if not hasattr(args, 'site'):
            args.site = None
        if not hasattr(args, 'location'):
            args.location = None
        if not hasattr(args, 'distance'):
            args.distance = None
        if not hasattr(args, 'availability'):
            args.availability = "available"
        if not hasattr(args, 'order'):
            args.order = "aflopend"
        if not hasattr(args, 'interval'):
            args.interval = 0
        if not hasattr(args, 'store'):
            args.store = DEFAULT_STORE
        if not hasattr(args, 'telegram'):
            args.telegram = False
        if not hasattr(args, 'telegram_token'):
            args.telegram_token = None
        if not hasattr(args, 'telegram_chat_id'):
            args.telegram_chat_id = None
    
    # Validate mutual exclusivity of site and location
    if hasattr(args, 'site') and hasattr(args, 'location'):
        if args.site and args.location:
            p.error("--site and --location are mutually exclusive. Use one or the other.")
        # Validate distance is only used with location
        if hasattr(args, 'distance') and args.distance and not args.location:
            p.error("--distance can only be used with --location")
    
    return args


def run_once(
    *, 
    animal_type: str,
    site: Optional[str] = None,
    availability: str, 
    order: str, 
    location: Optional[str] = None,
    distance: Optional[str] = None,
    store_path: Path,
    telegram: bool = False, 
    telegram_token: str | None = None, 
    telegram_chat_id: str | None = None
) -> int:
    # Create store key based on search type
    if location:
        key_site = f"location:{location}"
        if distance:
            key_site += f":{distance}"
    else:
        key_site = site or "deKuipershoek"
    
    key = StoreKey(site=key_site, availability=availability, animal_type=animal_type)

    try:
        animals = scrape_animals(
            animal_type=animal_type,
            availability=availability, 
            site=site, 
            order=order,
            location=location,
            distance=distance,
        )
    except Exception as e:
        print(f"Error while fetching/parsing: {e}", file=sys.stderr)
        return 2

    seen_ids = load_seen(store_path, key)
    current_ids = {a.id for a in animals}

    new_ids = current_ids - seen_ids
    new_entries = [a for a in animals if a.id in new_ids]
    new_entries.sort(key=lambda a: a.id)

    if new_entries:
        # Desktop notification first (if available), then console
        notify_desktop(new_entries)
        notify_console(new_entries)
        
        # Telegram notification if enabled
        if telegram:
            token = telegram_token or os.getenv("TELEGRAM_BOT_TOKEN")
            chat_id = telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID")
            if token and chat_id:
                notify_telegram(new_entries, token, chat_id)
            else:
                print("Warning: Telegram notifications enabled but token/chat_id not provided", file=sys.stderr)
    else:
        animal_name = ANIMAL_TYPES.get(animal_type, animal_type)
        print(f"No new {animal_name} found.")

    # Always persist the current state (merge seen + current)
    all_ids = seen_ids | current_ids
    save_seen(store_path, key, all_ids)

    return 0


def list_animals(
    *, 
    animal_type: str, 
    site: Optional[str] = None,
    availability: str, 
    order: str,
    location: Optional[str] = None,
    distance: Optional[str] = None,
) -> int:
    """List all currently available animals."""
    try:
        animals = scrape_animals(
            animal_type=animal_type,
            availability=availability, 
            site=site, 
            order=order,
            location=location,
            distance=distance,
        )
    except Exception as e:
        print(f"Error while fetching/parsing: {e}", file=sys.stderr)
        return 2

    animal_name = ANIMAL_TYPES.get(animal_type, animal_type)
    
    # Build description of search parameters
    if location:
        search_desc = f"location={location}"
        if distance:
            search_desc += f" within {distance}"
    else:
        search_desc = f"site={site or 'deKuipershoek'}"
    
    if not animals:
        print(f"No {animal_name} found with availability={availability} at {search_desc}")
        return 0

    print(f"Found {len(animals)} {animal_name} at {search_desc} with availability={availability}:")
    print()
    for animal in animals:
        print(f"  ID: {animal.id}")
        print(f"  Name: {animal.name}")
        print(f"  URL: {animal.url}")
        if animal.location:
            print(f"  Location: {animal.location}")
        if animal.site:
            print(f"  Site: {animal.site}")
        if animal.availability:
            print(f"  Availability: {animal.availability}")
        if animal.photo_url:
            print(f"  Photo: {animal.photo_url}")
        print()

    return 0


def generate_report(
    *, 
    animal_type: str, 
    site: Optional[str] = None,
    availability: str, 
    order: str,
    location: Optional[str] = None,
    distance: Optional[str] = None,
    output: Path,
    title: Optional[str] = None,
) -> int:
    """Generate a PDF report with animal photos."""
    try:
        animals = scrape_animals(
            animal_type=animal_type,
            availability=availability, 
            site=site, 
            order=order,
            location=location,
            distance=distance,
        )
    except Exception as e:
        print(f"Error while fetching/parsing: {e}", file=sys.stderr)
        return 2

    animal_name = ANIMAL_TYPES.get(animal_type, animal_type)
    
    # Build description of search parameters
    if location:
        search_desc = f"location={location}"
        if distance:
            search_desc += f" within {distance}"
    else:
        search_desc = f"site={site or 'deKuipershoek'}"
    
    if not animals:
        print(f"No {animal_name} found with availability={availability} at {search_desc}")
        return 0

    # Generate title if not provided
    if not title:
        title = f"Dierenasiel Alert - {animal_name.title()}"
        if location:
            title += f" near {location}"
            if distance:
                title += f" within {distance}"
        elif site:
            title += f" at {site}"
    
    print(f"Generating PDF report for {len(animals)} {animal_name}...")
    try:
        generate_pdf_report(animals, output, title=title)
        return 0
    except Exception as e:
        print(f"Error generating PDF report: {e}", file=sys.stderr)
        return 2


def main(argv: list[str] | None = None) -> int:
    ns = parse_args(argv or sys.argv[1:])

    if ns.command == "list":
        return list_animals(
            animal_type=ns.animal_type,
            site=ns.site,
            availability=ns.availability,
            order=ns.order,
            location=ns.location,
            distance=ns.distance,
        )
    
    if ns.command == "report":
        return generate_report(
            animal_type=ns.animal_type,
            site=ns.site,
            availability=ns.availability,
            order=ns.order,
            location=ns.location,
            distance=ns.distance,
            output=ns.output,
            title=ns.title,
        )

    # Monitor command
    if ns.interval <= 0:
        return run_once(
            animal_type=ns.animal_type,
            site=ns.site,
            availability=ns.availability,
            order=ns.order,
            location=ns.location,
            distance=ns.distance,
            store_path=ns.store,
            telegram=ns.telegram,
            telegram_token=ns.telegram_token,
            telegram_chat_id=ns.telegram_chat_id,
        )

    animal_name = ANIMAL_TYPES.get(ns.animal_type, ns.animal_type)
    
    # Build monitoring description
    if ns.location:
        search_desc = f"location={ns.location}"
        if ns.distance:
            search_desc += f" within {ns.distance}"
    else:
        search_desc = f"site={ns.site or 'deKuipershoek'}"
    
    print(
        f"Monitoring {animal_name} at {search_desc}, availability={ns.availability}, order={ns.order} every {ns.interval}s..."
    )
    try:
        while True:
            code = run_once(
                animal_type=ns.animal_type,
                site=ns.site,
                availability=ns.availability,
                order=ns.order,
                location=ns.location,
                distance=ns.distance,
                store_path=ns.store,
                telegram=ns.telegram,
                telegram_token=ns.telegram_token,
                telegram_chat_id=ns.telegram_chat_id,
            )
            # Don't exit on transient errors; keep polling
            time.sleep(max(1, ns.interval))
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
