from sqlalchemy import Column, Integer, String, Text, Float, Date, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
from app.models.user import User

class State(Base):
    __tablename__ = "states"
    
    state_id = Column(Integer, primary_key=True, index=True)
    state_name = Column(String(50), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    tasks = relationship("Task", back_populates="status")
    task_stages = relationship("TaskStage", back_populates="status")


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        UniqueConstraint('name', 'assigned_user_id', name='_name_assigned_user_uc'),
    )

    task_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    status_state_id = Column(Integer, ForeignKey("states.state_id"), nullable=False)
    due_date = Column(Date, nullable=False)
    completed_date = Column(Date, nullable=True)
    priority = Column(String(20), nullable=False)  # high/medium/low
    assigned_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    idempotency_key = Column(String(36), unique=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_deleted = Column(Boolean, default=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    status = relationship("State", back_populates="tasks", foreign_keys=[status_state_id])
    assigned_user = relationship("User", back_populates="tasks", foreign_keys=[assigned_user_id])
    creator = relationship("User", back_populates="created_tasks", foreign_keys=[created_by_id])
    stages = relationship("TaskStage", back_populates="task", cascade="all, delete-orphan", foreign_keys="[TaskStage.task_id]")


class TaskStage(Base):
    __tablename__ = "task_stages"

    stage_id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.task_id", ondelete="CASCADE"), nullable=False)
    stage_name = Column(String(100), nullable=False)
    estimated_time_hours = Column(Float, nullable=False)
    actual_time_hours = Column(Float, nullable=True)
    status_state_id = Column(Integer, ForeignKey("states.state_id"), nullable=False)
    order_number = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=True)
    completed_date = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    task = relationship("Task", back_populates="stages", foreign_keys=[task_id])
    status = relationship("State", back_populates="task_stages", foreign_keys=[status_state_id])


class TaskTemplate(Base):
    __tablename__ = "task_templates"

    template_id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    stages = relationship("TaskTemplateStage", back_populates="template", cascade="all, delete-orphan")


class TaskTemplateStage(Base):
    __tablename__ = "task_template_stages"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("task_templates.template_id", ondelete="CASCADE"), nullable=False)
    stage_name = Column(String(100), nullable=False)
    estimated_time_hours = Column(Float, nullable=True)  # optional default
    order_number = Column(Integer, nullable=False)

    template = relationship("TaskTemplate", back_populates="stages", foreign_keys=[template_id])


class ArchivedTask(Base):
    __tablename__ = "archived_tasks"

    task_id = Column(Integer, primary_key=True)
    name = Column(String(100))
    description = Column(Text)
    status_state_id = Column(Integer)
    due_date = Column(Date)
    completed_date = Column(Date)
    priority = Column(String(20))
    assigned_user_id = Column(Integer)
    created_by_id = Column(Integer)
    idempotency_key = Column(String(36))
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    archived_at = Column(DateTime(timezone=True), server_default=func.now())


class ArchivedTaskStage(Base):
    __tablename__ = "archived_task_stages"

    stage_id = Column(Integer, primary_key=True)
    task_id = Column(Integer)
    stage_name = Column(String(100))
    estimated_time_hours = Column(Float)
    actual_time_hours = Column(Float)
    status_state_id = Column(Integer)
    order_number = Column(Integer)
    start_date = Column(Date)
    completed_date = Column(Date)
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    archived_at = Column(DateTime(timezone=True), server_default=func.now())