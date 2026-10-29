import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import { visit } from 'unist-util-visit';

/**
 * Math → Dev.to {% katex %} liquid tags.
 *
 * Formulas are located with the same parser the site uses (remark-math over
 * GFM), so whatever renders as math on javieraguilar.ai renders as math on
 * Dev.to — and nothing else does (code spans, raw HTML, a lone "$5").
 */

// Dev.to runs markdown backslash-escape removal *inside* {% katex %} bodies:
// "\#F" reaches KaTeX as "#F" (ParseError), "\{" as "{", "\\" as "\".
// Measured on a Dev.to draft (2026-10-29) for every ASCII punctuation char;
// these lose their backslash, while " $ % ' , ; keep it.
const STRIPPED = new Set('!#&()*+-./:<=>?@[]^_`{|}~\\');

/** Double the backslash of every control symbol Dev.to would unescape. */
export function protectForDevto(tex) {
  let out = '';
  for (let i = 0; i < tex.length; i++) {
    const ch = tex[i];
    if (ch === '\\' && i + 1 < tex.length) {
      const next = tex[i + 1];
      out += STRIPPED.has(next) ? `\\\\${next === '\\' ? '\\\\' : next}` : `\\${next}`;
      i++;
    } else {
      out += ch;
    }
  }
  return out;
}

export function convertMathForDevto(markdown) {
  const tree = unified().use(remarkParse).use(remarkGfm).use(remarkMath).parse(markdown);
  const spans = [];
  visit(tree, ['math', 'inlineMath'], (node, _index, parent) => {
    // "$$…$$" written inside a paragraph parses as inlineMath; when it is the
    // whole paragraph it reads as a display equation, so keep it one on Dev.to.
    const display = node.type === 'math' || (parent?.type === 'paragraph' && parent.children.length === 1);
    spans.push({ start: node.position.start.offset, end: node.position.end.offset, node, display });
  });
  let out = markdown;
  for (const { start, end, node, display } of spans.sort((a, b) => b.start - a.start)) {
    const tex = protectForDevto(node.value.trim());
    const tag = display
      ? `{% katex %}\n${tex}\n{% endkatex %}`
      : `{% katex inline %}${tex}{% endkatex %}`;
    out = out.slice(0, start) + tag + out.slice(end);
  }
  return out;
}
