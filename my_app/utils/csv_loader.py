import csv
import os

# Permet override pour les tests
WHITELIST_PATH = os.getenv("WHITELIST_PATH", "/app/data/whitelist.csv")
EVENTS_PATH = os.getenv("EVENTS_PATH", "/app/data/events.csv")

def load_whitelist():
    """Charger la liste des emails autorisés avec leur type de membership"""
    whitelist = {}
    try:
        with open(WHITELIST_PATH, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row['email'].strip().lower()
                display_name = row['display_name']
                membership_type = row.get('membership_type', 'full_member').strip()
                credits_str = row.get('credits', '').strip()
                # Si credits est vide ou pas un nombre, mettre None (unlimited)
                credits = int(credits_str) if credits_str.isdigit() else None
 
                
                whitelist[email] = {
                    'display_name': display_name,
                    'membership_type': membership_type,
                    'initial_credits': credits
                }
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
                    'id': row['id'],  # ← AJOUTE CETTE LIGNE
                    'date': row['date'],
                    'max_spots': int(row['max_spots'])
                })
    except FileNotFoundError:
        print(f"Warning: Events file not found at {EVENTS_PATH}")
    return events