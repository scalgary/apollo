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

class MembershipPeriod(Base):
    __tablename__ = 'membership_periods'
    
    id = Column(Integer, primary_key=True, index=True)
    period_name = Column(String, unique=True, nullable=False)  # 'Fall 2025'
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EventTypePeriodConfig(Base):
    __tablename__ = 'event_type_period_configs'
    
    id = Column(Integer, primary_key=True, index=True)
    event_type_name = Column(String, nullable=False)  # 'open_play' ou 'competitive'
    period_id = Column(Integer, ForeignKey('membership_periods.id'), nullable=False)
    display_name = Column(String, nullable=False)  # 'Thursday Indoor'
    location = Column(String, nullable=False)
    time_start = Column(String, nullable=False)  # '19:00'
    time_end = Column(String, nullable=False)  # '21:00'
    max_capacity = Column(Integer, nullable=False)
    color = Column(String, nullable=False)  # '#3b82f6'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (UniqueConstraint('event_type_name', 'period_id', name='unique_event_type_period'),)

class UserEventTypeMembership(Base):
    __tablename__ = 'user_event_type_memberships'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    event_type_name = Column(String, nullable=False)  # 'open_play' ou 'competitive'
    period_id = Column(Integer, ForeignKey('membership_periods.id'), nullable=False)
    membership_type = Column(String, nullable=False)
    total_credits_purchased = Column(Integer, nullable=True)
    remaining_credits = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (UniqueConstraint('user_id', 'event_type_name', 'period_id', name='unique_user_event_type_period'),)

class Event(Base):
    __tablename__ = 'events'
    
    id = Column(Integer, primary_key=True, index=True)
    event_type_name = Column(String, nullable=False)  # 'open_play' ou 'competitive'
    date = Column(Date, nullable=False, unique=True)
    confirmed_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Attendee(Base):
    __tablename__ = 'attendees'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    event_id = Column(Integer, ForeignKey('events.id'), nullable=False)
    status = Column(String, default='going')  # 'going' ou 'waitlist'
    credit_used = Column(Integer, default=0)  # 1 si credit consomme, 0 sinon
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
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=True)
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