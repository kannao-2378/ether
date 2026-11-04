"""Loopback-only mainline review host. Always uses its own disposable data folder."""
import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'.tools/mainline-preview'
DATA.mkdir(parents=True,exist_ok=True)
os.environ['PELS_DATA_DIR']=str(DATA/'data')
os.environ['PELS_SKIP_BULK']='1'
os.environ['PELS_AUTH_ENABLED']='0'
sys.path.insert(0,str(ROOT/'backend'))

import app as api
import starter_course
from sqlalchemy import text
from fastapi import FastAPI
from fastapi.responses import HTMLResponse,RedirectResponse
from fastapi.staticfiles import StaticFiles

with api.test_engine.begin() as c:
    if not starter_course.enabled(c):
        if c.execute(text('SELECT 1 FROM answers LIMIT 1')).first():
            raise RuntimeError('隔离预览已有学习记录，未自动改写课程或清空记录')
        starter_course.activate(c,test_only=True,pack='mainline')

@api.app.get('/')
def preview_index():
    page=(ROOT/'frontend/dist/index.html').read_text(encoding='utf-8')
    return HTMLResponse(page.replace('</head>',"<script>sessionStorage.setItem('learning-test','1');document.title='通用主线 · 隔离试学';</script></head>"))

api.app.mount('/',StaticFiles(directory=ROOT/'frontend/dist',html=True))
preview=FastAPI(docs_url=None)

@preview.get('/')
def index():return RedirectResponse('/eng/')

preview.mount('/eng',api.app)

if __name__=='__main__':
    import argparse
    import uvicorn
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=18013)
    args=parser.parse_args()
    (DATA/'preview.pid').write_text(str(os.getpid()),encoding='ascii')
    uvicorn.run(preview,host='127.0.0.1',port=args.port)
