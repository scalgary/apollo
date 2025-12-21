#db_models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint, Date
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    real_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EventType(Base):
    __tablename__ = 'event_types'
    
    id = Column(Integer, primary_key=True, index=True)
    event_type_name = Column(String, unique=True, nullable=False)  # Auto-generated from display_name
    display_name = Column(String, nullable=False)  # 'JCC Sunday' ou 'Indoor Play'
    default_location = Column(String, nullable=False)
    default_time_start = Column(String, nullable=False)  # '19:00'
    default_time_end = Column(String, nullable=False)  # '21:00'
    default_max_capacity = Column(Integer, nullable=False)
    color = Column(String, unique=True, nullable=False)  # '#4A90E2' - UNIQUE IDENTIFIER
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserEventTypeMembership(Base):
    __tablename__ = 'user_event_type_memberships'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    event_type_id = Column(Integer, ForeignKey('event_types.id'), nullable=False)
    membership_type = Column(String, nullable=False)
    total_credits_purchased = Column(Integer, nullable=True)
    remaining_credits = Column(Integer, nullable=True)  # ← NOUVEAU
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (UniqueConstraint('user_id', 'event_type_id', name='unique_user_event_type'),)

class Event(Base):
    __tablename__ = 'events'
    
    id = Column(Integer, primary_key=True, index=True)
    event_type_id = Column(Integer, ForeignKey('event_types.id'), nullable=False)
    date = Column(Date, nullable=False, unique=True)
    confirmed_count = Column(Integer, default=0)  # ← AJOUTE CETTE LIGNE
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Attendee(Base):
    __tablename__ = 'attendees'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    status = Column(String, default='going')  # 'going' ou 'waitlist'
    credit_used = Column(Integer, default=0)  # 1 si crédit consommé, 0 sinon
    registered_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (UniqueConstraint('user_id', 'event_id', name='unique_user_event'),)

class PasswordReset(Base):
    __tablename__ = 'password_resets'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    token = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Admin(Base):
    __tablename__ = 'admins'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)  # ← Changed to False
    admin_email = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, index=True)
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Comment(Base):
    __tablename__ = 'comments'
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey('messages.id', ondelete='CASCADE'), nullable=False)
    author_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    content = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())