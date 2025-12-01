Logique des data

# Tests
## Users

Users can have different memberships - at least one by event
Users can have just 1 membership - the other is punchcard 0 by default 
Users CANT have more than 2 memberships for same event -id-
    __table_args__ = (UniqueConstraint('user_id', 'event_type_id', name='unique_user_event_type'),)
Users have default membership punchcard at 0

## Events 
Same user CANT be twice in attendees table

