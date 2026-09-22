"""Offline operator-only conversation erasure; never invoked by an HTTP route.

python -m apps.api.erase --request-id UUID --user-id UUID --api-stopped
Run with the database owner role while every API replica is stopped.
"""
import argparse
from datetime import timedelta
from uuid import UUID
from sqlalchemy import select, delete, update
from .db import engine, DeletionRequest, ConversationDeletion, ResponseDraft, ConversationState, UserPrivacy, Event, Session, ConversationMetadata, Rollup, AIUsageRequest, now


def fulfill(connection, request_id, user_id):
    """Caller owns the transaction. Any failure must roll back the whole operation."""
    request = connection.execute(select(DeletionRequest.__table__).where(
        DeletionRequest.id == request_id, DeletionRequest.user_id == user_id).with_for_update()).mappings().first()
    request_table = DeletionRequest
    if not request:
        request_table = ConversationDeletion
        request = connection.execute(select(ConversationDeletion.__table__).where(ConversationDeletion.id==request_id,ConversationDeletion.user_id==user_id).with_for_update()).mappings().first()
    if not request:
        raise ValueError('No deletion request matches both IDs.')
    if request['status'] == 'completed':
        return False
    active = connection.execute(select(AIUsageRequest.id).where(AIUsageRequest.user_id == user_id,
        AIUsageRequest.status == 'pending', AIUsageRequest.created_at > now() - timedelta(minutes=3))).first()
    if active:
        raise ValueError('A recent AI request is still pending. Stop the API and wait at least three minutes.')
    # This DML also starts a real SQLite transaction before transactional trigger DDL.
    connection.execute(update(request_table).where(request_table.id == request_id).values(status='completed', completed_at=now()))
    if request_table is DeletionRequest:
        connection.execute(update(UserPrivacy).where(UserPrivacy.user_id == user_id).values(research_opt_in=False, updated_at=now()))
        connection.execute(update(ConversationDeletion).where(ConversationDeletion.user_id==user_id,ConversationDeletion.status=='pending').values(status='completed',completed_at=now()))
    session_ids = select(Session.id).where(Session.user_id == user_id)
    if request_table is ConversationDeletion:
        session_ids = session_ids.where(Session.id==request['session_id'])
    connection.execute(delete(ResponseDraft).where(ResponseDraft.session_id.in_(session_ids)))
    connection.execute(delete(ConversationState).where(ConversationState.session_id.in_(session_ids)))
    connection.execute(delete(ConversationMetadata).where(ConversationMetadata.session_id.in_(session_ids)))
    if connection.dialect.name == 'postgresql':
        # ALTER holds the table lock until commit; no other writer can use this window.
        connection.exec_driver_sql('ALTER TABLE events DISABLE TRIGGER immutable_events')
    elif connection.dialect.name == 'sqlite':
        connection.exec_driver_sql('DROP TRIGGER immutable_events_DELETE')
    else:
        raise ValueError('Unsupported database for controlled erasure.')
    connection.execute(delete(Event.__table__).where(Event.session_id.in_(session_ids)))
    if connection.dialect.name == 'postgresql':
        connection.exec_driver_sql('ALTER TABLE events ENABLE TRIGGER immutable_events')
    else:
        connection.exec_driver_sql("CREATE TRIGGER immutable_events_DELETE BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT, 'events are append-only'); END")
    connection.execute(delete(Rollup).where(Rollup.user_id == user_id))
    connection.execute(delete(Session).where(Session.id.in_(session_ids)))
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request-id', type=UUID, required=True)
    parser.add_argument('--user-id', type=UUID, required=True)
    parser.add_argument('--api-stopped', action='store_true', help='Confirm all API replicas are stopped.')
    args = parser.parse_args()
    if not args.api_stopped:
        parser.error('Stop all API replicas, then explicitly pass --api-stopped.')
    with engine.begin() as connection:
        changed = fulfill(connection, str(args.request_id), str(args.user_id))
    print('Conversation deletion completed.' if changed else 'This request was already completed; no data changed.')


if __name__ == '__main__':
    main()
