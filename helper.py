import datetime
import json

# --- Constants for mapping weekdays ---
WEEKDAY_MAP = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}

# --- Internal Helper for Parsing ---
def _parse_dt_string(dt_str: str) -> datetime.datetime:
    """Internal helper to parse ICS datetime strings into datetime objects."""
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
    """
    Parses an RRULE string into a minimal, raw dictionary.
    """
    rules = {}
    for part in rrule_str.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            rules[k] = v

    days = []
    if "BYDAY" in rules:
        # --- SAFETY FIX IS HERE ---
        # Only include day codes that are in our map, ignoring others like '2SU'
        day_codes = rules["BYDAY"].split(",")
        days = [WEEKDAY_MAP[code] for code in day_codes if code in WEEKDAY_MAP]
    elif start_dt:
        days = [start_dt.weekday()]
    
    until_dt = _parse_dt_string(rules.get("UNTIL", ""))
    until_iso = until_dt.isoformat() if until_dt else None

    return {"days": sorted(days), "until": until_iso}


def parse_ics_to_raw(ics_text: str):
    """
    Parses an ICS file into a clean, JSON-safe list of event dictionaries.
    """
    events = []
    current_event_data = None
    start_dt_for_rrule = None
    in_event_block = False  # <-- MAIN FIX: The new state flag

    for line in ics_text.splitlines():
        line = line.strip()

        if line == "BEGIN:VEVENT":
            in_event_block = True  # <-- Start of an event block
            current_event_data = {}
            start_dt_for_rrule = None
            continue # Move to the next line

        if line == "END:VEVENT":
            in_event_block = False # <-- End of an event block
            if current_event_data:
                events.append(current_event_data)
            current_event_data = None
            continue # Move to the next line

        # --- MAIN FIX: Only process lines if we are inside a VEVENT block ---
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

# --- (The helper functions is_event_on_date and expand_event_occurrences remain the same) ---
def is_event_on_date(event: dict, check_date: datetime.date = None):
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
    start_time = datetime.time.fromisoformat(event["start_time"])
    end_time = datetime.time.fromisoformat(event["end_time"])
    current_date = start_range
    while current_date <= end_range:
        if is_event_on_date(event, current_date):
            start_datetime = datetime.datetime.combine(current_date, start_time)
            end_datetime = datetime.datetime.combine(current_date, end_time)
            yield (start_datetime, end_datetime)
        current_date += datetime.timedelta(days=1)


# --- Example Usage ---
if __name__ == "__main__":
    with open("calendar.ics", "r", encoding="utf-8") as f:
        ics_data = f.read()

    calendar = parse_ics_to_raw(ics_data)

    print("--- Successfully Parsed Data (JSON-Safe) ---")
    first_event = calendar["events"][2]
    print(json.dumps(first_event, indent=2))