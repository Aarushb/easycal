import datetime
import json
import sys # It's good practice to have imports at the top

# --- (All the other functions from your file remain exactly the same) ---
# --- Constants for mapping weekdays ---
WEEKDAY_MAP = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}

# --- Internal Helper for Parsing ---
def _parse_dt_string(dt_str: str) -> datetime.datetime:
    # ... (code is unchanged)
    if dt_str.endswith('Z'):
        dt_str = dt_str[:-1]
    for fmt in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M"):
        try:
            return datetime.datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    return None

# --- Core Parsing Logic ---
def parse_rrule_to_raw(rrule_str, start_dt):
    # ... (code is unchanged)
    rules = {}
    for part in rrule_str.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            rules[k] = v
    days = []
    if "BYDAY" in rules:
        day_codes = rules["BYDAY"].split(",")
        days = [WEEKDAY_MAP[code] for code in day_codes if code in WEEKDAY_MAP]
    elif start_dt:
        days = [start_dt.weekday()]
    until_dt = _parse_dt_string(rules.get("UNTIL", ""))
    until_iso = until_dt.isoformat() if until_dt else None
    return {"days": sorted(days), "until": until_iso}

def parse_ics_to_raw(ics_text: str):
    # ... (code is unchanged)
    events = []
    current_event_data = None
    start_dt_for_rrule = None
    in_event_block = False
    for line in ics_text.splitlines():
        line = line.strip()
        if line == "BEGIN:VEVENT":
            in_event_block = True
            current_event_data = {}
            start_dt_for_rrule = None
            continue
        if line == "END:VEVENT":
            in_event_block = False
            if current_event_data:
                events.append(current_event_data)
            current_event_data = None
            continue
        if in_event_block and current_event_data is not None and ":" in line:
            key, value = line.split(":", 1)
            key = key.split(";")[0]
            if key == "DTSTART":
                dt = _parse_dt_string(value)
                if dt:
                    current_event_data["start_time"] = dt.time().isoformat()
                    start_dt_for_rrule = dt 
            elif key == "DTEND":
                dt = _parse_dt_string(value)
                if dt:
                    current_event_data["end_time"] = dt.time().isoformat()
            elif key == "SUMMARY":
                current_event_data["summary"] = value
            elif key == "LOCATION":
                current_event_data["location"] = value.strip()
            elif key == "RRULE":
                rrule_data = parse_rrule_to_raw(value, start_dt_for_rrule)
                current_event_data.update(rrule_data)
    return {"events": events}

def is_event_on_date(event: dict, check_date: datetime.date = None):
    # ... (code is unchanged)
    if check_date is None:
        check_date = datetime.date.today()
    if event.get("until"):
        until_dt = datetime.datetime.fromisoformat(event["until"])
        if check_date > until_dt.date():
            return False
    if check_date.weekday() not in event.get("days", []):
        return False
    return True

def expand_event_occurrences(event: dict, start_range: datetime.date, end_range: datetime.date):
    # ... (code is unchanged)
    start_time = datetime.time.fromisoformat(event["start_time"])
    end_time = datetime.time.fromisoformat(event["end_time"])
    current_date = start_range
    while current_date <= end_range:
        if is_event_on_date(event, current_date):
            start_datetime = datetime.datetime.combine(current_date, start_time)
            end_datetime = datetime.datetime.combine(current_date, end_time)
            yield (start_datetime, end_datetime)
        current_date += datetime.timedelta(days=1)


def load_and_parse_calendar(file_path: str) -> dict | None:
    """
    Loads an .ics file from the given path and parses it.

    Args:
        file_path: The path to the .ics calendar file.

    Returns:
        A dictionary with the parsed calendar data on success,
        or None if an error occurred.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            ics_data = f.read()
        
        # Also include the parsing step inside the try block
        calendar = parse_ics_to_raw(ics_data)
        return calendar

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
        return None
    except IOError as e:
        # Catches other I/O errors, like permission denied
        print(f"Error: Could not read the file '{file_path}'. Reason: {e}")
        return None
    except Exception as e:
        # A catch-all for any other unexpected errors during parsing
        print(f"An unexpected error occurred while parsing '{file_path}': {e}")
        return None


# --- Example Usage (Updated to use the new function) ---
if __name__ == "__main__":
    
    # This is now the proper way to use your module
    calendar_data = load_and_parse_calendar("calendar.ics")

    # ALWAYS check if the function succeeded before using its output
    if calendar_data:
        print("--- Successfully Loaded and Parsed Calendar ---")
        
        # Check if there are any events before trying to access them
        if calendar_data["events"]:
            first_event = calendar_data["events"][0]
            print("Data for the first event:")
            print(json.dumps(first_event, indent=2))
        else:
            print("The calendar file was parsed, but it contains no events.")
    
    else:
        print("\nCould not process the calendar file. Program will exit.")
        sys.exit(1) # Exit with a non-zero code to indicate an error