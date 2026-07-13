from dataclasses import dataclass
from pathlib import Path
import re
import fitz
from bs4 import BeautifulSoup
from docx import Document as Docx

@dataclass
class Section:
    text:str; page_number:int|None=None; heading:str|None=None

def clean(t):
    t=t.replace('\x00',' '); t=re.sub(r'[ \t]+',' ',t); t=re.sub(r'\n{3,}','\n\n',t); return t.strip()
def heading(t):
    x=next((x.strip() for x in t.splitlines() if x.strip()),''); return x if 0<len(x)<=120 else None

def load_pdf(p):
    out=[]
    with fitz.open(p) as pdf:
        for i,page in enumerate(pdf):
            t=clean(page.get_text('text'))
            if t: out.append(Section(t,i+1,heading(t)))
    return out

def load_docx(p):
    doc=Docx(p); out=[]; h=None; buf=[]
    def flush():
        nonlocal buf
        t=clean('\n'.join(buf))
        if t: out.append(Section(t,None,h))
        buf=[]
    for para in doc.paragraphs:
        t=para.text.strip()
        if not t: continue
        if (para.style.name or '').lower().startswith('heading'): flush(); h=t
        else: buf.append(t)
    flush(); return out

def load_md_text(p):
    raw=p.read_text(encoding='utf-8',errors='ignore')
    if p.suffix.lower()=='.txt':
        t=clean(raw); return [Section(t,None,heading(t))] if t else []
    out=[]; h=None; buf=[]
    for line in raw.splitlines():
        m=re.match(r'^\s{0,3}#{1,6}\s+(.+?)\s*$',line)
        if m:
            t=clean('\n'.join(buf))
            if t: out.append(Section(t,None,h))
            buf=[]; h=m.group(1).strip()
        else: buf.append(line)
    t=clean('\n'.join(buf))
    if t: out.append(Section(t,None,h))
    return out

def load_html(p):
    soup=BeautifulSoup(p.read_text(encoding='utf-8',errors='ignore'),'html.parser')
    for x in soup(['script','style','noscript']): x.decompose()
    out=[]; h=None; buf=[]
    def flush():
        nonlocal buf
        t=clean('\n'.join(buf))
        if t: out.append(Section(t,None,h))
        buf=[]
    for el in soup.find_all(['h1','h2','h3','h4','h5','h6','p','li','pre']):
        t=el.get_text(' ',strip=True)
        if not t: continue
        if el.name.startswith('h'): flush(); h=t
        else: buf.append(t)
    flush(); return out

def load_document(path:Path):
    ext=path.suffix.lower()
    if ext=='.pdf': out=load_pdf(path)
    elif ext=='.docx': out=load_docx(path)
    elif ext in {'.txt','.md'}: out=load_md_text(path)
    elif ext in {'.html','.htm'}: out=load_html(path)
    else: raise ValueError(f'Unsupported type: {ext}')
    if not out: raise ValueError('No readable text found')
    return out
