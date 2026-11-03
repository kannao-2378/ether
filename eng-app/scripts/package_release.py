"""Package reviewed production code only. Excludes all data, credentials and dev tools."""
import argparse,json,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def package(target):
 dist=ROOT/'frontend/dist'
 if not (dist/'index.html').exists():raise ValueError('Build frontend first: npm run build --prefix frontend -- --base=/eng/')
 if '/eng/assets/' not in (dist/'index.html').read_text(encoding='utf-8'):raise ValueError('Frontend must be built with --base=/eng/')
 paths=list((ROOT/'backend').glob('*.py'))
 paths=[p for p in paths if not p.name.startswith('test_')]
 paths+=[ROOT/'backend/requirements.txt',ROOT/'backend/requirements-production.txt',ROOT/'backend/resources/lookup-reference.sqlite3.gz',ROOT/'backend/resources/ecdict/LICENSE',ROOT/'backend/resources/compiled_courses.json',ROOT/'backend/resources/teaching_routes.json',ROOT/'backend/resources/transfer_practice.psv',ROOT/'backend/resources/composition_rules.json',ROOT/'backend/resources/sourced_transfer_pilot.json',ROOT/'backend/resources/THIRD_PARTY_NOTICES.md',ROOT/'scripts/create_auth_env.py']
 paths+=list((ROOT/'deploy').glob('*'))
 paths+=[p for p in dist.rglob('*') if p.is_file()]
 target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
  for p in paths:
   if p.is_file():z.write(p,p.relative_to(ROOT).as_posix())
  z.writestr('release.json',json.dumps(dict(base='/eng/',api='/eng/api/',private_data_included=False)))
 with zipfile.ZipFile(target) as z:
  assert not any('/data/' in n or '.env'==Path(n).name or n.endswith('.db') for n in z.namelist())
  assert z.testzip() is None
 return target
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',default=str(ROOT/'.tools/releases/english-app.zip'));a=p.parse_args();print(package(a.output))
