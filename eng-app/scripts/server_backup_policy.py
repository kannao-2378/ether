"""Server-only backup policy: changed logical SQLite data, >=5 days, keep two."""
from contextlib import closing
import argparse,hashlib,re,sqlite3,tempfile,zipfile,os
from pathlib import Path
from datetime import datetime,timedelta
NAME=re.compile(r'^learning-(\d{8}-\d{6})\.zip$')
def digest(db):
    h=hashlib.sha256()
    with closing(sqlite3.connect(db)) as c:
        for line in c.iterdump():h.update(line.encode('utf-8'));h.update(b'\n')
    return h.hexdigest()
def run(data,folder,stamp=None):
    stamp=stamp or datetime.now();data=Path(data);folder=Path(folder)
    if not (data/'learning.db').is_file():raise ValueError('Learning database not found')
    folder.mkdir(parents=True,exist_ok=True)
    archives=sorted([p for p in folder.iterdir() if p.is_file() and NAME.fullmatch(p.name)],reverse=True)
    if archives and stamp-datetime.strptime(NAME.fullmatch(archives[0].name)[1],'%Y%m%d-%H%M%S')<timedelta(days=5):return 'SKIP less than five days'
    with tempfile.TemporaryDirectory() as tmp:
        snapshot=Path(tmp)/'learning.db'
        with closing(sqlite3.connect((data/'learning.db').resolve().as_uri()+'?mode=ro',uri=True)) as source,closing(sqlite3.connect(snapshot)) as dest:source.backup(dest)
        with closing(sqlite3.connect(snapshot)) as c:
            if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Database integrity check failed')
        if archives:
            previous=Path(tmp)/'previous';previous.mkdir()
            with zipfile.ZipFile(archives[0]) as z:
                if z.testzip():raise ValueError('Previous backup is corrupt')
                # Fixed member only, never extract arbitrary paths.
                with z.open('learning.db') as src:(previous/'learning.db').write_bytes(src.read())
            if digest(snapshot)==digest(previous/'learning.db'):return 'SKIP no data changes'
        target=folder/('learning-'+stamp.strftime('%Y%m%d-%H%M%S')+'.zip');partial=target.with_suffix('.zip.part')
        try:
            with zipfile.ZipFile(partial,'w',zipfile.ZIP_DEFLATED) as z:z.write(snapshot,'learning.db')
            with zipfile.ZipFile(partial) as z:
                if z.testzip():raise ValueError('Archive verification failed')
            os.chmod(partial,0o600)
            if os.name=='posix' and os.geteuid()==0:
                import pwd
                owner=pwd.getpwnam('admin');os.chown(partial,owner.pw_uid,owner.pw_gid)
            partial.replace(target)
        finally:partial.unlink(missing_ok=True)
    for old in archives[1:]:old.unlink()
    return 'OK '+target.name
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data',default='/var/lib/pels');p.add_argument('--folder',default='/var/backups/pels');args=p.parse_args()
    os.umask(0o077)
    # Cron and manual invocation must not race.
    import fcntl
    with open('/run/lock/pels-backup.lock','a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        print(run(args.data,args.folder))
