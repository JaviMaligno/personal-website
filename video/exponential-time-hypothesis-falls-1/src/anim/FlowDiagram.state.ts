import type { Label } from '../types.ts';
import { progress, sceneTime, stepTimes } from './steps.ts';

export type FlowNode = { id: string; label: Label; /** Scene second it appears at; default: its own beat. */ at?: number };
export type FlowEdge = { from: string; to: string; label?: Label; /** Drawn dashed and muted, with a gap. */ broken?: boolean };
export type FlowDiagramProps = { nodes: FlowNode[]; edges: FlowEdge[]; layout: 'vertical' | 'horizontal' };

export type Point = [number, number];

/** An edge draws in this long, in seconds. */
export const EDGE_SECONDS = 0.5;
/** A node with an incoming edge appears this long after the edge starts drawing. */
export const EDGE_LEAD = 0.3;
/** Pop-in of a node, in seconds. */
export const NODE_SECONDS = 0.45;
/** Share of a broken edge's length left out in the middle. */
export const BROKEN_GAP: [number, number] = [0.38, 0.62];

const indexOf = (p: FlowDiagramProps) => new Map(p.nodes.map((n, i) => [n.id, i]));

/** What the diagram draws at scene second `t`: nodes in order, each edge just before its later node. */
export function frameState(p: FlowDiagramProps, time: number, beats: number[], dur: number) {
  const t = sceneTime(time, dur);
  const idx = indexOf(p);
  const starts = stepTimes(p.nodes.length, beats, p.nodes.map((n) => n.at), Math.max(EDGE_SECONDS, EDGE_LEAD + NODE_SECONDS), dur);
  const incoming = p.nodes.map(() => false);
  const edges = p.edges.map((e) => {
    const a = idx.get(e.from);
    const b = idx.get(e.to);
    if (a === undefined || b === undefined || a === b) return { valid: false, broken: !!e.broken, start: 0, draw: 0 };
    const later = Math.max(a, b);
    incoming[later] = true;
    return { valid: true, broken: !!e.broken, start: starts[later], draw: progress(t, starts[later], EDGE_SECONDS) };
  });
  const nodes = p.nodes.map((n, i) => {
    const start = starts[i] + (incoming[i] ? EDGE_LEAD : 0);
    return { id: n.id, start, appear: progress(t, start, NODE_SECONDS) };
  });
  return { nodes, edges };
}

// ---- Geometry: positions inside a content box of w × h, origin at its top left. ----

export type NodeBox = { id: string; x: number; y: number; w: number; h: number };
export type EdgePath = { valid: boolean; points: Point[]; label: Point; labelAlign: 'left' | 'center' };

const MARGIN = 12;
/** Distance between the nodes and the first detour of an edge that skips nodes. */
const DETOUR = 44;
/** Extra distance for each further skipping edge, so detours never overlap. */
const DETOUR_STEP = 30;

