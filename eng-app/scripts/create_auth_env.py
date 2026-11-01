"""Run on the server: prompt locally, save a hash; never print a password."""
import argparse,getpass,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from private_auth import password_hash

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--origin',default='https://kannao.top');a=p.parse_args()
 first=getpass.getpass('Learning password (at least 12 characters): ')
 second=getpass.getpass('Repeat password: ')
 if len(first)<12 or first!=second:raise SystemExit('Password too short or confirmation does not match; no file written.')
 # Configuration is parsed by systemd, never interpolated into a shell command.
 from urllib.parse import urlparse
 u=urlparse(a.origin)
 if u.scheme!='https' or not u.hostname or u.path or any(ch.isspace() for ch in a.origin):raise SystemExit('Use an HTTPS origin without a path.')
 target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True)
 fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
 with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as f:
  f.write('PELS_AUTH_ENABLED=1\nPELS_AUTH_PASSWORD_HASH='+password_hash(first)+'\nPELS_PUBLIC_ORIGIN='+a.origin+'\nPELS_COOKIE_PATH=/eng/\nPELS_DATA_DIR=/var/lib/pels\n')
 print('Created private server configuration:',target)
