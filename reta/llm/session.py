"""
RETA Session — adaptateur session DB (sync et async).

On reçoit la session de l'extérieur (SQLAlchemy, peewee, databases, tortoise…).
On ne crée pas de DB — on expose des méthodes RETA sur la session existante.

Contrat minimal attendu de la session :
  Sync  : session.execute(query, params) → rows
          session.commit()
  Async : await session.execute(query, params) → rows
          await session.commit()

Les méthodes save/load sérialisent ConversationMemory en JSON
et écrivent dans une table `reta_memory` que l'app doit créer.

DDL minimal (à créer côté app) :
  CREATE TABLE reta_memory (
    session_id  TEXT PRIMARY KEY,
    payload     TEXT NOT NULL,     -- JSON de ConversationMemory
    updated_at  TEXT NOT NULL
  );
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from .memory import ConversationMemory


_TABLE = "reta_memory"


class RETASession:
    """Adaptateur sync. Compatible SQLAlchemy Core, sqlite3, peewee raw, etc."""

    def __init__(self, session):
        self.session = session

    def save(self, memory: ConversationMemory) -> None:
        payload    = json.dumps(memory.encode())
        updated_at = datetime.now(timezone.utc).isoformat()
        self.session.execute(
            f"INSERT INTO {_TABLE} (session_id, payload, updated_at) VALUES (?, ?, ?)"
            f" ON CONFLICT(session_id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at",
            (memory.session_id, payload, updated_at),
        )
        self.session.commit()

    def load(self, session_id: str) -> ConversationMemory | None:
        row = self.session.execute(
            f"SELECT payload FROM {_TABLE} WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        return ConversationMemory.from_dict(json.loads(row[0]))

    def load_all(self) -> list[ConversationMemory]:
        rows = self.session.execute(
            f"SELECT payload FROM {_TABLE} ORDER BY updated_at"
        ).fetchall()
        return [ConversationMemory.from_dict(json.loads(r[0])) for r in rows]

    def delete(self, session_id: str) -> None:
        self.session.execute(
            f"DELETE FROM {_TABLE} WHERE session_id = ?", (session_id,)
        )
        self.session.commit()


class RETASessionAsync:
    """Adaptateur async. Compatible SQLAlchemy async, databases, tortoise, etc."""

    def __init__(self, session):
        self.session = session

    async def save(self, memory: ConversationMemory) -> None:
        payload    = json.dumps(memory.encode())
        updated_at = datetime.now(timezone.utc).isoformat()
        await self.session.execute(
            f"INSERT INTO {_TABLE} (session_id, payload, updated_at) VALUES (:sid, :p, :ts)"
            f" ON CONFLICT(session_id) DO UPDATE SET payload=excluded.payload, updated_at=excluded.updated_at",
            {"sid": memory.session_id, "p": payload, "ts": updated_at},
        )
        await self.session.commit()

    async def load(self, session_id: str) -> ConversationMemory | None:
        row = await self.session.execute(
            f"SELECT payload FROM {_TABLE} WHERE session_id = :sid",
            {"sid": session_id},
        )
        result = row.fetchone() if hasattr(row, "fetchone") else await row.fetchone()
        if result is None:
            return None
        return ConversationMemory.from_dict(json.loads(result[0]))

    async def load_all(self) -> list[ConversationMemory]:
        rows = await self.session.execute(
            f"SELECT payload FROM {_TABLE} ORDER BY updated_at"
        )
        all_rows = rows.fetchall() if hasattr(rows, "fetchall") else await rows.fetchall()
        return [ConversationMemory.from_dict(json.loads(r[0])) for r in all_rows]

    async def delete(self, session_id: str) -> None:
        await self.session.execute(
            f"DELETE FROM {_TABLE} WHERE session_id = :sid", {"sid": session_id}
        )
        await self.session.commit()
