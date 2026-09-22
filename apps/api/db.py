import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Integer, BigInteger, Boolean, create_engine, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .deployment import database_url

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


class UserPrivacy(Base):
    __tablename__ = 'user_privacy'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), primary_key=True)
    research_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    notice_version: Mapped[str | None] = mapped_column(String, nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AnswerPreferences(Base):
    __tablename__ = 'answer_preferences'
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), primary_key=True)
    answer_style: Mapped[str] = mapped_column(String, default='concise')


class DeletionRequest(Base):
    __tablename__ = 'deletion_requests'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    status: Mapped[str] = mapped_column(String, default='pending')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Session(Base):
    __tablename__ = 'sessions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'))
    problem_domain: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default='open')
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConversationMetadata(Base):
    __tablename__ = 'conversation_metadata'
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'), primary_key=True)
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)


class ConversationState(Base):
    __tablename__ = 'conversation_state'
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'), primary_key=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)


class ConversationDeletion(Base):
    __tablename__ = 'conversation_deletions'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    session_id: Mapped[str] = mapped_column(String(36), unique=True)
    status: Mapped[str] = mapped_column(String, default='pending')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ResponseDraft(Base):
    __tablename__ = 'response_drafts'
    request_id: Mapped[str] = mapped_column(ForeignKey('events.id'), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey('sessions.id'), index=True)
    text: Mapped[str] = mapped_column(String, default='')
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False)


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


url = database_url(os.getenv('DATABASE_URL', 'postgresql+psycopg://thinkfirst:thinkfirst@localhost:55432/thinkfirst'))
engine = create_engine(url, pool_pre_ping=True, hide_parameters=True, connect_args={'check_same_thread': False} if url.get_backend_name() == 'sqlite' else {'connect_timeout': 5})
SessionLocal = sessionmaker(engine, expire_on_commit=False)


@event.listens_for(Event, 'before_update')
@event.listens_for(Event, 'before_delete')
def immutable(*args):
    raise ValueError('Events are append-only; insert a corrective event.')


def migrate(target=engine):
    with target.begin() as conn:
        if target.dialect.name == 'postgresql':
            conn.exec_driver_sql('SELECT pg_advisory_xact_lock(74684601)')
        Base.metadata.create_all(conn)
        conn.exec_driver_sql('INSERT INTO ai_budget_lock (id) VALUES (1) ON CONFLICT (id) DO NOTHING')
        if target.dialect.name == 'postgresql':
            conn.exec_driver_sql("""CREATE OR REPLACE FUNCTION prevent_event_mutation() RETURNS trigger AS $$
            BEGIN RAISE EXCEPTION 'events are append-only'; END; $$ LANGUAGE plpgsql""")
            conn.exec_driver_sql('DROP TRIGGER IF EXISTS immutable_events ON events')
            conn.exec_driver_sql('CREATE TRIGGER immutable_events BEFORE UPDATE OR DELETE ON events FOR EACH ROW EXECUTE FUNCTION prevent_event_mutation()')
        elif target.dialect.name == 'sqlite':
            for op in ('UPDATE', 'DELETE'):
                conn.exec_driver_sql(f"CREATE TRIGGER IF NOT EXISTS immutable_events_{op} BEFORE {op} ON events BEGIN SELECT RAISE(ABORT, 'events are append-only'); END")


def verify_schema(target=engine):
    from sqlalchemy import inspect
    with target.connect() as conn:
        inspector = inspect(conn)
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name) or not set(table.columns.keys()).issubset({c['name'] for c in inspector.get_columns(table.name)}):
                raise RuntimeError('Database schema is not ready. Run python -m apps.api.migrate with the migration role before starting the API.')
        if conn.exec_driver_sql('SELECT count(*) FROM ai_budget_lock WHERE id=1').scalar() != 1:
            raise RuntimeError('AI admission lock is missing; run the migration command.')
        if target.dialect.name == 'postgresql':
            active = conn.exec_driver_sql("SELECT count(*) FROM pg_trigger WHERE tgrelid='events'::regclass AND tgname='immutable_events' AND tgenabled IN ('O','A')").scalar()
            if active != 1:
                raise RuntimeError('Immutable event protection is missing; run the migration command.')


if __name__ == '__main__':
    migrate()
