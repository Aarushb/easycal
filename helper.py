import datetime
import json
import sys

# --- Custom Exceptions for Clear Error Handling ---
class CalendarError(Exception):
    """Base exception for all calendar-related errors in this module."""
    pass

class CalendarNotFoundError(CalendarError):
    """Raised when the calendar file cannot be found at the given path."""
    pass

class CalendarParseError(CalendarError):
    """Raised when the file is found but cannot be read or parsed due to format errors."""
    pass

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


# In ics_parser.py

# ... (the custom exceptions from Step 1 are above this) ...
# ... (all the other parsing functions like _parse_dt_string are here) ...

def load_and_parse_calendar(file_path: str) -> dict:
    """
    Loads and parses an .ics file, raising specific exceptions on failure.

    Args:
        file_path: The path to the .ics calendar file.

    Returns:
        A dictionary with the parsed calendar data on successful completion.

    Raises:
        CalendarNotFoundError: If the file does not exist at the path.
        CalendarParseError: If the file cannot be read or has an invalid format.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            ics_data = f.read()
        
        # We also try to parse inside this block
        calendar = parse_ics_to_raw(ics_data)
        return calendar

    # --- This is the "translation" part ---
    # Catch a generic Python error...
    except FileNotFoundError:
        # ...and RAISE our specific, meaningful alarm.
        raise CalendarNotFoundError(f"The calendar file was not found at: {file_path}")
    
    # Catch other potential low-level errors during reading or parsing...
    except (IOError, ValueError, KeyError, IndexError) as e:
        # ...and RAISE our other specific alarm.
        raise CalendarParseError(f"Failed to read or parse '{file_path}'. The file may be corrupt or in an unexpected format. Details: {e}")

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