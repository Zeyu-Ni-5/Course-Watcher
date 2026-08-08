import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


# Store the watch list beside this script.
WATCHES_FILE = Path(__file__).with_name("watches.json")

# Base URL for the Waterloo Open Data API.
API_BASE_URL = "https://openapi.data.uwaterloo.ca"

# Stop waiting if the server does not respond within ten seconds.
REQUEST_TIMEOUT = 10


class WatchError(Exception):
    """Represent an expected error that can be shown to the user."""


def load_watches():
    """Load and validate the watch list from watches.json."""
    if not WATCHES_FILE.exists():
        return []

    try:
        with WATCHES_FILE.open("r", encoding="utf-8") as file:
            watches = json.load(file)

    except json.JSONDecodeError as error:
        raise WatchError("watches.json is not valid JSON.") from error

    except OSError as error:
        raise WatchError(f"Could not read watches.json: {error}") from error

    if not isinstance(watches, list):
        raise WatchError("watches.json must contain a JSON list.")

    return watches


def save_watches(watches):
    """Save the watch list in a readable JSON format."""
    try:
        with WATCHES_FILE.open("w", encoding="utf-8") as file:
            json.dump(watches, file, indent=2, ensure_ascii=False)
            file.write("\n")

    except OSError as error:
        raise WatchError(f"Could not write watches.json: {error}") from error


def get_api_key():
    """Read the API key from the environment."""
    api_key = os.getenv("UW_API_KEY")

    if not api_key:
        raise WatchError(
            "UW_API_KEY is not set. Set it before running the check command."
        )

    return api_key


def api_get(path, api_key):
    """Send an authenticated GET request and return decoded JSON."""
    request = Request(
        f"{API_BASE_URL}{path}",
        headers={
            "x-api-key": api_key,
            "Accept": "application/json",
            "User-Agent": "uw-course-watcher-v0",
        },
    )

    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            return json.load(response)

    except HTTPError as error:
        if error.code in (401, 403):
            raise WatchError("The UW API key was rejected.") from error
        if error.code == 404:
            raise WatchError("The requested UW API resource was not found.") from error
        raise WatchError(f"UW API returned HTTP {error.code}.") from error
    
    except TimeoutError as error:
        raise WatchError(
                f"UW API did not respond within {REQUEST_TIMEOUT} seconds. "
                "Please try again later."
        ) from error
    
    except URLError as error:
        raise WatchError(f"Could not connect to the UW API: {error.reason}") from error
    
    except json.JSONDecodeError as error:
        raise WatchError("UW API returned invalid JSON.") from error


def get_current_term(api_key):
    """Get the current Waterloo term code."""
    term = api_get("/v3/Terms/current", api_key)

    if not isinstance(term, dict) or not term.get("termCode"):
        raise WatchError("UW API did not return a valid current term.")

    return term["termCode"]


def get_course_sections(api_key, term_code, subject, catalog_number):
    """Get all scheduled sections for one course."""
    encoded_subject = quote(subject, safe="")
    encoded_catalog = quote(catalog_number, safe="")

    path = (
        f"/v3/ClassSchedules/{term_code}/"
        f"{encoded_subject}/{encoded_catalog}"
    )

    sections = api_get(path, api_key)

    if not isinstance(sections, list):
        raise WatchError(f"Unexpected API response for {subject} {catalog_number}.")

    if not sections:
        raise WatchError(
            f"No scheduled course found for {subject} {catalog_number} "
            f"in term {term_code}."
        )

    return sections


def add_watch(args):
    """Add one course to watches.json."""
    subject = args.subject.strip().upper()
    catalog_number = args.catalog_number.strip().upper()
    component = args.component.strip().upper() if args.component else None

    if not subject.isalpha():
        raise WatchError("Subject must contain letters only.")

    if not catalog_number or any(character.isspace() for character in catalog_number):
        raise WatchError("Catalog number must not be empty or contain spaces.")

    if component is not None and not component.isalpha():
        raise WatchError("Component must contain letters only.")

    new_watch = {
        "subject": subject,
        "catalog_number": catalog_number,
        "component": component,
    }

    watches = load_watches()

    if new_watch in watches:
        print("This watch already exists.")
        return False

    watches.append(new_watch)
    save_watches(watches)

    component_text = component or "ALL"
    print(f"Added {subject} {catalog_number} ({component_text}).")
    return False


def list_watches(args):
    """Print every course in the watch list."""
    watches = load_watches()

    if not watches:
        print("The watch list is empty.")
        return False

    for number, watch in enumerate(watches, start=1):
        component = watch.get("component") or "ALL"
        print(
            f"{number}. {watch['subject']} "
            f"{watch['catalog_number']} ({component})"
        )

    return False


def check_watches(args):
    """Query the UW API and print enrollment information."""
    watches = load_watches()

    if not watches:
        print("The watch list is empty. Add a course first.")
        return False

    api_key = get_api_key()
    term_code = get_current_term(api_key)

    # Group watches so each course causes only one API request.
    grouped_watches = {}

    for watch in watches:
        course = (watch["subject"], watch["catalog_number"])
        grouped_watches.setdefault(course, set()).add(watch.get("component"))

    had_error = False

    for (subject, catalog_number), wanted_components in grouped_watches.items():
        try:
            sections = get_course_sections(
                api_key,
                term_code,
                subject,
                catalog_number,
            )

        except WatchError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            had_error = True
            continue

        matched_section = False

        for section in sections:
            component = str(section.get("courseComponent", "")).upper()

            if None not in wanted_components and component not in wanted_components:
                continue

            try:
                section_number = int(section["classSection"])
                enrolled = int(section["enrolledStudents"])
                capacity = int(section["maxEnrollmentCapacity"])

            except (KeyError, TypeError, ValueError) as error:
                raise WatchError(
                    f"UW API returned incomplete data for "
                    f"{subject} {catalog_number}."
                ) from error

            status = "OPEN" if enrolled < capacity else "FULL"

            print(
                f"{subject} {catalog_number}  "
                f"{component} {section_number:03d}  "
                f"{enrolled}/{capacity}  {status}"
            )

            matched_section = True

        if not matched_section:
            requested = ", ".join(
                sorted(component for component in wanted_components if component)
            )
            print(
                f"ERROR: No matching {requested} sections found for "
                f"{subject} {catalog_number}.",
                file=sys.stderr,
            )
            had_error = True

    return had_error


def build_parser():
    """Create the command-line parser."""
    parser = argparse.ArgumentParser(
        description="Monitor Waterloo course enrollment."
    )

    commands = parser.add_subparsers(dest="command", required=True)

    add_parser = commands.add_parser(
        "add",
        help="Add a course to the watch list.",
    )
    add_parser.add_argument("subject", help="Course subject, such as CS.")
    add_parser.add_argument(
        "catalog_number",
        help="Catalog number, such as 136.",
    )
    add_parser.add_argument(
        "--component",
        help="Optional component filter, such as LEC.",
    )
    add_parser.set_defaults(handler=add_watch)

    list_parser = commands.add_parser(
        "list",
        help="Show the watch list.",
    )
    list_parser.set_defaults(handler=list_watches)

    check_parser = commands.add_parser(
        "check",
        help="Check enrollment using the UW API.",
    )
    check_parser.set_defaults(handler=check_watches)

    return parser


def main():
    """Run the selected command and return an exit code."""
    parser = build_parser()
    args = parser.parse_args()

    try:
        failed = args.handler(args)
        return 1 if failed else 0
    
    except WatchError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())