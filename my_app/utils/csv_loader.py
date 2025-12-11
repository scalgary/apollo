import csv
import os

# Paths with environment variable override for tests
WHITELIST_PATH = os.getenv("WHITELIST_PATH", "/app/data/whitelist.csv")
EVENTS_PATH = os.getenv("EVENTS_PATH", "/app/data/events.csv")
MEMBERSHIP_PERIODS_PATH = os.getenv("MEMBERSHIP_PERIODS_PATH", "/app/data/membership_periods.csv")
EVENT_TYPE_CONFIGS_PATH = os.getenv("EVENT_TYPE_CONFIGS_PATH", "/app/data/event_type_configs.csv")
ADMINS_PATH = os.getenv("ADMINS_PATH", "/app/data/admins.csv")


def load_membership_periods():
    """
    Load membership periods from CSV.
    
    CSV format:
    period_name,start_date,end_date,notes
    Fall 2025,2025-10-01,2025-12-31,Fall indoor season
    
    Returns:
    [
        {
            'period_name': 'Fall 2025',
            'start_date': '2025-10-01',
            'end_date': '2025-12-31',
            'notes': 'Fall indoor season'
        }
    ]
    """
    periods = []
    try:
        with open(MEMBERSHIP_PERIODS_PATH, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                periods.append({
                    'period_name': row['period_name'].strip(),
                    'start_date': row['start_date'].strip(),
                    'end_date': row['end_date'].strip(),
                    'notes': row.get('notes', '').strip()
                })
    except FileNotFoundError:
        print(f"ERROR: Membership periods file not found at {MEMBERSHIP_PERIODS_PATH}")
        raise
    
    return periods


def load_event_type_configs():
    """
    Load event type configurations from CSV.
    
    CSV format:
    event_type_name,period_name,display_name,location,time_start,time_end,max_capacity,color
    open_play,Fall 2025,Thursday Indoor,Calgary Arena,19:00,21:00,20,#3b82f6
    
    Returns:
    [
        {
            'event_type_name': 'open_play',
            'period_name': 'Fall 2025',
            'display_name': 'Thursday Indoor',
            'location': 'Calgary Arena',
            'time_start': '19:00',
            'time_end': '21:00',
            'max_capacity': 20,
            'color': '#3b82f6'
        }
    ]
    """
    configs = []
    try:
        with open(EVENT_TYPE_CONFIGS_PATH, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                configs.append({
                    'event_type_name': row['event_type_name'].strip(),
                    'period_name': row['period_name'].strip(),
                    'display_name': row['display_name'].strip(),
                    'location': row['location'].strip(),
                    'time_start': row['time_start'].strip(),
                    'time_end': row['time_end'].strip(),
                    'max_capacity': int(row['max_capacity']),
                    'color': row['color'].strip()
                })
    except FileNotFoundError:
        print(f"ERROR: Event type configs file not found at {EVENT_TYPE_CONFIGS_PATH}")
        raise
    
    return configs


def load_whitelist():
    """
    Load whitelist with memberships linked to periods.
    
    CSV format:
    email,real_name,event_type_name,membership_type,total_credits_purchased,period_name
    user1@example.com,User One,open_play,full_member,,Fall 2025
    
    Returns:
    {
        'user1@example.com': {
            'real_name': 'User One',
            'memberships': [
                {
                    'event_type_name': 'open_play',
                    'membership_type': 'full_member',
                    'total_credits_purchased': None,
                    'period_name': 'Fall 2025'
                }
            ]
        }
    }
    """
    whitelist = {}
    try:
        with open(WHITELIST_PATH, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row['email'].strip().lower()
                real_name = row['real_name'].strip()
                event_type_name = row['event_type_name'].strip()
                membership_type = row['membership_type'].strip()
                credits_str = (row.get('total_credits_purchased') or '').strip()
                period_name = row['period_name'].strip()
                
                # Convert credits
                total_credits = int(credits_str) if credits_str else None
                
                # Create user entry if doesn't exist
                if email not in whitelist:
                    whitelist[email] = {
                        'real_name': real_name,
                        'memberships': []
                    }
                
                # Add membership with period
                whitelist[email]['memberships'].append({
                    'event_type_name': event_type_name,
                    'membership_type': membership_type,
                    'total_credits_purchased': total_credits,
                    'period_name': period_name
                })
                
    except FileNotFoundError:
        print(f"Warning: Whitelist file not found at {WHITELIST_PATH}")
    
    return whitelist


def load_events():
    """
    Load events from CSV.
    
    CSV format:
    event_type_name,date
    open_play,2025-10-02
    competitive,2025-10-05
    
    Returns:
    [
        {
            'event_type_name': 'open_play',
            'date': '2025-10-02'
        }
    ]
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


def load_admins():
    """
    Load admin emails from CSV.
    
    CSV format:
    admin_email
    admin@example.com
    
    Returns:
    ['admin@example.com']
    """
    admins = []
    
    try:
        with open(ADMINS_PATH, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                admin_email = row['admin_email'].strip().lower()
                admins.append(admin_email)
                
    except FileNotFoundError:
        print(f"ERROR: Admins file not found at {ADMINS_PATH}")
        raise
    
    return admins