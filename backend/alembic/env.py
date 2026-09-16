import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

import sys
import os

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import Base, db_url

# Import all models here to ensure they are registered with Base.metadata
from app.models.user import User
from app.models.academic_profile import AcademicProfile
from app.models.subject import Subject
from app.models.attendance import AttendanceRecord
from app.models.study_plan import StudyPlan, StudyBlock
from app.models.note import Note
from app.models.document import Document
from app.models.tutor import TutorSession, SessionAsset, AcademicMemory, ConceptNode
from app.models.connect import UserConnection, ConnectGroup, GroupMember, ConnectMessage, CollaborativeNoteState, AcademicReputationLog
from app.models.timetable import TimetableEvent, Assignment
from app.models.course import Course, Chapter, Section
from app.models.ai_tracking import AIRequest, AIUsage, AICache
from app.models.knowledge_graph import KnowledgeNode, KnowledgeEdge
from app.models.document_chunk import DocumentChunk
from app.models.conversation import Conversation, Message, ConversationSummary
from app.models.audit_log import AdminAuditLog
from app.models.resource_share import ResourceShare

target_metadata = Base.metadata

# Override sqlalchemy.url with our application's url (escaping % for configparser)
safe_url = db_url.replace("%", "%%")
config.set_main_option("sqlalchemy.url", safe_url)


# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    from app.core.database import engine

    connectable = engine

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
