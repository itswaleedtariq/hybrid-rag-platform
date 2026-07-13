from datetime import datetime, timezone
from uuid import uuid4
from sqlmodel import Field, SQLModel

def now(): return datetime.now(timezone.utc)

class User(SQLModel, table=True):
    id: str = Field(default_factory=lambda:str(uuid4()), primary_key=True)
    email: str = Field(index=True, unique=True, max_length=320)
    full_name: str = Field(max_length=120)
    hashed_password: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=now)

class DocumentRecord(SQLModel, table=True):
    id: str = Field(default_factory=lambda:str(uuid4()), primary_key=True)
    user_id: str = Field(index=True, foreign_key='user.id')
    original_name: str
    stored_name: str
    file_type: str
    size_bytes: int
    sha256: str = Field(index=True)
    status: str = Field(default='processing', index=True)
    chunking_strategy: str = 'recursive'
    chunk_count: int = 0
    error_message: str|None = None
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)

class ChunkRecord(SQLModel, table=True):
    id: str = Field(primary_key=True)
    user_id: str = Field(index=True, foreign_key='user.id')
    document_id: str = Field(index=True, foreign_key='documentrecord.id')
    text: str
    page_number: int|None = None
    section_heading: str|None = None
    chunk_index: int
    character_count: int
    strategy: str
    created_at: datetime = Field(default_factory=now)

class Conversation(SQLModel, table=True):
    id: str = Field(default_factory=lambda:str(uuid4()), primary_key=True)
    user_id: str = Field(index=True, foreign_key='user.id')
    title: str = 'New conversation'
    created_at: datetime = Field(default_factory=now)
    updated_at: datetime = Field(default_factory=now)

class Message(SQLModel, table=True):
    id: str = Field(default_factory=lambda:str(uuid4()), primary_key=True)
    conversation_id: str = Field(index=True, foreign_key='conversation.id')
    user_id: str = Field(index=True, foreign_key='user.id')
    role: str
    content: str
    sources_json: str|None = None
    confidence: float|None = None
    created_at: datetime = Field(default_factory=now)
