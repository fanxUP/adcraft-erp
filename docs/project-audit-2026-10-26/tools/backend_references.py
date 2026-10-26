import ast
import json
from pathlib import Path
from collections import defaultdict

root = Path(__file__).resolve().parents[3]
app = root / 'backend/app'
modules = {}
trees = {}
for path in app.rglob('*.py'):
    parts = path.relative_to(root / 'backend').with_suffix('').parts
    name = '.'.join(parts[:-1] if parts[-1] == '__init__' else parts)
    modules[name] = path
    trees[name] = ast.parse(path.read_text(), filename=str(path))
edges = defaultdict(set)
incoming = defaultdict(set)
duplicates = []
for name, tree in trees.items():
    path = modules[name]
    for node in ast.walk(tree):
        imports = []
        if isinstance(node, ast.Import):
            imports = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            package = name if path.name == '__init__.py' else name.rpartition('.')[0]
            prefix = '.'.join(package.split('.')[:len(package.split('.')) - node.level + 1]) if node.level else ''
            base = '.'.join(x for x in (prefix, node.module) if x)
            imports = [base] + [f'{base}.{a.name}' for a in node.names]
        for imported in imports:
            if imported in modules:
                edges[name].add(imported)
                incoming[imported].add(name)
        if isinstance(node, (ast.Module, ast.ClassDef)):
            seen = {}
            for child in node.body:
                symbols = []
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    symbols = [child.name]
                elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                    symbols = [child.target.id]
                elif isinstance(child, ast.Assign):
                    symbols = [t.id for t in child.targets if isinstance(t, ast.Name)]
                for symbol in symbols:
                    if symbol in seen:
                        duplicates.append({'path':str(path.relative_to(root)), 'scope':getattr(node,'name','module'), 'symbol':symbol, 'lines':[seen[symbol],child.lineno]})
                    seen[symbol] = child.lineno
reachable = set()
def visit(name):
    if name in reachable:
        return
    reachable.add(name)
    for dep in edges[name]:
        visit(dep)
visit('app.main')
result = {
    'method':'AST import graph rooted at app.main; dynamic imports, model metadata registration, scripts and tests require manual classification.',
    'modules':len(modules),
    'reachable_from_main':len(reachable),
    'unreachable_from_main':[{'module':name,'path':str(path.relative_to(root)),'imported_by':sorted(incoming[name])} for name,path in modules.items() if name not in reachable],
    'duplicate_definitions':duplicates,
}
out = root / 'docs/project-audit-2026-10-26/evidence/backend-references.json'
out.write_text(json.dumps(result,indent=2,ensure_ascii=False))
print(json.dumps(result,indent=2,ensure_ascii=False))
