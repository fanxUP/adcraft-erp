import os
import json
import re
import tempfile
from pathlib import Path
os.environ['APP_ENV']='test'
os.environ['LOCAL_UPLOAD_DIR']=tempfile.mkdtemp(prefix='adcraft-audit-routes-')
os.environ['AI_ENABLED']='false'
from app.main import app
from fastapi.routing import APIRoute

def dependencies(dep):
    out=[]
    call=getattr(dep,'call',None)
    if call:
        out.append(f'{getattr(call,"__module__","")}.{getattr(call,"__name__",str(type(call)))}')
    for child in getattr(dep,'dependencies',[]):
        out.extend(dependencies(child))
    return out

routes=[]
for branch in app.routes:
    candidates=branch.effective_route_contexts() if hasattr(branch,'effective_route_contexts') else [branch]
    for candidate in candidates:
        original=getattr(candidate,'original_route',candidate)
        if isinstance(original,APIRoute):
            routes.append(candidate)
def endpoint(route):
    return getattr(route,'original_route',route).endpoint
shadow=[]
for i,r in enumerate(routes):
    sample=re.sub(r'\{[^}]+\}', '11111111-1111-1111-1111-111111111111',r.path)
    for earlier in routes[:i]:
        if r.methods & earlier.methods and earlier.path_regex.fullmatch(sample):
            shadow.append({'shadowed':r.path,'earlier':earlier.path,'methods':sorted(r.methods & earlier.methods),'endpoint':endpoint(r).__name__})
            break
entries=[{'path':r.path,'methods':sorted(r.methods),'endpoint':f'{endpoint(r).__module__}.{endpoint(r).__name__}','dependencies':dependencies(r.dependant)} for r in routes]
unauth=[e for e in entries if not any('.get_current_user' in dep for dep in e['dependencies'])]
result={'route_count':len(routes),'shadow_candidates':shadow,'without_current_user_dependency':unauth,'routes':entries}
Path('docs/project-audit-2026-10-26/evidence/routes.json').write_text(json.dumps(result,indent=2,ensure_ascii=False))
print(json.dumps({k:v for k,v in result.items() if k!='routes'},indent=2,ensure_ascii=False))
