from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated
from uuid import uuid4
import hashlib, json, re

from fastapi import Depends, FastAPI, File, Form, HTTPException, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, func, select

from app.config import settings
from app.database import create_db_and_tables, get_session
from app.models import ChunkRecord, Conversation, DocumentRecord, Message, User
from app.rag import ingest, package_answer, remove_document, retrieve
from app.schemas import AskIn, AskOut, AuthOut, ConversationDetail, ConversationOut, DocumentOut, LoginIn, MessageOut, RegisterIn, SourceOut, StatsOut, UserOut
from app.security import DUMMY_HASH, create_token, decode_token, hash_password, verify_password

SessionDep=Annotated[Session,Depends(get_session)]
oauth=OAuth2PasswordBearer(tokenUrl='/api/auth/login')

def current_user(token:Annotated[str,Depends(oauth)],session:SessionDep):
    try: uid=decode_token(token)
    except ValueError: raise HTTPException(401,'Invalid or expired token',headers={'WWW-Authenticate':'Bearer'})
    user=session.get(User,uid)
    if not user or not user.is_active: raise HTTPException(401,'User not found')
    return user
UserDep=Annotated[User,Depends(current_user)]

@asynccontextmanager
async def lifespan(app):
    settings.prepare(); create_db_and_tables(); yield

app=FastAPI(title=settings.app_name,version='1.0.0',description='Multi-user hybrid RAG with dense search, BM25, RRF, reranking, Groq and citations.',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=settings.origins,allow_credentials=True,allow_methods=['*'],allow_headers=['*'])

@app.get('/')
def root(): return {'message':settings.app_name,'docs':'/docs'}
@app.get('/api/health')
def health(): return {'status':'ok','app':settings.app_name,'groq_configured':bool(settings.groq_api_key),'reranker_enabled':settings.enable_reranker}

@app.post('/api/auth/register',response_model=AuthOut,status_code=201)
def register(data:RegisterIn,session:SessionDep):
    email=data.email.lower().strip()
    if session.exec(select(User).where(User.email==email)).first(): raise HTTPException(409,'Email already registered')
    user=User(email=email,full_name=data.full_name.strip(),hashed_password=hash_password(data.password)); session.add(user); session.commit(); session.refresh(user)
    return AuthOut(access_token=create_token(user.id),user=UserOut.model_validate(user))

@app.post('/api/auth/login',response_model=AuthOut)
def login(data:LoginIn,session:SessionDep):
    user=session.exec(select(User).where(User.email==data.email.lower().strip())).first()
    if not user:
        verify_password(data.password,DUMMY_HASH); raise HTTPException(401,'Incorrect email or password')
    if not verify_password(data.password,user.hashed_password): raise HTTPException(401,'Incorrect email or password')
    return AuthOut(access_token=create_token(user.id),user=UserOut.model_validate(user))

@app.get('/api/auth/me',response_model=UserOut)
def me(user:UserDep): return user

def safe_name(name): return re.sub(r'[^A-Za-z0-9._-]+','_',Path(name).name)[:180] or 'document'
def owned_doc(session,id,uid):
    d=session.get(DocumentRecord,id)
    if not d or d.user_id!=uid: raise HTTPException(404,'Document not found')
    return d

def owned_conversation(session,id,uid):
    c=session.get(Conversation,id)
    if not c or c.user_id!=uid: raise HTTPException(404,'Conversation not found')
    return c

@app.get('/api/documents',response_model=list[DocumentOut])
def documents(session:SessionDep,user:UserDep):
    return session.exec(select(DocumentRecord).where(DocumentRecord.user_id==user.id).order_by(DocumentRecord.created_at.desc())).all()

@app.post('/api/documents/upload',response_model=DocumentOut,status_code=201)
async def upload(session:SessionDep,user:UserDep,file:UploadFile=File(...),chunking_strategy:str=Form('recursive')):
    if chunking_strategy not in {'fixed','recursive','semantic'}: raise HTTPException(422,'Use fixed, recursive, or semantic chunking')
    name=safe_name(file.filename or 'document'); ext=Path(name).suffix.lower(); allowed={'.pdf','.docx','.txt','.md','.html','.htm'}
    if ext not in allowed: raise HTTPException(415,f'Unsupported type. Allowed: {sorted(allowed)}')
    data=await file.read(settings.max_upload_bytes+1)
    if not data: raise HTTPException(422,'File is empty')
    if len(data)>settings.max_upload_bytes: raise HTTPException(413,f'File exceeds {settings.max_upload_mb} MB')
    digest=hashlib.sha256(data).hexdigest()
    duplicate=session.exec(select(DocumentRecord).where(DocumentRecord.user_id==user.id,DocumentRecord.sha256==digest,DocumentRecord.status!='failed')).first()
    if duplicate: raise HTTPException(409,f'Already indexed as {duplicate.original_name}')
    folder=settings.upload_path/user.id; folder.mkdir(parents=True,exist_ok=True); stored=f'{uuid4()}{ext}'; path=folder/stored; path.write_bytes(data)
    doc=DocumentRecord(user_id=user.id,original_name=name,stored_name=stored,file_type=ext[1:],size_bytes=len(data),sha256=digest,chunking_strategy=chunking_strategy)
    session.add(doc); session.commit(); session.refresh(doc)
    try: return ingest(session,doc,path,chunking_strategy)
    except Exception as e: raise HTTPException(422,f'Indexing failed: {e}')

