from pathlib import Path
import json
from sqlmodel import Session, select
from app.database import create_db_and_tables, engine
from app.models import Conversation, User
from app.rag import package_answer, retrieve

def main():
    create_db_and_tables(); cases=json.loads((Path(__file__).resolve().parents[2]/'evaluation_dataset/golden_qa.json').read_text())
    with Session(engine) as s:
        user=s.exec(select(User).where(User.email=='demo@example.com')).first()
        if not user: raise SystemExit('Run python -m scripts.seed_demo first')
        results=[]
        for c in cases:
            hits=retrieve(s,c['question'],user.id,'hybrid',5); answer,sources,confidence,insufficient,debug=package_answer(c['question'],hits)
            low=answer.lower(); score=sum(k.lower() in low for k in c.get('expected_keywords',[]))/max(1,len(c.get('expected_keywords',[])))
            results.append({'id':c['id'],'answer':answer,'keyword_accuracy':score,'confidence':confidence,'sources':[x['filename'] for x in sources]}); print(c['id'],score)
    out=Path('evaluation_report.json'); out.write_text(json.dumps(results,indent=2)); print('Written',out)
if __name__=='__main__': main()
