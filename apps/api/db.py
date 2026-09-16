import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Integer, BigInteger, Boolean, create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

load_dotenv()


def now():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    subject: Mapped[str] = mapped_column(String, unique=True)
    display_name: Mapped[str] = mapped_column(String, default='Research participant')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class UserPreferences(Base):
    __tablename__ = 'user_preferences'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), primary_key=True)
    practice_reminders: Mapped[bool] = mapped_column(Boolean, default=True)


class Session(Base):
    __tablename__ = 'sessions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    problem_domain: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default='open')
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Event(Base):
    __tablename__ = 'events'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'))
    event_type: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, 'postgresql'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    __table_args__ = (Index('idx_events_session', 'session_id', 'created_at'),
                      Index('idx_events_user_type', 'user_id', 'event_type', 'created_at'))


class Rollup(Base):
    __tablename__ = 'user_behavior_rollup'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), primary_key=True)
    data: Mapped[dict] = mapped_column(JSON)
    refreshed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ResearchExport(Base):
    __tablename__ = 'research_exports'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    data: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AIBudgetLock(Base):
    __tablename__ = 'ai_budget_lock'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)


class AIUsageRequest(Base):
    """Mutable accounting, separate from the append-only behavioral events."""
    __tablename__ = 'ai_usage_requests'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, index=True)
    status: Mapped[str] = mapped_column(String, default='pending')
    attempt_budget: Mapped[int] = mapped_column(Integer)
    max_attempts: Mapped[int] = mapped_column(Integer)
    accounted_tokens: Mapped[int] = mapped_column(BigInteger)
    accounted_micro_usd: Mapped[int] = mapped_column(BigInteger)
    rate_micro_usd_per_million: Mapped[int] = mapped_column(BigInteger)
    attempts: Mapped[list] = mapped_column(JSON, default=list)


url = os.getenv('DATABASE_URL', 'postgresql+psycopg://thinkfirst:thinkfirst@localhost:55432/thinkfirst')
engine = create_engine(url, pool_pre_ping=True, connect_args={'check_same_thread': False} if url.startswith('sqlite') else {'connect_timeout': 5})
SessionLocal = sessionmaker(engine, expire_on_commit=False)


@event.listens_for(Event, 'before_update')
@event.listens_for(Event, 'before_delete')
def immutable(*args):
    raise ValueError('Events are append-only; insert a corrective event.')


def migrate():
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql('INSERT INTO ai_budget_lock (id) VALUES (1) ON CONFLICT (id) DO NOTHING')
        if engine.dialect.name == 'postgresql':
            conn.exec_driver_sql("""CREATE OR REPLACE FUNCTION prevent_event_mutation() RETURNS trigger AS $$
            BEGIN RAISE EXCEPTION 'events are append-only'; END; $$ LANGUAGE plpgsql""")
            conn.exec_driver_sql('DROP TRIGGER IF EXISTS immutable_events ON events')
            conn.exec_driver_sql('CREATE TRIGGER immutable_events BEFORE UPDATE OR DELETE ON events FOR EACH ROW EXECUTE FUNCTION prevent_event_mutation()')
        elif engine.dialect.name == 'sqlite':
            for op in ('UPDATE', 'DELETE'):
                conn.exec_driver_sql(f"CREATE TRIGGER IF NOT EXISTS immutable_events_{op} BEFORE {op} ON events BEGIN SELECT RAISE(ABORT, 'events are append-only'); END")


if __name__ == '__main__':
    migrate()
