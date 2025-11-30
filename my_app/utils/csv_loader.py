import csv
import os

# Permet override pour les tests
WHITELIST_PATH = os.getenv("WHITELIST_PATH", "/app/data/whitelist.csv")
EVENTS_PATH = os.getenv("EVENTS_PATH", "/app/data/events.csv")

def load_whitelist():
    """
    Charger la liste des emails autorisés avec leurs memberships.
    
    Règles de sécurité :
    - Si un event_type manque pour un user, il reçoit punch_card avec 0 crédits
    
    Retourne:
    {
        'user1@example.com': {
            'real_name': 'Alice',
            'memberships': [
                {'event_type_name': 'open_play', 'membership_type': 'full_member', 'total_credits_purchased': None},
                {'event_type_name': 'competitive', 'membership_type': 'punch_card', 'total_credits_purchased': 10}
            ]
        }
    }
    """
    EVENT_TYPES = ['open_play', 'competitive']
    
    whitelist = {}
    try:
        with open(WHITELIST_PATH, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row['email'].strip().lower()
                real_name = row['real_name'].strip()
                event_type_name = row['event_type_name'].strip()
                membership_type = row['membership_type'].strip()
                credits_str = row.get('total_credits_purchased', '').strip()
                
                # Convertir credits
                total_credits = int(credits_str) if credits_str else None
                
                # Créer l'entrée user si n'existe pas
                if email not in whitelist:
                    whitelist[email] = {
                        'real_name': real_name,
                        'memberships': []
                    }
                
                # Ajouter le membership
                whitelist[email]['memberships'].append({
                    'event_type_name': event_type_name,
                    'membership_type': membership_type,
                    'total_credits_purchased': total_credits
                })
        
        # RÈGLE : Ajouter event_types manquants avec punch_card 0 crédits
        for email, data in whitelist.items():
            existing_types = {m['event_type_name'] for m in data['memberships']}
            missing_types = set(EVENT_TYPES) - existing_types
            
            for event_type in missing_types:
                data['memberships'].append({
                    'event_type_name': event_type,
                    'membership_type': 'punch_card',
                    'total_credits_purchased': 0
                })
                
    except FileNotFoundError:
        print(f"Warning: Whitelist file not found at {WHITELIST_PATH}")
    
    return whitelist

def load_events():
    """
    Charger les événements depuis CSV.
    
    Format CSV attendu:
    event_type_name,date
    open_play,2025-12-05
    competitive,2025-12-08
    """
    events = []
    try:
        with open(EVENTS_PATH, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                events.append({
                    'event_type_name': row['event_type_name'].strip(),
                    'date': row['date'].strip()
                })
    except FileNotFoundError:
        print(f"Warning: Events file not found at {EVENTS_PATH}")
    return events





def load_event_types():
    """
    Charge event_type.csv
    Charger les événements type depuis CSV.
    name,display_name,default_location,default_time_start,default_time_end,default_max_capacity,color
    open_play,Intérieur,Calgary Indoor Sports Arena,19:00,21:00,20,#4A90E2
    competitive,Extérieur,Riley Park Outdoor Courts,14:00,16:00,16,#7ED321
    Format CSV attendu:
    """

    import csv
    event_types = []
    
    with open('data/event_types.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            event_types.append({
                'name': row['name'],
                'display_name': row['display_name'],
                'default_location': row['default_location'],
                'default_time_start': row['default_time_start'],
                'default_time_end': row['default_time_end'],
                'default_max_capacity': int(row['default_max_capacity']),
                'color': row['color']
            })
    
    return event_types
