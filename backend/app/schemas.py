from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class UserOut(BaseModel):
    id:str; email:EmailStr; full_name:str; created_at:datetime
    model_config=ConfigDict(from_attributes=True)
class RegisterIn(BaseModel):
    email:EmailStr; full_name:str=Field(min_length=2,max_length=120); password:str=Field(min_length=8,max_length=128)
class LoginIn(BaseModel): email:EmailStr; password:str
class AuthOut(BaseModel): access_token:str; token_type:str='bearer'; user:UserOut
class DocumentOut(BaseModel):
    id:str; original_name:str; file_type:str; size_bytes:int; status:str; chunking_strategy:str; chunk_count:int; error_message:str|None; created_at:datetime; updated_at:datetime
    model_config=ConfigDict(from_attributes=True)
class SourceOut(BaseModel):
    citation:int; chunk_id:str; document_id:str; filename:str; page_number:int|None=None; section_heading:str|None=None; excerpt:str; verified:bool=False
class RetrievedOut(BaseModel):
    chunk_id:str; document_id:str; filename:str; page_number:int|None=None; section_heading:str|None=None; excerpt:str
    dense_rank:int|None=None; sparse_rank:int|None=None; dense_score:float|None=None; sparse_score:float|None=None
    rrf_score:float=0; rerank_score:float|None=None; final_score:float=0
class ConfidenceOut(BaseModel): retrieval:float; citation_coverage:float; citation_validity:float; composite:float
class AskIn(BaseModel):
    question:str=Field(min_length=2,max_length=4000); conversation_id:str|None=None; retrieval_mode:Literal['hybrid','dense','bm25']='hybrid'; top_k:int=Field(default=5,ge=1,le=12)
class AskOut(BaseModel):
    conversation_id:str; answer:str; sources:list[SourceOut]; confidence:ConfidenceOut; retrieval_mode:str; model:str; insufficient_context:bool; retrieved_chunks:list[RetrievedOut]
class MessageOut(BaseModel): id:str; role:str; content:str; sources:list[SourceOut]=[]; confidence:float|None=None; created_at:datetime
class ConversationOut(BaseModel): id:str; title:str; created_at:datetime; updated_at:datetime
class ConversationDetail(ConversationOut): messages:list[MessageOut]
class StatsOut(BaseModel): documents:int; indexed_documents:int; chunks:int; conversations:int; messages:int
