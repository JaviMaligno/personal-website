// Print the "units" of TypeScript sources as JSON (used by aa.tasks to compute
// protected_hits at function level).
//
// Usage: node functions.mjs <dir-with-node_modules/typescript>  < in.json > out.json
//   in.json:  [{"key": "...", "text": "...", "tsx": false}, ...]
//   out.json: {"<key>": [{"kind": "fn"|"stmt", "name": "...", "start": 1, "end": 9}, ...]}
//
// A unit is either a *named* function (function/method/constructor/accessor
// declaration, or an arrow/function expression bound to a variable, property or
// assignment) or a top-level statement of the file. Anonymous callbacks are not
// units: their lines belong to the enclosing named function. Lines are 1-based
// and inclusive; ranges nest, so the innermost unit of a line is the smallest
// range that contains it.
import { createRequire } from 'node:module';
import path from 'node:path';
import { readFileSync } from 'node:fs';

const tsDir = process.argv[2] ?? process.env.AA_TS_DIR;
if (!tsDir) {
  console.error('usage: node functions.mjs <dir containing node_modules/typescript>');
  process.exit(2);
}
const ts = createRequire(path.join(path.resolve(tsDir), 'package.json'))('typescript');

const input = JSON.parse(readFileSync(0, 'utf8'));
const out = {};

function nameOf(n) {
  if (n.name && ts.isIdentifier(n.name)) return n.name.text;
  if (n.name && (ts.isStringLiteral(n.name) || ts.isPrivateIdentifier(n.name))) return n.name.text;
  if (n.name) return n.name.getText();
  return null;
}

function boundName(fn) {
  const p = fn.parent;
  if (!p) return null;
  if (ts.isVariableDeclaration(p) || ts.isPropertyAssignment(p) || ts.isPropertyDeclaration(p)) {
    return p.initializer === fn ? nameOf(p) : null;
  }
  if (ts.isBinaryExpression(p) && p.right === fn && p.operatorToken.kind === ts.SyntaxKind.EqualsToken) {
    return p.left.getText();
  }
  return null;
}

for (const { key, text, tsx } of input) {
  const sf = ts.createSourceFile(tsx ? 'f.tsx' : 'f.ts', text, ts.ScriptTarget.Latest, true,
    tsx ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  const line = pos => sf.getLineAndCharacterOfPosition(pos).line + 1;
  const units = [];
  const add = (kind, name, node) =>
    units.push({ kind, name, start: line(node.getStart(sf)), end: line(node.getEnd()) });

  for (const st of sf.statements) {
    const first = st.getText(sf).split('\n')[0].trim().slice(0, 120);
    add('stmt', first, st);
  }
  const visit = n => {
    let name = null;
    if (ts.isFunctionDeclaration(n) || ts.isMethodDeclaration(n) || ts.isGetAccessor(n) ||
        ts.isSetAccessor(n) || ts.isMethodSignature(n)) {
      name = nameOf(n);
    } else if (ts.isConstructorDeclaration(n)) {
      name = 'constructor';
    } else if (ts.isArrowFunction(n) || ts.isFunctionExpression(n)) {
      name = boundName(n) ?? (n.name ? nameOf(n) : null);
    }
    if (name && (n.body || ts.isMethodSignature(n))) {
      // Qualify methods with their class so counterparts match across images.
      let q = name;
      for (let p = n.parent; p; p = p.parent) {
        if ((ts.isClassDeclaration(p) || ts.isClassExpression(p)) && p.name) { q = `${p.name.text}.${q}`; break; }
      }
      add('fn', q, n);
    }
    ts.forEachChild(n, visit);
  };
  ts.forEachChild(sf, visit);
  out[key] = units;
}
process.stdout.write(JSON.stringify(out));
