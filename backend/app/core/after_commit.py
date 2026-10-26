"""Queue ephemeral UI notifications only after the owning transaction commits."""
import asyncio
import logging
from sqlalchemy import event
from sqlalchemy.orm import Session

_KEY = "adcraft_after_commit"


def after_commit(db, callback):
    session = db.sync_session
    transaction = session.get_nested_transaction() or session.get_transaction()
    db.info.setdefault(_KEY, []).append((transaction, callback))


@event.listens_for(Session, "after_commit")
def _committed(session):
    if session.in_nested_transaction():
        return
    callbacks = session.info.pop(_KEY, [])
    for _, callback in callbacks:
        async def dispatch(fn=callback):
            try:
                await fn()
            except Exception:
                logging.getLogger(__name__).exception("Committed notification dispatch failed")
        asyncio.get_running_loop().create_task(dispatch())


@event.listens_for(Session, "after_soft_rollback")
def _rolled_back(session, previous_transaction):
    def belongs_to_rollback(transaction):
        while transaction is not None:
            if transaction is previous_transaction:
                return True
            transaction = transaction.parent
        return False
    session.info[_KEY] = [(transaction, callback) for transaction, callback in session.info.get(_KEY, [])
                          if not belongs_to_rollback(transaction)]
