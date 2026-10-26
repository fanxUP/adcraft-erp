import { fileURLToPath } from 'node:url'
import fs from 'node:fs'
import path from 'node:path'
import {createRequire} from 'node:module'
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../..')
const require=createRequire(path.join(root,'frontend/package.json'))
const ts=require('typescript')
const backend=JSON.parse(fs.readFileSync(path.join(root,'docs/project-audit-2026-10-26/evidence/routes.json'),'utf8')).routes
const normalize=p=>p.split('?')[0].replace(/\{[^}]*\}/g,'{}').replace(/\/$/,'')
const contracts=new Set(backend.flatMap(r=>r.methods.map(m=>`${m} ${normalize(r.path.replace(/^\/api\/v1/,''))}`)))
const results=[],unknown=[]
for(const file of fs.readdirSync(path.join(root,'frontend/src/api')).filter(f=>f.endsWith('.ts')&&!f.endsWith('.test.ts'))){const source=fs.readFileSync(path.join(root,'frontend/src/api',file),'utf8');const tree=ts.createSourceFile(file,source,ts.ScriptTarget.Latest,true);function walk(n){if(ts.isCallExpression(n)){const methodName=ts.isIdentifier(n.expression)?n.expression.text:ts.isPropertyAccessExpression(n.expression)?n.expression.name.text:'';const method={get:'GET',post:'POST',put:'PUT',patch:'PATCH',del:'DELETE',delete:'DELETE'}[methodName];const arg=n.arguments[0];if(method&&arg){let url;if(ts.isStringLiteral(arg)||ts.isNoSubstitutionTemplateLiteral(arg))url=arg.text;else if(ts.isTemplateExpression(arg)){url=arg.head.text;for(const span of arg.templateSpans)url+='{}'+span.literal.text}if(url?.startsWith('/')){const lc=tree.getLineAndCharacterOfPosition(n.getStart());results.push({file:`frontend/src/api/${file}`,line:lc.line+1,method,url,matched:contracts.has(`${method} ${normalize(url)}`)})}else unknown.push({file,method,expression:arg.getText().slice(0,100)})}}ts.forEachChild(n,walk)}walk(tree)}
const result={calls:results.length,matched:results.filter(r=>r.matched).length,unmatched:results.filter(r=>!r.matched),dynamic_or_wrapper_calls:unknown,contracts:results}
fs.writeFileSync(path.join(root,'docs/project-audit-2026-10-26/evidence/api-contracts.json'),JSON.stringify(result,null,2))
console.log(JSON.stringify({calls:result.calls,matched:result.matched,unmatched:result.unmatched},null,2))
