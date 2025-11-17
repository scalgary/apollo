import csv
import os

# Permet override pour les tests
WHITELIST_PATH = os.getenv("WHITELIST_PATH", "/app/data/whitelist.csv")
EVENTS_PATH = os.getenv("EVENTS_PATH", "/app/data/events.csv")

def load_whitelist():
    """Charger la liste des emails autorisés"""
    whitelist = set()
    try:
        with open(WHITELIST_PATH, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                whitelist.add(row['email'].strip().lower())
    except FileNotFoundError:
        print(f"Warning: Whitelist file not found at {WHITELIST_PATH}")
    return whitelist

def load_events():
    """Charger les événements depuis CSV"""
    events = []
    try:
        with open(EVENTS_PATH, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                events.append({
                    'date': row['date'],
                    'max_spots': int(row['max_spots'])
                })
    except FileNotFoundError:
        print(f"Warning: Events file not found at {EVENTS_PATH}")
    return events