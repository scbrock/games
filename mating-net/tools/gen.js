const { Chess } = require('chess.js');
const { keys } = require('./solve.js');
const FILES = 'abcdefgh';
const sq = (f, r) => FILES[f] + (r + 1);
function legalStart(fen) {
  const c = new Chess();
  if (!c.validate_fen(fen).valid) return null;
  if (!c.load(fen)) return null;
  if (c.in_check() || c.game_over()) return null;
  // The side not to move must not be in check either.
  const parts = fen.split(' '); parts[1] = parts[1] === 'w' ? 'b' : 'w';
  const d = new Chess(); if (!d.load(parts.join(' ')) || d.in_check()) return null;
  return c;
}
function rnd(a) { return a[Math.floor(Math.random() * a.length)]; }
function build() {
  const board = {};
  const put = (s, p) => { if (board[s]) return false; board[s] = p; return true; };
  // Black king shelter on the king side or queen side.
  const side = Math.random() < 0.75 ? 'k' : 'q';
  const kf = side === 'k' ? rnd([6, 6, 7, 5]) : rnd([1, 2, 2]);
  put(sq(kf, 7), 'k');
  for (const df of [-1, 0, 1]) {
    const f = kf + df; if (f < 0 || f > 7) continue;
    const r = Math.random();
    if (r < 0.62) put(sq(f, 6), 'p'); else if (r < 0.85) put(sq(f, 5), 'p');
  }
  const extras = ['r', 'r', 'q', 'b', 'n', 'p', 'p'];
  const nb = 1 + Math.floor(Math.random() * 3);
  for (let i = 0; i < nb; i++) { const p = rnd(extras); for (let t = 0; t < 20; t++) { const f = Math.floor(Math.random() * 8), r = 3 + Math.floor(Math.random() * 5); if (p === 'p' && r === 7) continue; if (put(sq(f, r), p)) break; } }
  put('g1', 'K'); put('f2', 'P'); put('g2', 'P'); put('h2', 'P');
  if (Math.random() < 0.5) put('a2', 'P');
  const atk = ['Q', 'Q', 'R', 'R', 'B', 'B', 'N', 'N', 'P'];
  const nw = 2 + Math.floor(Math.random() * 2);
  for (let i = 0; i < nw; i++) { const p = rnd(atk); for (let t = 0; t < 20; t++) { const f = Math.floor(Math.random() * 8), r = 1 + Math.floor(Math.random() * 7); if (p === 'P' && (r === 7 || r < 2)) continue; if (put(sq(f, r), p)) break; } }
  let rows = [];
  for (let r = 7; r >= 0; r--) { let row = '', e = 0; for (let f = 0; f < 8; f++) { const p = board[sq(f, r)]; if (p) { if (e) row += e; e = 0; row += p; } else e++; } if (e) row += e; rows.push(row); }
  return rows.join('/') + ' w - - 0 1';
}
const material = (c) => { const v = { p: 1, n: 3, b: 3, r: 5, q: 9, k: 0 }; let w = 0, b = 0; for (const row of c.board()) for (const x of row) if (x) (x.color === 'w' ? (w += v[x.type]) : (b += v[x.type])); return [w, b]; };
const out = [];
const deadline = Date.now() + (+process.argv[2] || 120) * 1000;
const want = { 1: +process.argv[3] || 40, 2: +process.argv[4] || 40 };
const got = { 1: 0, 2: 0 };
let tries = 0;
while (Date.now() < deadline && (got[1] < want[1] || got[2] < want[2])) {
  tries++;
  const fen = build();
  const c = legalStart(fen); if (!c) continue;
  const [w, b] = material(c);
  if (w - b > 9 || b < 3) continue; // avoid lopsided positions
  const k1 = keys(c, 1);
  if (k1.length) { if (k1.length === 1 && got[1] < want[1]) { out.push({ fen, n: 1, keys: k1 }); got[1]++; } continue; }
  if (got[2] >= want[2]) continue;
  // Cheap pre-filter: mate in 2 needs a forcing first move most of the time; still check all.
  const k2 = keys(c, 2);
  if (k2.length === 1) { out.push({ fen, n: 2, keys: k2 }); got[2]++; }
}
require('fs').writeFileSync(process.argv[5] || 'gen.json', JSON.stringify(out));
console.log('tries', tries, 'got', JSON.stringify(got));
