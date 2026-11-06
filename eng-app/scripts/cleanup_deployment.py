"""Bounded post-deployment cleanup. Dry run by default; never removes live databases."""
import argparse,json,re,shutil,zipfile,sqlite3,tempfile,os,pwd
from pathlib import Path
from contextlib import closing
from datetime import datetime
RUNTIME=Path('/opt/pels');DATA=Path('/var/lib/pels');BACKUPS=Path('/var/backups/pels');STATIC=Path('/var/www/pels-static/eng')
STAMP=re.compile(r'(\d{8}-\d{6})')
def validate(p):
 with tempfile.TemporaryDirectory(prefix='pels-backup-check-') as temp:
  with zipfile.ZipFile(p) as z:
   if z.testzip() is not None or 'learning.db' not in z.namelist():raise ValueError('Invalid backup '+str(p))
   with z.open('learning.db') as source,open(Path(temp)/'learning.db','wb') as target:shutil.copyfileobj(source,target)
  with closing(sqlite3.connect(str(Path(temp)/'learning.db'))) as c:
   if c.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Invalid SQLite backup '+str(p))
def size(p):
 if p.is_symlink():raise ValueError('Refuse symlink '+str(p))
 return sum(f.stat().st_size for f in p.rglob('*') if f.is_file() and not f.is_symlink()) if p.is_dir() else p.stat().st_size

def run(apply=False,snapshot=False):
 if os.name!='posix' or not (DATA/'learning.db').is_file():raise ValueError('Run only on the configured server')
 for root in [RUNTIME,DATA,BACKUPS,STATIC]:
  if root.is_symlink() or root.resolve()!=root:raise ValueError('Unexpected deployment path')
 if snapshot:
  if not apply:raise ValueError('Snapshot requires --apply')
  from export_learning_bundle import export
  target=BACKUPS/('learning-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.zip');partial=target.with_suffix('.zip.part')
  if target.exists():raise ValueError('Backup exists')
  export(partial,DATA);validate(partial);owner=pwd.getpwnam('admin');os.chown(partial,owner.pw_uid,owner.pw_gid);os.chmod(partial,0o600);partial.replace(target)
 archives=[p for p in BACKUPS.glob('learning-*.zip') if re.fullmatch(r'learning-\d{8}-\d{6}\.zip',p.name)]
 archives += [p for p in DATA.glob('before-*.zip') if STAMP.search(p.name)]
 by_stamp={}
 for p in sorted(archives,key=lambda p:p.parent==BACKUPS):by_stamp[STAMP.search(p.name)[0]]=p
 selected=sorted(by_stamp,reverse=True)[:2]
 if len(selected)<2:raise ValueError('Keep at least two valid backups before pruning')
 for stamp in selected:validate(by_stamp[stamp])
 keep=[]
 for stamp in selected:
  src=by_stamp[stamp];dst=BACKUPS/('learning-'+stamp+'.zip')
  if apply and src!=dst:
   shutil.copy2(src,dst);owner=pwd.getpwnam('admin');os.chown(dst,owner.pw_uid,owner.pw_gid);os.chmod(dst,0o600)
  keep.append(dst)
 targets=[p for p in archives if p not in keep]
 rollbacks=sorted([p for p in RUNTIME.glob('.before-*') if STAMP.search(p.name) and p.is_dir()],key=lambda p:STAMP.search(p.name)[0],reverse=True)
 targets+=rollbacks[1:]
 targets += [p for p in RUNTIME.iterdir() if p.is_dir() and re.fullmatch(r'\.[a-z-]+-stage-\d{8}-\d{6}',p.name)]
 targets += list(RUNTIME.glob('.app-before-*.py'))
 targets += [p for p in Path('/tmp').iterdir() if p.is_file() and (p.name.startswith('pels-') or p.name.startswith('deploy-'))]
 if (DATA/'local-sync-latest.zip').is_file():targets.append(DATA/'local-sync-latest.zip')
 # Source tests are retained in Git, not needed by the running service.
 targets+=list((RUNTIME/'backend').glob('test_*.py'))
 refs=set(re.findall(r'assets/([^\"\'<>]+)',(STATIC/'index.html').read_text()))
 if rollbacks and (rollbacks[0]/'static/index.html').exists():refs.update(re.findall(r'assets/([^\"\'<>]+)',(rollbacks[0]/'static/index.html').read_text()))
 targets += [p for p in (STATIC/'assets').iterdir() if p.is_file() and re.fullmatch(r'index-[A-Za-z0-9_-]+\.(js|css)',p.name) and p.name not in refs]
 allowed={RUNTIME,DATA,BACKUPS,Path('/tmp'),RUNTIME/'backend',STATIC/'assets'}
 total=0;removed=[]
 for p in dict.fromkeys(targets):
  if p.parent not in allowed or p.is_symlink() or p.resolve().parent!=p.parent:raise ValueError('Unexpected cleanup target '+str(p))
  n=size(p);total+=n;removed.append(dict(path=str(p),bytes=n))
  if apply:
   if p.is_dir():shutil.rmtree(p)
   else:p.unlink()
 report=dict(applied=apply,bytes=total,kept_backups=list(map(str,keep)),kept_rollback=str(rollbacks[0]) if rollbacks else None,targets=removed)
 print(json.dumps(report));return report
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--apply',action='store_true');p.add_argument('--snapshot',action='store_true');a=p.parse_args();run(a.apply,a.snapshot)