@app.post('/api/documents/{document_id}/reindex',response_model=DocumentOut)
def reindex(document_id:str,session:SessionDep,user:UserDep,chunking_strategy:str|None=None):
    doc=owned_doc(session,document_id,user.id); strategy=chunking_strategy or doc.chunking_strategy
    if strategy not in {'fixed','recursive','semantic'}: raise HTTPException(422,'Use fixed, recursive, or semantic')
    path=settings.upload_path/user.id/doc.stored_name
    if not path.exists(): raise HTTPException(404,'Stored file is missing')
    remove_document(session,doc.id); doc.status='processing'; doc.error_message=None; doc.chunk_count=0; doc.updated_at=datetime.now(timezone.utc); session.add(doc); session.commit()
    try: return ingest(session,doc,path,strategy)
    except Exception as e: raise HTTPException(422,f'Re-indexing failed: {e}')

@app.delete('/api/documents/{document_id}',status_code=204)
def delete_document(document_id:str,session:SessionDep,user:UserDep):
    doc=owned_doc(session,document_id,user.id); remove_document(session,doc.id); path=settings.upload_path/user.id/doc.stored_name
    if path.exists(): path.unlink()
    session.delete(doc); session.commit(); return Response(status_code=204)

@app.post('/api/chat/ask',response_model=AskOut)
def ask(data:AskIn,session:SessionDep,user:UserDep):
    if data.conversation_id: conv=owned_conversation(session,data.conversation_id,user.id)
    else:
        conv=Conversation(user_id=user.id,title=' '.join(data.question.split())[:100]); session.add(conv); session.commit(); session.refresh(conv)
    hits=retrieve(session,data.question,user.id,data.retrieval_mode,data.top_k)
    try: answer,sources,confidence,insufficient,debug=package_answer(data.question,hits)
    except RuntimeError as e: raise HTTPException(503,str(e))
    session.add(Message(conversation_id=conv.id,user_id=user.id,role='user',content=data.question))
    session.add(Message(conversation_id=conv.id,user_id=user.id,role='assistant',content=answer,sources_json=json.dumps(sources),confidence=confidence['composite']))
    conv.updated_at=datetime.now(timezone.utc); session.add(conv); session.commit()
    return {'conversation_id':conv.id,'answer':answer,'sources':sources,'confidence':confidence,'retrieval_mode':data.retrieval_mode,'model':settings.groq_model,'insufficient_context':insufficient,'retrieved_chunks':debug}

@app.get('/api/chat/conversations',response_model=list[ConversationOut])
def conversations(session:SessionDep,user:UserDep):
    return session.exec(select(Conversation).where(Conversation.user_id==user.id).order_by(Conversation.updated_at.desc())).all()

@app.get('/api/chat/conversations/{conversation_id}',response_model=ConversationDetail)
def conversation(conversation_id:str,session:SessionDep,user:UserDep):
    conv=owned_conversation(session,conversation_id,user.id); rows=session.exec(select(Message).where(Message.conversation_id==conv.id,Message.user_id==user.id).order_by(Message.created_at)).all(); messages=[]
    for m in rows:
        src=[SourceOut(**x) for x in json.loads(m.sources_json)] if m.sources_json else []
        messages.append(MessageOut(id=m.id,role=m.role,content=m.content,sources=src,confidence=m.confidence,created_at=m.created_at))
    return ConversationDetail(id=conv.id,title=conv.title,created_at=conv.created_at,updated_at=conv.updated_at,messages=messages)

@app.delete('/api/chat/conversations/{conversation_id}',status_code=204)
def delete_conversation(conversation_id:str,session:SessionDep,user:UserDep):
    conv=owned_conversation(session,conversation_id,user.id)
    for m in session.exec(select(Message).where(Message.conversation_id==conv.id)).all(): session.delete(m)
    session.delete(conv); session.commit(); return Response(status_code=204)

def count(session,model,uid): return int(session.exec(select(func.count()).select_from(model).where(model.user_id==uid)).one())
@app.get('/api/stats',response_model=StatsOut)
def stats(session:SessionDep,user:UserDep):
    indexed=int(session.exec(select(func.count()).select_from(DocumentRecord).where(DocumentRecord.user_id==user.id,DocumentRecord.status=='indexed')).one())
    return StatsOut(documents=count(session,DocumentRecord,user.id),indexed_documents=indexed,chunks=count(session,ChunkRecord,user.id),conversations=count(session,Conversation,user.id),messages=count(session,Message,user.id))
