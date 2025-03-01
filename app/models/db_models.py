from sqlalchemy import Column, Integer, Enum, String, JSON
from sqlalchemy import VARCHAR, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import uuid
from sqlalchemy.orm import relationship
import enum


class User(Base):
    __tablename__ = "users"
    user_id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        index=True,
        default=uuid.uuid4,
    )
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(VARCHAR, unique=True, nullable=False)
    password = Column(VARCHAR, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_id"),)


class JobDetails(Base):
    __tablename__ = "job_details"

    id = Column(
        UUID(as_uuid=True), primary_key=True, nullable=False, default=uuid.uuid4
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    role = Column(String, nullable=False)
    industry = Column(String, nullable=False)
    company = Column(String, nullable=False)
    experience_level = Column(String, nullable=False)
    description = Column(Text, nullable=False)  
    interview_type = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )



class PortfolioStatus(enum.Enum):
    PENDING = "Pending"
    ANALYZED = "Analyzed"
    FAILED = "Failed"


class UserPortfolio(Base):
    __tablename__ = "user_portfolios"

    id = Column(
        UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4
        )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), 
                     unique=True, nullable=False)
    linkedin_url = Column(String, nullable=True)
    github_url = Column(String, nullable=True)
    linkedin_data = Column(JSON, nullable=True)
    github_data = Column(JSON, nullable=True)
    upload_date = Column(DateTime, server_default=func.now(), nullable=False)
    status = Column(Enum(PortfolioStatus), default=PortfolioStatus.PENDING, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationship to the User model (if you have a User model defined)
    #user = relationship("User", back_populates="portfolios")

class Resume(Base):
    __tablename__ = "resumes"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        index=True,
        nullable=False,
        default=uuid.uuid4,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    parsed_sections = Column(JSON)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ResumeKeySections(Base):
    __tablename__ = "resume_key_sections"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        index=True,
        default=uuid.uuid4,
    )
    resume_id = Column(
        UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False
    )
    job_id = Column(
        UUID(as_uuid=True),
        ForeignKey("job_details.id", ondelete="CASCADE"),
        nullable=False,
    )
    job_role = Column(String, nullable=False)
    key_sections = Column(JSON)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        index=True,
        default=uuid.uuid4,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    job_role = Column(String, nullable=False)
    status = Column(
        Enum("active", "completed", name="session_status"), default="active"
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class Question(Base):
    __tablename__ = "questions"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        index=True,
        default=uuid.uuid4,
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_text = Column(Text, nullable=False)
    model_answer = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class Answer(Base):
    __tablename__ = "answers"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        index=True,
        default=uuid.uuid4,
    )
    session_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id = Column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_answer = Column(Text, nullable=False)
    score = Column(Integer, nullable=False)
    feedback = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