/** Node boxes and edge polylines. Edges between neighbours are straight; others detour to the side. */
export function flowGeometry(p: FlowDiagramProps, box: { w: number; h: number }) {
  const n = Math.max(1, p.nodes.length);
  const idx = indexOf(p);
  const skips = p.edges.filter((e) => {
    const a = idx.get(e.from);
    const b = idx.get(e.to);
    return a !== undefined && b !== undefined && Math.abs(a - b) > 1;
  }).length;
  const detourRoom = skips ? DETOUR + DETOUR_STEP * (skips - 1) + MARGIN : 0;
  const labelled = p.edges.some((e) => e.label);
  const nodes: NodeBox[] = [];

  if (p.layout === 'vertical') {
    const w = Math.max(0, Math.min(640, box.w - 2 * (detourRoom + MARGIN)));
    const minGap = labelled ? 90 : 70;
    const h = Math.max(0, Math.min(150, (box.h - (n - 1) * minGap) / n));
    const gap = n > 1 ? Math.min(200, (box.h - n * h) / (n - 1)) : 0;
    const top = (box.h - (n * h + (n - 1) * gap)) / 2;
    p.nodes.forEach((nd, i) => nodes.push({ id: nd.id, x: box.w / 2, y: top + h / 2 + i * (h + gap), w, h }));
  } else {
    const minGap = labelled ? 150 : 90;
    const w = Math.max(0, Math.min(420, (box.w - (n - 1) * minGap - 2 * MARGIN) / n));
    const h = Math.max(0, Math.min(190, box.h * 0.5, box.h - 2 * detourRoom - 2 * MARGIN));
    const gap = n > 1 ? Math.min(220, (box.w - 2 * MARGIN - n * w) / (n - 1)) : 0;
    const left = (box.w - (n * w + (n - 1) * gap)) / 2;
    p.nodes.forEach((nd, i) => nodes.push({ id: nd.id, x: left + w / 2 + i * (w + gap), y: box.h / 2, w, h }));
  }

  let skip = 0;
  const edges: EdgePath[] = p.edges.map((e) => {
    const a = idx.get(e.from);
    const b = idx.get(e.to);
    if (a === undefined || b === undefined || a === b) return { valid: false, points: [], label: [0, 0], labelAlign: 'center' };
    const s = nodes[a];
    const d = nodes[b];
    const dir = b > a ? 1 : -1;
    if (Math.abs(a - b) === 1) {
      if (p.layout === 'vertical') {
        const y0 = s.y + (dir * s.h) / 2 + dir * MARGIN;
        const y1 = d.y - (dir * d.h) / 2 - dir * MARGIN;
        return { valid: true, points: [[s.x, y0], [d.x, y1]], label: [s.x + 26, (y0 + y1) / 2], labelAlign: 'left' };
      }
      const x0 = s.x + (dir * s.w) / 2 + dir * MARGIN;
      const x1 = d.x - (dir * d.w) / 2 - dir * MARGIN;
      return { valid: true, points: [[x0, s.y], [x1, d.y]], label: [(x0 + x1) / 2, s.y - 34], labelAlign: 'center' };
    }
    const off = DETOUR + DETOUR_STEP * skip++;
    if (p.layout === 'vertical') {
      const x0 = s.x + s.w / 2;
      const xo = Math.min(box.w, x0 + off);
      return { valid: true, points: [[x0 + 4, s.y], [xo, s.y], [xo, d.y], [x0 + 4, d.y]], label: [xo + 12, (s.y + d.y) / 2], labelAlign: 'left' };
    }
    const y0 = s.y + s.h / 2;
    const yo = Math.min(box.h, y0 + off);
    return { valid: true, points: [[s.x, y0 + 4], [s.x, yo], [d.x, yo], [d.x, y0 + 4]], label: [(s.x + d.x) / 2, yo + 22], labelAlign: 'center' };
  });
  return { nodes, edges };
}

export const polylineLength = (pts: Point[]): number =>
  pts.slice(1).reduce((sum, q, i) => sum + Math.hypot(q[0] - pts[i][0], q[1] - pts[i][1]), 0);

/** The part of a polyline between fractions `a` and `b` of its length. */
export const subPolyline = (pts: Point[], a: number, b: number): Point[] => {
  const total = polylineLength(pts);
  if (pts.length < 2 || total <= 0 || b <= a) return [];
  const from = a * total;
  const to = b * total;
  const out: Point[] = [];
  let walked = 0;
  for (let i = 1; i < pts.length; i++) {
    const [x0, y0] = pts[i - 1];
    const [x1, y1] = pts[i];
    const len = Math.hypot(x1 - x0, y1 - y0);
    const lerp = (d: number): Point => {
      const k = len ? (d - walked) / len : 0;
      return [x0 + (x1 - x0) * k, y0 + (y1 - y0) * k];
    };
    if (walked + len >= from && walked <= to) {
      if (!out.length) out.push(lerp(Math.max(from, walked)));
      out.push(lerp(Math.min(to, walked + len)));
    }
    walked += len;
  }
  return out;
};

/** The polylines to stroke for an edge drawn up to `draw` (0..1): broken edges skip their middle. */
export const edgeSegments = (pts: Point[], draw: number, broken: boolean): Point[][] => {
  if (draw <= 0) return [];
  if (!broken) return [subPolyline(pts, 0, draw)];
  const [g0, g1] = BROKEN_GAP;
  const parts = [subPolyline(pts, 0, Math.min(draw, g0))];
  if (draw > g1) parts.push(subPolyline(pts, g1, draw));
  return parts.filter((s) => s.length >= 2);
};
