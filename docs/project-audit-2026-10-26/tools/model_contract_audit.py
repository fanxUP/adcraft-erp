import ast
import importlib
import json
import os
import pkgutil
from pathlib import Path
os.environ['APP_ENV']='test'
import app.models
for item in pkgutil.iter_modules(app.models.__path__):
    importlib.import_module('app.models.'+item.name)
root=Path(__file__).resolve().parents[3]
findings=[]
for path in (root/'backend/app').rglob('*.py'):
    tree=ast.parse(path.read_text())
    aliases={}
    for node in ast.walk(tree):
        if isinstance(node,ast.ImportFrom) and node.module and node.module.startswith('app.models.'):
            module=importlib.import_module(node.module)
            for alias in node.names:
                model=getattr(module,alias.name,None)
                if isinstance(model,type) and hasattr(model,'__table__'):
                    aliases[alias.asname or alias.name]=model
    for node in ast.walk(tree):
        if isinstance(node,ast.Attribute) and isinstance(node.value,ast.Name) and node.value.id in aliases:
            model=aliases[node.value.id]
            if not hasattr(model,node.attr):
                findings.append({'path':str(path.relative_to(root)),'line':node.lineno,'model':model.__name__,'attribute':node.attr})
out=root/'docs/project-audit-2026-10-26/evidence/model-contracts.json'
out.write_text(json.dumps(findings,ensure_ascii=False,indent=2))
print(json.dumps(findings,ensure_ascii=False,indent=2))
