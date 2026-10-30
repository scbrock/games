// Mine tactics puzzles from engine self-play with deliberate mistakes.
// Usage: node mine.js <seconds> <out.json> <seed>
const { Chess } = require('chess.js');
const { Engine, score } = require('./engine.js');
const fs = require('fs');
const VAL = { p: 1, n: 3, b: 3, r: 5, q: 9, k: 0 };
let seed = +(process.argv[4] || 1) * 7919;
const rand = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647; };
const uciMove = (c, u) => c.move({ from: u.slice(0, 2), to: u.slice(2, 4), promotion: u[4] });
const material = (c, color) => { let s = 0; for (const row of c.board()) for (const x of row) if (x) s += (x.color === color ? 1 : -1) * VAL[x.type]; return s; };

(async () => {
  const E = await new Engine().start();
  const deadline = Date.now() + (+process.argv[2] || 600) * 1000;
  const out = [];
  let games = 0;
  while (Date.now() < deadline) {
    games++;
    const c = new Chess();
    let prevEval = 0; // from the side to move
    for (let ply = 0; ply < 140 && !c.game_over() && Date.now() < deadline; ply++) {
      const fen0 = c.fen();
      // Choose a move: varied opening, then mostly decent moves with occasional mistakes.
      const shallow = process.argv[6] === 'low';
      const cands = await E.analyse(fen0, ply < 8 ? 4 : shallow ? 2 + Math.floor(rand() * 3) : 7, ply < 8 ? 5 : shallow ? 3 : 4);
      if (!cands.length) break;
      let pick;
      const blunderRate = +(process.argv[5] || 0.1);
      if (ply >= 8 && rand() < blunderRate) {
        const legal = c.moves({ verbose: true });
        pick = legal[Math.floor(rand() * legal.length)];
        pick = pick.from + pick.to + (pick.promotion || '');
      } else {
        const b = score(cands[0]);
        const w = cands.map((x) => Math.exp((score(x) - b) / (ply < 8 ? 60 : shallow ? 25 : 45)));
        let r = rand() * w.reduce((a, x) => a + x, 0), i = 0;
        while ((r -= w[i]) > 0 && i < w.length - 1) i++;
        pick = cands[i].move;
      }
      const before = score(cands[0]);
      const m = uciMove(c, pick);
      if (!m) break;
      if (c.game_over()) break;
      // Did that move hand the opponent a big, single winning reply?
      const quick = await E.analyse(c.fen(), 9, 1);
      const gain = score(quick[0]);
      if (gain >= 250 && before >= -120 && gain + before >= 300 && Math.abs(gain) < 200000) {
        const p = await buildPuzzle(E, fen0, m, c.fen());
        if (p) { out.push(p); fs.writeFileSync(process.argv[3], JSON.stringify(out)); }
      }
      prevEval = gain;
    }
  }
  console.log('games', games, 'puzzles', out.length);
  process.exit(0);
})();

async function buildPuzzle(E, fen0, setup, fen1) {
  const c = new Chess(fen1);
  const player = c.turn();
  const startMat = material(c, player);
  const line = [];
  const depthFound = [];
  for (let step = 0; step < 4; step++) {
    const res = await E.analyse(c.fen(), 16, 2);
    if (!res.length) break;
    const [b, s] = res;
    const sb = score(b), ss = s ? score(s) : -99999;
    const unique = b.mate != null && b.mate > 0
      ? !(s && s.mate != null && s.mate > 0 && s.mate <= b.mate + 1)
      : sb >= 200 && ss <= sb - 220 && ss < 250;
    if (!unique) break;
    // How shallow a search finds it: a rough difficulty signal.
    let found = 16;
    if (step === 0) for (const d of [1, 2, 3, 4, 6, 8, 10, 12]) { const r = await E.analyse(c.fen(), d, 1); if (r[0] && r[0].move === b.move) { found = d; break; } }
    depthFound.push(found);
    const pm = uciMove(c, b.move);
    line.push(pm);
    if (c.in_checkmate() || c.game_over()) break;
    const rr = await E.analyse(c.fen(), 14, 1);
    if (!rr.length) break;
    line.push(uciMove(c, rr[0].move));
    if (c.game_over()) break;
  }
  // Must end on the solver's move.
  while (line.length && line.length % 2 === 0) line.pop();
  // Trim to the last move that converts: capture, promotion or mate.
  while (line.length > 1) {
    const last = line[line.length - 1];
    if (last.captured || last.promotion || last.san.includes('#')) break;
    line.splice(-2, 2);
  }
  if (!line.length) return null;
  const c2 = new Chess(fen1);
  for (const m of line) c2.move(m.san);
  const mated = c2.in_checkmate();
  const gainMat = material(c2, player) - startMat;
  if (!mated && gainMat < 2) return null;
  if (!mated) {
    const fin = await E.analyse(c2.fen(), 14, 1);
    if (!fin.length || -score(fin[0]) < 150) return null; // opponent to move; must still be clearly winning
  }
  return { fen: fen0, setup: setup.san, line: line.map((m) => m.san), depth: depthFound[0], gain: mated ? 99 : gainMat };
}
