// Conservative source inventory: exclusions are audited in strings.md.
const ts=require('../../apps/desktop/node_modules/typescript');
const fs=require('fs');
const file='apps/desktop/src/main.tsx';
const source=ts.createSourceFile(file,fs.readFileSync(file,'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.TSX);
const rows=[];
function visit(n){
 if(ts.isJsxText(n)||ts.isStringLiteral(n)||ts.isNoSubstitutionTemplateLiteral(n)||ts.isTemplateExpression(n)){
  const text=(ts.isTemplateExpression(n)?n.getText(source):n.text).replace(/\s+/g,' ').trim();
  if(text){const line=source.getLineAndCharacterOfPosition(n.getStart(source)).line+1;rows.push({line,syntax:ts.SyntaxKind[n.kind],text,parent:ts.SyntaxKind[n.parent.kind],attribute:ts.isJsxAttribute(n.parent)?n.parent.name.getText(source):''});}
 }
 ts.forEachChild(n,visit);
}
visit(source);console.log(JSON.stringify(rows,null,2));
