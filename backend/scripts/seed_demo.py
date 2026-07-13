from pathlib import Path
from uuid import uuid4
import hashlib, shutil
from sqlmodel import Session, select
from app.config import settings
from app.database import create_db_and_tables, engine
from app.models import DocumentRecord, User
from app.rag import ingest
from app.security import hash_password

def main():
    create_db_and_tables(); sample=Path(__file__).resolve().parents[2]/'sample_documents'
    with Session(engine) as s:
        user=s.exec(select(User).where(User.email=='demo@example.com')).first()
        if not user:
            user=User(email='demo@example.com',full_name='Demo User',hashed_password=hash_password('DemoPassword123!')); s.add(user); s.commit(); s.refresh(user)
        folder=settings.upload_path/user.id; folder.mkdir(parents=True,exist_ok=True)
        for src in sample.iterdir():
            data=src.read_bytes(); digest=hashlib.sha256(data).hexdigest()
            if s.exec(select(DocumentRecord).where(DocumentRecord.user_id==user.id,DocumentRecord.sha256==digest)).first(): continue
            stored=f'{uuid4()}{src.suffix.lower()}'; target=folder/stored; shutil.copy2(src,target)
            doc=DocumentRecord(user_id=user.id,original_name=src.name,stored_name=stored,file_type=src.suffix[1:],size_bytes=len(data),sha256=digest); s.add(doc); s.commit(); s.refresh(doc); ingest(s,doc,target)
            print('Indexed',src.name,doc.chunk_count)
    print('Demo login: demo@example.com / DemoPassword123!')
if __name__=='__main__': main()
