# backend/utils/csv_loader.py
import csv
from pathlib import Path

def load_events():
    """Load events from CSV file"""
    events = []
    csv_path = Path('data/events.csv')
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        events = list(reader)
    
    return events

def load_whitelist():
    """Load allowed emails from CSV file"""
    with open('data/whitelist.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        emails = [row['email_address'].strip() for row in reader]
    return emails