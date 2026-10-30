const { Chess } = require('chess.js');
// Can the side to move force mate within n of its own moves?
function forced(c, n) {
  for (const m of c.moves()) {
    c.move(m);
    let ok;
    if (c.in_checkmate()) ok = true;
    else if (n === 1 || c.game_over()) ok = false;
    else {
      ok = true;
      for (const r of c.moves()) { c.move(r); const s = forced(c, n - 1); c.undo(); if (!s) { ok = false; break; } }
    }
    c.undo();
    if (ok) return true;
  }
  return false;
}
function keys(c, n) {
  const out = [];
  for (const m of c.moves()) {
    c.move(m);
    let ok;
    if (c.in_checkmate()) ok = true;
    else if (n === 1 || c.game_over()) ok = false;
    else { ok = true; for (const r of c.moves()) { c.move(r); const s = forced(c, n - 1); c.undo(); if (!s) { ok = false; break; } } }
    c.undo();
    if (ok) out.push(m);
  }
  return out;
}
// Defender reply that delays mate longest; then build a main line.
function line(c, n) {
  const seq = [];
  for (let k = n; k >= 1; k--) {
    const ks = keys(c, k);
    if (!ks.length) return null;
    // Prefer a mating move if one exists at this step.
    let mv = ks.find((m) => { c.move(m); const mt = c.in_checkmate(); c.undo(); return mt; }) || ks[0];
    c.move(mv); seq.push(mv);
    if (c.in_checkmate()) return seq;
    // Pick the defence after which mate takes longest (stays forced at k-1 by construction).
    let best = null, bestLen = -1;
    for (const r of c.moves()) {
      c.move(r);
      let len = k - 1;
      for (let j = 1; j < k - 1; j++) if (forced(c, j)) { len = j; break; }
      c.undo();
      if (len > bestLen) { bestLen = len; best = r; }
    }
    c.move(best); seq.push(best);
  }
  return c.in_checkmate() ? seq : null;
}
function analyse(fen, maxN = 3) {
  const c = new Chess(fen);
  if (!c.validate_fen(fen).valid) return { error: c.validate_fen(fen).error };
  if (c.in_check() && false) {}
  for (let n = 1; n <= maxN; n++) {
    const ks = keys(c, n);
    if (ks.length) return { n, keys: ks, line: line(new Chess(fen), n) };
  }
  return { n: null };
}
module.exports = { analyse, forced, keys };
if (require.main === module) {
  const t = Date.now();
  console.log(JSON.stringify(analyse(process.argv[2], +process.argv[3] || 3)), Date.now() - t, 'ms');
}
