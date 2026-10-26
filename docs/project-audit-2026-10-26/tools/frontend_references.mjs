import { fileURLToPath } from 'node:url'
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')
const base=path.join(root,'frontend/src')
const require=createRequire(path.join(root,'frontend/package.json'))
const ts=require('typescript')
const {parse}=require('@vue/compiler-sfc')
const files=[]
function scan(dir){for(const ent of fs.readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,ent.name);if(ent.isDirectory())scan(p);else if(/\.(ts|vue|scss|css|json)$/.test(p)&&!p.endsWith('.d.ts')&&!p.endsWith('.test.ts'))files.push(p)}}
scan(base)
const all=new Set(files)
const components=new Map()
const kebab=s=>s.replace(/([a-z0-9])([A-Z])/g,'$1-$2').toLowerCase()
for(const f of files.filter(f=>f.includes('/components/')&&f.endsWith('.vue'))){const name=path.basename(f,'.vue');components.set(name,f);components.set(kebab(name),f)}
function resolve(from,s){let p;if(s.startsWith('@/'))p=path.join(base,s.slice(2));else if(s.startsWith('.'))p=path.resolve(path.dirname(from),s);else return;return [p,p+'.ts',p+'.vue',p+'.json',p+'.scss',p+'.css',path.join(p,'index.ts')].find(x=>all.has(x))}
const edges=new Map(), incoming=new Map(), missing=[]
for(const f of files){const deps=new Set();edges.set(f,deps);let source=fs.readFileSync(f,'utf8');let code=source;if(f.endsWith('.vue')){const {descriptor}=parse(source);code=[descriptor.script?.content,descriptor.scriptSetup?.content].filter(Boolean).join('\n');for(const m of (descriptor.template?.content||'').matchAll(/<([A-Za-z][\w-]*)\b/g)){const c=components.get(m[1]);if(c&&c!==f)deps.add(c)}}
 function add(s){const p=resolve(f,s);if(p)deps.add(p);else if(s.startsWith('@/')||s.startsWith('.')){if(/\.(?:ts|vue|json|scss|css)$/.test(s)||!path.extname(s))missing.push({file:path.relative(root,f),import:s})}}
 if(/\.(ts|vue)$/.test(f)){const tree=ts.createSourceFile(f,code,ts.ScriptTarget.Latest,true);function walk(n){if((ts.isImportDeclaration(n)||ts.isExportDeclaration(n))&&n.moduleSpecifier&&ts.isStringLiteral(n.moduleSpecifier))add(n.moduleSpecifier.text);if(ts.isCallExpression(n)&&n.expression.kind===ts.SyntaxKind.ImportKeyword&&n.arguments.length&&ts.isStringLiteral(n.arguments[0]))add(n.arguments[0].text);ts.forEachChild(n,walk)}walk(tree)}
 for(const m of source.matchAll(/(?:@use|@import|\bsrc=)\s*['"]([^'"]+)['"]/g))add(m[1]);for(const d of deps){if(!incoming.has(d))incoming.set(d,[]);incoming.get(d).push(f)}}
const seen=new Set();function visit(f){if(seen.has(f))return;seen.add(f);for(const d of edges.get(f)||[])visit(d)}visit(path.join(base,'main.ts'))
const result={method:'TypeScript AST imports and lazy imports; Vue template components scanned using Vite auto-component conventions. Types included. Unreachable candidates require manual review.',files:files.length,reachable:seen.size,unreachable:files.filter(f=>!seen.has(f)).map(f=>({file:path.relative(root,f),imported_by:(incoming.get(f)||[]).map(x=>path.relative(root,x))})),missing_imports:missing}
fs.writeFileSync(path.join(root,'docs/project-audit-2026-10-26/evidence/frontend-references.json'),JSON.stringify(result,null,2))
console.log(JSON.stringify(result,null,2))
