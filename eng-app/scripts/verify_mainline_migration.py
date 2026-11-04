"""Rehearse production initialization on a temporary private snapshot, never live DBs."""
import argparse,json,os,sqlite3,sys,tempfile,zipfile
from contextlib import closing
from pathlib import Path

def verify(archive):
 with tempfile.TemporaryDirectory(prefix='pels-mainline-check-') as work:
  data=Path(work)
  with zipfile.ZipFile(archive) as z:
   with z.open('learning.db') as src:(data/'learning.db').write_bytes(src.read())
  tables=('answers','feedback_events','progress','memory_states','questions','spelling_checks','review_queue')
  with closing(sqlite3.connect(data/'learning.db')) as c:
   before={t:set(c.execute('SELECT * FROM '+t)) for t in tables}
   owners=dict(c.execute('SELECT * FROM group_primary'))
  os.environ.update(PELS_DATA_DIR=work,PELS_SKIP_BULK='1',PELS_MAINLINE_ENABLED='1',PELS_AUTH_ENABLED='0')
  sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
  import app,mainline_runtime,curriculum_engine
  from sqlalchemy import text
  with app.real_engine.connect() as c:
   losses={t:len(before[t]-set(tuple(r) for r in c.execute(text('SELECT * FROM '+t)))) for t in tables}
   now_owners=dict(c.execute(text('SELECT * FROM group_primary')).all())
   assert not any(losses.values()),losses
   assert all(now_owners[k]==v for k,v in owners.items())
   assert c.execute(text('PRAGMA integrity_check')).scalar()=='ok'
   status=mainline_runtime.status(c);assert status['topics']==148
   assert app.study_settings()['active-course']==mainline_runtime.COURSE
   assert curriculum_engine.report(c,mainline_runtime.COURSE)['ready_total']==148
  app.real_engine.dispose();app.test_engine.dispose()
  return dict(old_rows_changed_or_lost=losses,old_ownership_preserved=True,integrity='ok',
              active_course=mainline_runtime.COURSE,topics=148,source='private snapshot in temporary folder',live_data_changed=False)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('archive');a=p.parse_args();print(json.dumps(verify(a.archive)))
