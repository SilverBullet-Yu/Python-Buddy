from coze_coding_dev_sdk.database import Base

from typing import Optional
import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Double, ForeignKey, Index, Integer, Numeric, PrimaryKeyConstraint, String, Table, Text, func, text
from sqlalchemy.dialects.postgresql import OID
from sqlalchemy.orm import Mapped, mapped_column

class HealthCheck(Base):
    __tablename__ = 'health_check'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='health_check_pkey'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(True), server_default=text('now()'))


t_pg_stat_statements = Table(
    'pg_stat_statements', Base.metadata,
    Column('userid', OID),
    Column('dbid', OID),
    Column('toplevel', Boolean),
    Column('queryid', BigInteger),
    Column('query', Text),
    Column('plans', BigInteger),
    Column('total_plan_time', Double(53)),
    Column('min_plan_time', Double(53)),
    Column('max_plan_time', Double(53)),
    Column('mean_plan_time', Double(53)),
    Column('stddev_plan_time', Double(53)),
    Column('calls', BigInteger),
    Column('total_exec_time', Double(53)),
    Column('min_exec_time', Double(53)),
    Column('max_exec_time', Double(53)),
    Column('mean_exec_time', Double(53)),
    Column('stddev_exec_time', Double(53)),
    Column('rows', BigInteger),
    Column('shared_blks_hit', BigInteger),
    Column('shared_blks_read', BigInteger),
    Column('shared_blks_dirtied', BigInteger),
    Column('shared_blks_written', BigInteger),
    Column('local_blks_hit', BigInteger),
    Column('local_blks_read', BigInteger),
    Column('local_blks_dirtied', BigInteger),
    Column('local_blks_written', BigInteger),
    Column('temp_blks_read', BigInteger),
    Column('temp_blks_written', BigInteger),
    Column('shared_blk_read_time', Double(53)),
    Column('shared_blk_write_time', Double(53)),
    Column('local_blk_read_time', Double(53)),
    Column('local_blk_write_time', Double(53)),
    Column('temp_blk_read_time', Double(53)),
    Column('temp_blk_write_time', Double(53)),
    Column('wal_records', BigInteger),
    Column('wal_fpi', BigInteger),
    Column('wal_bytes', Numeric),
    Column('jit_functions', BigInteger),
    Column('jit_generation_time', Double(53)),
    Column('jit_inlining_count', BigInteger),
    Column('jit_inlining_time', Double(53)),
    Column('jit_optimization_count', BigInteger),
    Column('jit_optimization_time', Double(53)),
    Column('jit_emission_count', BigInteger),
    Column('jit_emission_time', Double(53)),
    Column('jit_deform_count', BigInteger),
    Column('jit_deform_time', Double(53)),
    Column('stats_since', DateTime(True)),
    Column('minmax_stats_since', DateTime(True))
)


t_pg_stat_statements_info = Table(
    'pg_stat_statements_info', Base.metadata,
    Column('dealloc', BigInteger),
    Column('stats_reset', DateTime(True))
)


class StudentProgress(Base):
    """学生学习进度表：记录每个学生对各知识点的掌握程度"""
    __tablename__ = 'student_progress'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="学生标识")
    topic: Mapped[str] = mapped_column(String(128), nullable=False, comment="知识点名称，如 variables, data_types, control_flow, functions")
    mastery_level: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'), comment="掌握程度 0-100")
    exercises_completed: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'), comment="已完成练习数")
    exercises_correct: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text('0'), comment="正确练习数")
    last_practiced_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment="最近练习时间")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    __table_args__ = (
        Index("ix_student_progress_student_id", "student_id"),
        Index("ix_student_progress_topic", "topic"),
        Index("ix_student_progress_student_topic", "student_id", "topic"),
    )


class ExerciseRecord(Base):
    """练习记录表：记录学生每次练习的详细信息"""
    __tablename__ = 'exercise_records'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="学生标识")
    topic: Mapped[str] = mapped_column(String(128), nullable=False, comment="知识点名称")
    question: Mapped[str] = mapped_column(Text, nullable=False, comment="题目内容")
    student_code: Mapped[str] = mapped_column(Text, nullable=False, comment="学生提交的代码")
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, comment="是否正确")
    error_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息")
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="反馈建议")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_exercise_records_student_id", "student_id"),
        Index("ix_exercise_records_topic", "topic"),
        Index("ix_exercise_records_created_at", "created_at"),
    )


class Conversation(Base):
    """对话历史表：持久化学生与 AI 的对话记录"""
    __tablename__ = 'conversations'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="学生标识")
    role: Mapped[str] = mapped_column(String(16), nullable=False, comment="角色：user 或 assistant")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_conversations_student_id", "student_id"),
        Index("ix_conversations_student_created", "student_id", "created_at"),
    )
