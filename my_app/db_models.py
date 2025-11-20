#db_models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Date, Time
from sqlalchemy.sql import func
from database import Base
from sqlalchemy.orm import relationship  # ← Assurez-vous d'avoir cet import

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    real_name = Column(String, nullable=False)

    hashed_password = Column(String, nullable=False)
    membership_type = Column(String, default='full_member')  # 'full_member' ou 'punch_card'
    initial_credits = Column(Integer, nullable=True)  # Nombre total de crédits autorisés (None = unlimited)
    remaining_credits = Column(Integer, nullable=True)  # Crédits restants (None = unlimited)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# Dans le même fichier db_models.py

class Event(Base):
    __tablename__ = 'events'
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    event_type_id = Column(Integer, ForeignKey('event_types.id'), nullable=False)
    confirmed_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relation : un Event appartient à un EventType
    event_type = relationship("EventType", back_populates="events")

class Attendee(Base):
    __tablename__ = 'attendees'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    status = Column(String, default='going')
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (UniqueConstraint('user_id', 'event_id', name='unique_user_event'),)

class PasswordReset(Base):
    __tablename__ = 'password_resets'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    token = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ========== NOUVELLE CLASSE ==========
class EventType(Base):
    __tablename__ = 'event_types'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=False)
    default_location = Column(String, nullable=False)
    default_time_start = Column(Time, nullable=False)
    default_time_end = Column(Time, nullable=False)
    default_max_capacity = Column(Integer, nullable=False)
    color = Column(String, nullable=True)
    
    # Relation : un EventType peut avoir plusieurs Events
    events = relationship("Event", back_populates="event_type")