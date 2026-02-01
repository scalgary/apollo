from sqlalchemy.orm import Session
from db_models import Admin, User, EventType, UserEventTypeMembership, Event
from utils import load_events, load_event_types, load_admins



class AdminService:
    """Service pour gérer les administrateurs"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def import_admins_from_csv(self):
        """
        Import admins depuis CSV et créer leurs comptes users automatiquement.
        
        Logique:
        1. Lire admins.csv (admin_email, display_name, real_name)
        2. Lire env vars (ADMIN_EMAIL_1/2, ADMIN_PASSWORD_1/2)
        3. Pour chaque admin:
        - Créer user si n'existe pas
        - Créer memberships punch_card 0 crédits
        - Créer entrée dans table admins
        
        Returns:
            int: Nombre d'admins importés
        """
        from db_models import User, UserEventTypeMembership, EventType
        from services.auth_service import AuthService
        import os
    
        # 1. Charger admins.csv
        admins_data = load_admins()
    
        # 2. Charger passwords depuis env vars
        admin_passwords = {}
        for i in range(1, 3):  # ADMIN_EMAIL_1 et ADMIN_EMAIL_2
            email_key = f'ADMIN_EMAIL_{i}'
            password_key = f'ADMIN_PASSWORD_{i}'
            
            email = os.getenv(email_key)
            password = os.getenv(password_key)
            
            if email and password:
                admin_passwords[email.strip().lower()] = password
            elif email or password:
                # Un des deux manque
                raise ValueError(f"Missing {email_key} or {password_key} in environment variables")
        
        if not admin_passwords:
            raise ValueError("No admin passwords found in environment variables (ADMIN_EMAIL_1/2, ADMIN_PASSWORD_1/2)")
        
        # 3. Récupérer tous les event types
        event_types = self.db.query(EventType).all()
        if not event_types:
            print("Warning: No event types found, admins will have no memberships")
        
        auth_service = AuthService(self.db)
        imported_count = 0
        
        # 4. Pour chaque admin dans CSV
        for admin_data in admins_data:
            admin_email = admin_data['admin_email']
            display_name = admin_data['display_name']
            real_name = admin_data['real_name']
            
            # Vérifier que le password existe
            if admin_email not in admin_passwords:
                raise ValueError(f"Admin {admin_email} in CSV but no password in env vars")
            
            password = admin_passwords[admin_email]
            
            try:
                # 5. Vérifier si user existe déjà
                existing_user = self.db.query(User).filter(User.email == admin_email).first()
                
                if existing_user:
                    print(f"Admin user {admin_email} already exists, skipping user creation")
                    user_id = existing_user.id
                else:
                    # 6. Créer le user
                    hashed_password = auth_service.hash_password(password)
                    new_user = User(
                        email=admin_email,
                        hashed_password=hashed_password,
                        display_name=display_name,
                        real_name=real_name
                    )
                    self.db.add(new_user)
                    self.db.flush()  # Pour obtenir l'ID
                    user_id = new_user.id
                    print(f"✓ Created admin user: {admin_email}")
                    
                    # 7. Créer memberships punch_card 0 crédits pour tous les event types
                    for event_type in event_types:
                        membership = UserEventTypeMembership(
                            user_id=user_id,
                            event_type_id=event_type.id,
                            membership_type='punch_card',
                            total_credits_purchased=0,
                            remaining_credits=0
                        )
                        self.db.add(membership)
                    
                    print(f"✓ Created {len(event_types)} punch_card memberships (0 credits)")
                
                # 8. Créer/update entrée dans table admins
                existing_admin = self.db.query(Admin).filter(Admin.admin_email == admin_email).first()
                
                if not existing_admin:
                    new_admin = Admin(
                        user_id=user_id,
                        admin_email=admin_email
                    )
                    self.db.add(new_admin)
                    imported_count += 1
                    print(f"✓ Created admin entry for {admin_email}")
                else:
                    # Update user_id au cas où
                    existing_admin.user_id = user_id
                    print(f"✓ Updated admin entry for {admin_email}")
                
            except Exception as e:
                print(f"Error importing admin {admin_email}: {e}")
                raise
        
        self.db.commit()
        return imported_count
        

    def is_user_admin(self, user_id: int) -> bool:
        """
        Vérifie si un user_id est admin.
        
        Args:
            user_id: ID du user
        
        Returns:
            bool: True si admin, False sinon
        """
        admin = self.db.query(Admin).filter(Admin.user_id == user_id).first()
        return admin is not None
    
    
    def is_email_admin(self, email: str) -> bool:
        """
        Vérifie si un email est dans la liste des admins.
        
        Utile pour login/permissions basées sur email.
        
        Args:
            email: Email à vérifier
        
        Returns:
            bool: True si admin, False sinon
        """
        email_lower = email.strip().lower()
        admin = self.db.query(Admin).filter(Admin.admin_email == email_lower).first()
        return admin is not None
    
    
    def get_admin_emails(self) -> list[str]:
        """
        Récupère tous les emails admins pour notifications.
        
        Returns:
            list[str]: Liste des admin_email
        """
        admins = self.db.query(Admin).all()
        return [admin.admin_email for admin in admins]
    
    
    def link_user_to_admin(self, user_id: int, admin_email: str) -> bool:
        """
        Lie un user existant à un admin existant.
        
        Utile quand un admin s'inscrit comme user après coup.
        
        Args:
            user_id: ID du user
            admin_email: Email de l'admin
        
        Returns:
            bool: True si lien créé, False si admin pas trouvé
        """
        admin = self.db.query(Admin).filter(Admin.admin_email == admin_email).first()
        
        if not admin:
            return False
        
        # Update le user_id
        admin.user_id = user_id
        self.db.commit()
        return True
        
    def create_event_type(
        self,
        display_name: str,
        default_location: str,
        default_time_start: str,
        default_time_end: str,
        default_max_capacity: int,
        color: str
    ) -> EventType:
        """
        Create a new event type
        
        Auto-generates event_type_name based on color (event_1, event_2, etc.)
        Max 4 event types allowed
        
        Raises:
            ValueError: If validation fails or max limit reached
        """
        import re
        from datetime import datetime
        
        # 0. CHECK MAX LIMIT
        current_count = self.get_event_type_count()
        if current_count >= 4:
            raise ValueError("Maximum 4 event types allowed. Delete one to create a new one.")
        
        # 1. Map color to event_type_name
        color_to_name = {
            '#3b82f6': 'event_1',  # Blue
            '#f97316': 'event_2',  # Orange
            '#10b981': 'event_3',  # Green
            '#8b5cf6': 'event_4',  # Purple
        }
        
        event_type_name = color_to_name.get(color.strip())
        
        if not event_type_name:
            raise ValueError(f"Invalid color: {color}. Must be one of the 4 allowed colors.")
        
        # 2. Check if this color already used
        existing = self.db.query(EventType).filter(EventType.color == color.strip()).first()
        if existing:
            raise ValueError(f"Color already in use by '{existing.display_name}'")
        
        # 3. Validate time format
        time_pattern = r'^([0-9]|[01][0-9]|2[0-3]):([0-5][0-9])$'
        
        if not re.match(time_pattern, default_time_start):
            raise ValueError(f"Invalid start time format: {default_time_start}. Use HH:MM")
        
        if not re.match(time_pattern, default_time_end):
            raise ValueError(f"Invalid end time format: {default_time_end}. Use HH:MM")
        
        # 4. Normalize times
        def normalize_time(time_str):
            parts = time_str.split(':')
            return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
        
        start_normalized = normalize_time(default_time_start)
        end_normalized = normalize_time(default_time_end)
        
        # 5. Validate start < end
        start_dt = datetime.strptime(start_normalized, '%H:%M')
        end_dt = datetime.strptime(end_normalized, '%H:%M')
        
        if start_dt >= end_dt:
            raise ValueError("Start time must be before end time")
        
        # 6. Create EventType
        new_event_type = EventType(
            event_type_name=event_type_name,
            display_name=display_name.strip(),
            default_location=default_location.strip(),
            default_time_start=start_normalized,
            default_time_end=end_normalized,
            default_max_capacity=default_max_capacity,
            color=color.strip()
        )
        
        self.db.add(new_event_type)
        self.db.commit()
        self.db.refresh(new_event_type)
        
        return new_event_type

    def delete_event_type(self, event_type_id: int) -> dict:
        """
        Delete an event type
        
        Rules:
        - Cannot delete if ANY future events exist
        - Deletes all UserEventTypeMembership for this event type (CASCADE)
        - Updates whitelist.csv to remove memberships for this event type
        
        Returns:
            dict: Success message
            
        Raises:
            ValueError: If has future events or not found
        """
        from datetime import date
        import csv
        import os
        
        # 1. Check event type exists
        event_type = self.db.query(EventType).filter(EventType.id == event_type_id).first()
        if not event_type:
            raise ValueError("Event type not found")
        
        event_type_name = event_type.event_type_name
        display_name = event_type.display_name
        
        # 2. Check for future events (INCLUDING TODAY)
        today = date.today()
        future_events_count = self.db.query(Event).filter(
            Event.event_type_id == event_type_id,
            Event.date >= today
        ).count()
        
        if future_events_count > 0:
            raise ValueError(
                f"Cannot delete '{display_name}' - {future_events_count} upcoming event(s) scheduled. "
                f"Delete all future events for this type first."
            )
        
        # 3. Delete UserEventTypeMembership for this event type
        deleted_memberships = self.db.query(UserEventTypeMembership).filter(
            UserEventTypeMembership.event_type_id == event_type_id
        ).delete()
        
        # 4. Delete the event type
        self.db.delete(event_type)
        self.db.commit()
        
        # 5. Update whitelist.csv to remove this event type's memberships
        #mwhitelist_path = 'data/whitelist.csv'
        
        # if os.path.exists(whitelist_path):
        #     # Read existing whitelist
        #     whitelist_data = []
            
        #     with open(whitelist_path, 'r', encoding='utf-8') as f:
        #         reader = csv.DictReader(f)
        #         for row in reader:
        #             # Keep only rows NOT for this event type
        #             if row['event_type_name'] != event_type_name:
        #                 whitelist_data.append(row)
            
        #     # Write back filtered data
        #     with open(whitelist_path, 'w', newline='', encoding='utf-8') as f:
                # if whitelist_data:
                #     fieldnames = ['email', 'real_name', 'event_type_name', 'membership_type', 'total_credits_purchased']
                #     writer = csv.DictWriter(f, fieldnames=fieldnames)
                #     writer.writeheader()
                #     writer.writerows(whitelist_data)
                # else:
                #     # Empty file if no data left
                #     f.write('')
        
        return {
            "success": True,
            "message": f"Event type '{display_name}' deleted successfully ({deleted_memberships} memberships removed)"
        }


    def can_delete_event_type(self, event_type_id: int) -> dict:
        """
        Check if an event type can be deleted
        
        Returns:
            dict: {
                'can_delete': bool,
                'reason': str or None,
                'future_events_count': int
            }
        """
        from datetime import date
        
        event_type = self.db.query(EventType).filter(EventType.id == event_type_id).first()
        if not event_type:
            return {
                'can_delete': False,
                'reason': 'Event type not found',
                'future_events_count': 0
            }
        
        today = date.today()
        future_events_count = self.db.query(Event).filter(
            Event.event_type_id == event_type_id,
            Event.date >= today
        ).count()
        
        if future_events_count > 0:
            return {
                'can_delete': False,
                'reason': f'{future_events_count} upcoming event(s) scheduled',
                'future_events_count': future_events_count
            }
        
        return {
            'can_delete': True,
            'reason': None,
            'future_events_count': 0
        }

    def get_event_type_count(self) -> int:
        """Get current number of event types"""
        return self.db.query(EventType).count()
    
    
    # ============================================
    # MEMBERSHIP MANAGEMENT
    # ============================================
    
    def bulk_add_memberships(self, event_type_id: int, membership_type: str, emails_text: str, credits: int) -> dict:
        """
        Add memberships by adding/updating Friends table
        
        Args:
            event_type_id: ID of event type
            membership_type: 'full_member' or 'punch_card'
            emails_text: Text with emails (comma or newline separated)
            credits: Credits for punch_card
        
        Returns:
            dict: Summary of added emails
        """
        import re
        from db_models import Friend, EventType
        
        # Parse emails
        emails = re.split(r'[,\s\n]+', emails_text.strip())
        emails = [e.lower().strip() for e in emails if e and '@' in e]
        
        if not emails:
            raise ValueError("No valid emails provided")
        
        # Validate event type exists
        event_type = self.db.query(EventType).filter(EventType.id == event_type_id).first()
        if not event_type:
            raise ValueError("Event type not found")
        
        # Validate membership type
        if membership_type not in ['full_member', 'punch_card']:
            raise ValueError("Invalid membership type")
        
        # Validate credits for punch_card
        if membership_type == 'punch_card' and credits <= 0:
            raise ValueError("Punch card requires credits > 0")
        
        added_count = 0
        updated_count = 0
        
        for email in emails:
            # Check if Friend already exists for this email + event_type
            existing_friend = self.db.query(Friend).filter(
                Friend.email == email,
                Friend.event_type_id == event_type_id
            ).first()
            
            if existing_friend:
                # Update existing Friend
                existing_friend.membership_type = membership_type
                if membership_type == 'punch_card':
                    current_credits = existing_friend.total_credits_purchased or 0
                    existing_friend.total_credits_purchased = current_credits + credits
                else:
                    existing_friend.total_credits_purchased = None
                updated_count += 1
            else:
                # Create new Friend
                new_friend = Friend(
                    email=email,
                    real_name='Unknown',
                    event_type_id=event_type_id,
                    membership_type=membership_type,
                    total_credits_purchased=credits if membership_type == 'punch_card' else None
                )
                self.db.add(new_friend)
                added_count += 1
            # Check if user is signed up and create UserEventTypeMembership
            user = self.db.query(User).filter(User.email == email).first()
            if user:
                user_membership = self.db.query(UserEventTypeMembership).filter(
                    UserEventTypeMembership.user_id==user.id,
                    UserEventTypeMembership.event_type_id==event_type_id
                ).first()
                if not user_membership:
                    user_membership=UserEventTypeMembership(
                        user_id=user.id,
                        event_type_id=event_type_id,
                        membership_type=membership_type,
                        total_credits_purchased=credits if membership_type=='punch_card' else None,
                        remaining_credits = credits if membership_type =='punch_card' else None
                    )
                    self.db.add(user_membership)
                else:
                    if membership_type=='punch_card':
                        user_membership.total_credits_purchased += credits
                        user_membership.remaining_credits += credits
                


        
        self.db.commit()
        
        return {
            'message': f'Added {added_count} new, updated {updated_count} existing memberships for {event_type.display_name}',
            'added': added_count,
            'updated': updated_count
        }
    
    def add_credits(self, user_id: int, event_type_id: int, credits_to_add: int) -> dict:
        """
        Add credits to user's punch card
        
        Args:
            user_id: ID of user
            event_type_id: ID of event type
            credits_to_add: Number of credits to add
        
        Returns:
            dict: Success message
            
        Raises:
            ValueError: If membership not found or not punch_card
        """
        membership = self.db.query(UserEventTypeMembership).filter(
            UserEventTypeMembership.user_id == user_id,
            UserEventTypeMembership.event_type_id == event_type_id
        ).first()
        
        if not membership:
            raise ValueError("Membership not found")
        
        if membership.membership_type != 'punch_card':
            raise ValueError("Can only add credits to punch card memberships")
        
        # Add credits
        if membership.total_credits_purchased is None:
            membership.total_credits_purchased = 0
        if membership.remaining_credits is None:
            membership.remaining_credits = 0
        
        membership.total_credits_purchased += credits_to_add
        membership.remaining_credits += credits_to_add
        
        self.db.commit()
        
        # Get user and event type for message
        user = self.db.query(User).filter(User.id == user_id).first()
        event_type = self.db.query(EventType).filter(EventType.id == event_type_id).first()
        
        return {
            'message': f'Added {credits_to_add} credits to {user.email} for {event_type.display_name}'
        }
        
    def get_all_users_with_memberships(self) -> list[dict]:
        """
        Get all memberships from Friends table with signup status
        
        Shows:
        - All emails in Friends table (signed up or not)
        - Their memberships from Friends table
        - Actual remaining credits AND total credits from DB if signed up
        
        Returns:
            list[dict]: Memberships with user info if signed up
        """
        from db_models import Friend, User, UserEventTypeMembership
        
        event_types = self.db.query(EventType).order_by(EventType.id).all()
        
        # Get all unique emails from Friends table
        all_friends = self.db.query(Friend).all()
        unique_emails = list(set(f.email for f in all_friends))
        
        result = []
        
        for email in sorted(unique_emails):
            # Check if user signed up
            user = self.db.query(User).filter(User.email == email).first()
            
            memberships_list = []
            
            for event_type in event_types:
                # Get Friend entry for this email + event_type
                friend = self.db.query(Friend).filter(
                    Friend.email == email,
                    Friend.event_type_id == event_type.id
                ).first()
                
                if friend:
                    # Default values from Friends table
                    remaining_credits = friend.total_credits_purchased
                    total_credits = friend.total_credits_purchased
                    
                    # If user signed up, get ACTUAL values from UserEventTypeMembership
                    if user:
                        db_membership = self.db.query(UserEventTypeMembership).filter(
                            UserEventTypeMembership.user_id == user.id,
                            UserEventTypeMembership.event_type_id == event_type.id
                        ).first()
                        
                        if db_membership:
                            # Use DB values (these are updated when admin adds credits)
                            if db_membership.remaining_credits is not None:
                                remaining_credits = db_membership.remaining_credits
                            if db_membership.total_credits_purchased is not None:
                                total_credits = db_membership.total_credits_purchased
                    
                    memberships_list.append({
                        'event_type_id': event_type.id,
                        'event_type_name': event_type.display_name,
                        'membership_type': friend.membership_type,
                        'total_credits': total_credits,  # ← Changed: use actual total from DB
                        'remaining_credits': remaining_credits
                    })
                else:
                    memberships_list.append({
                        'event_type_id': event_type.id,
                        'event_type_name': event_type.display_name,
                        'membership_type': None,
                        'total_credits': None,
                        'remaining_credits': None
                    })
            
            result.append({
                'email': email,
                'user_id': user.id if user else None,
                'display_name': user.display_name if user else '(Not signed up)',
                'signed_up': user is not None,
                'memberships': memberships_list
            })
        
        return result
    def bulk_create_events(self, event_type_id: int, dates_text: str) -> dict:
        """
        Create multiple events for an event type
        
        Args:
            event_type_id: ID of event type
            dates_text: Text with dates (newline separated, format YYYY-MM-DD)
        
        Returns:
            dict: Success message with count
        """
        from datetime import datetime
        
        # Validate event type exists
        event_type = self.db.query(EventType).filter(EventType.id == event_type_id).first()
        if not event_type:
            raise ValueError("Event type not found")
        
        # Parse dates
        lines = [line.strip() for line in dates_text.strip().split('\n') if line.strip()]
        
        created_count = 0
        skipped_count = 0
        errors = []
        
        for line in lines:
            try:
                # Parse date
                event_date = datetime.strptime(line, '%Y-%m-%d').date()
                
                # Check if already exists
                existing = self.db.query(Event).filter(Event.date == event_date).first()
                
                if existing:
                    skipped_count += 1
                    continue
                
                # Create event
                new_event = Event(
                    event_type_id=event_type_id,
                    date=event_date,
                    confirmed_count=0
                )
                self.db.add(new_event)
                created_count += 1
                
            except ValueError as e:
                errors.append(f"Invalid date '{line}': {str(e)}")
        
        self.db.commit()
        
        message = f"Created {created_count} events for {event_type.display_name}"
        if skipped_count > 0:
            message += f" (skipped {skipped_count} duplicates)"
        if errors:
            message += f" - Errors: {'; '.join(errors[:3])}"
        
        return {'message': message, 'created': created_count}
    
    def manage_event_dates(self, event_type_id: int, dates_to_add: list[str], dates_to_delete: list[str]) -> dict:
        """
        Add and delete event dates
        
        Args:
            event_type_id: ID of event type
            dates_to_add: List of dates to add (YYYY-MM-DD)
            dates_to_delete: List of dates to delete (YYYY-MM-DD)
        
        Returns:
            dict: Success message with counts
        """
        from datetime import datetime
        
        # Validate event type
        event_type = self.db.query(EventType).filter(EventType.id == event_type_id).first()
        if not event_type:
            raise ValueError("Event type not found")
        
        added_count = 0
        deleted_count = 0
        errors = []
        
        # Delete dates
        for date_str in dates_to_delete:
            try:
                event_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                event = self.db.query(Event).filter(
                    Event.event_type_id == event_type_id,
                    Event.date == event_date
                ).first()
                
                if event:
                    self.db.delete(event)
                    deleted_count += 1
                
            except ValueError as e:
                errors.append(f"Invalid date '{date_str}': {str(e)}")
        
        # Add dates
        for date_str in dates_to_add:
            try:
                event_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                # Check if already exists
                existing = self.db.query(Event).filter(Event.date == event_date).first()
                
                if existing:
                    errors.append(f"Date {date_str} already exists")
                    continue
                
                # Create event
                new_event = Event(
                    event_type_id=event_type_id,
                    date=event_date,
                    confirmed_count=0
                )
                self.db.add(new_event)
                added_count += 1
                
            except ValueError as e:
                errors.append(f"Invalid date '{date_str}': {str(e)}")
        
        self.db.commit()
        
        message = f"Added {added_count}, deleted {deleted_count} dates"
        if errors:
            message += f" - Errors: {'; '.join(errors[:3])}"
        
        return {'success': True, 'message': message}
    def delete_user_membership(self, user_id: int, event_type_id: int) -> dict:
        """
        Delete a user's membership for a specific event type
        
        Also removes from Friends table and cancels future registrations
        
        Args:
            user_id: ID of user
            event_type_id: ID of event type
        
        Returns:
            dict: Success message
            
        Raises:
            ValueError: If user is admin or membership not found
        """
        from db_models import User, UserEventTypeMembership, Attendee, Friend, Event
        from datetime import date
        
        print(f"🔍 DEBUG delete_user_membership: user_id={user_id}, event_type_id={event_type_id}")
        
        # 1. Check user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"❌ User not found: {user_id}")
            raise ValueError("User not found")
        
        print(f"✅ User found: {user.email}")
        
        # 2. Check user is not admin
        if self.is_user_admin(user_id):
            raise ValueError("Cannot delete admin memberships")
        
        # 3. Get event type for display name
        event_type = self.db.query(EventType).filter(EventType.id == event_type_id).first()
        if not event_type:
            raise ValueError("Event type not found")
        
        print(f"✅ Event type found: {event_type.display_name}")
        
        # 4. Cancel all FUTURE registrations for this event type
        today = date.today()
        
        # Get all future event IDs for this event type
        future_events = self.db.query(Event).filter(
            Event.event_type_id == event_type_id,
            Event.date >= today
        ).all()
        
        future_event_ids = [e.id for e in future_events]
        print(f"📅 Found {len(future_event_ids)} future events for this type")
        
        # Delete attendee records
        cancelled_count = 0
        if future_event_ids:
            # Get attendees before deleting to update event confirmed_count
            attendees_to_cancel = self.db.query(Attendee).filter(
                Attendee.user_id == user_id,
                Attendee.event_id.in_(future_event_ids)
            ).all()
            
            for attendee in attendees_to_cancel:
                # If user was 'going', decrement the event's confirmed_count
                if attendee.status == 'going':
                    event = self.db.query(Event).filter(Event.id == attendee.event_id).first()
                    if event and event.confirmed_count > 0:
                        event.confirmed_count -= 1
                
                self.db.delete(attendee)
                cancelled_count += 1
            
            print(f"❌ Cancelled {cancelled_count} future registration(s)")
        
        # 5. Delete membership (if exists)
        membership = self.db.query(UserEventTypeMembership).filter(
            UserEventTypeMembership.user_id == user_id,
            UserEventTypeMembership.event_type_id == event_type_id
        ).first()
        
        if membership:
            print(f"🗑️  Deleting membership: {membership.membership_type}")
            self.db.delete(membership)
        else:
            print(f"⚠️  No membership found in user_event_type_memberships (might be OK)")
        
        # 6. Delete from Friends table
        deleted_friends = self.db.query(Friend).filter(
            Friend.email == user.email,
            Friend.event_type_id == event_type_id
        ).delete()
        
        print(f"🗑️  Deleted {deleted_friends} entry/entries from Friends table")
        
        self.db.commit()
        
        message = f"Removed {user.email} from {event_type.display_name}"
        if cancelled_count > 0:
            message += f" (cancelled {cancelled_count} future registration"
            """
            Delete a user's membership for a specific event type
            
            Also removes from Friends table and cancels future registrations
            
            Args:
                user_id: ID of user
                event_type_id: ID of event type
            
            Returns:
                dict: Success message
                
            Raises:
                ValueError: If user is admin or membership not found
            """
            from db_models import User, UserEventTypeMembership, Attendee, Friend, Event
            from datetime import date
            
            # 1. Check user exists
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                raise ValueError("User not found")
            
            # 2. Check user is not admin
            if self.is_user_admin(user_id):
                raise ValueError("Cannot delete admin memberships")
            
            # 3. Get event type for display name
            event_type = self.db.query(EventType).filter(EventType.id == event_type_id).first()
            if not event_type:
                raise ValueError("Event type not found")
            
            # 4. Get membership
            membership = self.db.query(UserEventTypeMembership).filter(
                UserEventTypeMembership.user_id == user_id,
                UserEventTypeMembership.event_type_id == event_type_id
            ).first()
            
            if not membership:
                raise ValueError(f"User has no membership for {event_type.display_name}")
            
            # 5. Cancel all FUTURE registrations for this event type
            today = date.today()
            
            # Get all future event IDs for this event type
            future_events = self.db.query(Event.id).filter(
                Event.event_type_id == event_type_id,
                Event.date >= today
            ).all()
            
            future_event_ids = [e.id for e in future_events]
            
            # Delete attendee records
            cancelled_count = 0
            if future_event_ids:
                cancelled_count = self.db.query(Attendee).filter(
                    Attendee.user_id == user_id,
                    Attendee.event_id.in_(future_event_ids)
                ).delete(synchronize_session=False)
            
            # 6. Delete membership
            self.db.delete(membership)
            
            # 7. Delete from Friends table
            self.db.query(Friend).filter(
                Friend.email == user.email,
                Friend.event_type_id == event_type_id
            ).delete()
            
            self.db.commit()
            
            message = f"Removed {user.email} from {event_type.display_name}"
            if cancelled_count > 0:
                message += f" (cancelled {cancelled_count} future registration(s))"
            
            return {
                'success': True,
                'message': message
            }