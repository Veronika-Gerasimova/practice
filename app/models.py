from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'Users'
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String)
    role = Column(String)
    deleted_flag = Column(Integer, default=0)
    is_meeting_creator = Column(Integer, default=0)
    first_name = Column(Text)
    role_changed = Column(Integer, default=0)
    
    meetings = relationship("Meeting", back_populates="creator")
    reminders = relationship("Reminder", back_populates="user")
    meeting_notes = relationship("MeetingNote", back_populates="user")
    invitations = relationship("MeetingInvitation", back_populates="user")
    feedback = relationship("Feedback", back_populates="user")

class Meeting(Base):
    __tablename__ = 'Meetings'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    description = Column(String)
    created_by = Column(DateTime, default=datetime.utcnow)
    scheduled_at = Column(DateTime)
    creator_id = Column(Integer, ForeignKey('Users.id'))
    
    creator = relationship("User", back_populates="meetings")
    reminders = relationship("Reminder", back_populates="meeting")
    meeting_notes = relationship("MeetingNote", back_populates="meeting")
    invitations = relationship("MeetingInvitation", back_populates="meeting")

class Reminder(Base):
    __tablename__ = "reminders"
    reminder_id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("Meetings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("Users.id"), nullable=False)
    reminder_time = Column(DateTime, nullable=False)
    
    meeting = relationship("Meeting", back_populates="reminders")
    user = relationship("User", back_populates="reminders")

class MeetingNote(Base):
    __tablename__ = "meeting_notes"
    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("Meetings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("Users.id"), nullable=False)
    note = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    meeting = relationship("Meeting", back_populates="meeting_notes")
    user = relationship("User", back_populates="meeting_notes")

class MeetingInvitation(Base):
    __tablename__ = "MeetingInvitations"
    id = Column(Integer, primary_key=True, index=True)
    meeting_id = Column(Integer, ForeignKey("Meetings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("Users.id"), nullable=False)
    accepted = Column(String)  

    meeting = relationship("Meeting", back_populates="invitations")
    user = relationship("User", back_populates="invitations")

class Feedback(Base):
    __tablename__ = 'feedback'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('Users.id'), nullable=False) 
    message = Column(String, nullable=False)
    answered = Column(Integer, default=0)
    
    user = relationship("User", back_populates="feedback")
