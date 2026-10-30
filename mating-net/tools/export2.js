// Tag, rate and explain mined tactics; merge with the verified mate puzzles.
// Usage: node export2.js <mates.json> <out.json> <mined1.json> [mined2.json ...]
const { Chess } = require('chess.js');
const fs = require('fs');
const VAL = { p: 1, n: 3, b: 3, r: 5, q: 9, k: 100 };
const NAME = { p: 'pawn', n: 'knight', b: 'bishop', r: 'rook', q: 'queen', k: 'king' };
const F = 'abcdefgh';
const sq = (f, r) => F[f] + (r + 1);
const fr = (s) => [F.indexOf(s[0]), +s[1] - 1];
const STEPS = { n: [[1,2],[2,1],[2,-1],[1,-2],[-1,-2],[-2,-1],[-2,1],[-1,2]], k: [[1,0],[1,1],[0,1],[-1,1],[-1,0],[-1,-1],[0,-1],[1,-1]], b: [[1,1],[1,-1],[-1,1],[-1,-1]], r: [[1,0],[-1,0],[0,1],[0,-1]] };
STEPS.q = [...STEPS.b, ...STEPS.r];
const on = (x, y) => x >= 0 && x < 8 && y >= 0 && y < 8;
function attacks(g, s) {
  const p = g.get(s); if (!p) return [];
  const [f, r] = fr(s), out = [];
  if (p.type === 'p') { const dy = p.color === 'w' ? 1 : -1; for (const dx of [-1, 1]) if (on(f + dx, r + dy)) out.push(sq(f + dx, r + dy)); return out; }
  if (p.type === 'n' || p.type === 'k') { for (const [dx, dy] of STEPS[p.type]) if (on(f + dx, r + dy)) out.push(sq(f + dx, r + dy)); return out; }
  for (const [dx, dy] of STEPS[p.type]) { let x = f + dx, y = r + dy; while (on(x, y)) { const t = sq(x, y); out.push(t); if (g.get(t)) break; x += dx; y += dy; } }
  return out;
}
function pieces(g, color) { const out = []; for (let r = 0; r < 8; r++) for (let f = 0; f < 8; f++) { const s = sq(f, r), p = g.get(s); if (p && p.color === color) out.push([s, p]); } return out; }
const attackers = (g, s, color) => pieces(g, color).filter(([t]) => t !== s && attacks(g, t).includes(s));
const material = (g, color) => { let m = 0; for (const row of g.board()) for (const x of row) if (x && x.type !== 'k') m += (x.color === color ? 1 : -1) * VAL[x.type]; return m; };
const opp = (c) => (c === 'w' ? 'b' : 'w');

function analyse(p) {
  const g = new Chess(p.fen);
  if (p.setup && !g.move(p.setup)) return null;
  const player = g.turn();
  const start = material(g, player);
  const tags = new Set();
  const notes = {};
  let minMat = start;
  const moves = [];
  for (let i = 0; i < p.line.length; i++) {
    const before = new Chess(g.fen());
    const m = g.move(p.line[i]);
    if (!m) return null;
    moves.push(m);
    if (m.color !== player) { minMat = Math.min(minMat, material(g, player)); continue; }
    // Player move: look for motifs.
    const hits = attacks(g, m.to).map((s) => [s, g.get(s)]).filter(([, x]) => x && x.color !== player && (x.type === 'k' || VAL[x.type] >= 3));
    const valuable = hits.filter(([s, x]) => x.type === 'k' || VAL[x.type] > VAL[m.piece] || attackers(g, s, opp(player)).length === 0);
    if (hits.length >= 2 && valuable.length >= 1 && i < p.line.length - 1 && !notes.fork) { tags.add('Fork'); notes.fork = { m, targets: hits.map(([, x]) => NAME[x.type]) }; }
    if ('bqr'.includes(m.piece)) {
      for (const [dx, dy] of STEPS[m.piece]) {
        let [x, y] = fr(m.to); x += dx; y += dy;
        const line = [];
        while (on(x, y) && line.length < 2) { const t = g.get(sq(x, y)); if (t) { if (t.color === player) break; line.push([sq(x, y), t]); } x += dx; y += dy; }
        if (line.length === 2) {
          const [[s1, a], [s2, b]] = line;
          if (a.type !== 'k' && VAL[b.type] > VAL[a.type] && VAL[b.type] >= 5 && !notes.pin) { tags.add('Pin'); notes.pin = { m, front: NAME[a.type], back: NAME[b.type] }; }
          if ((a.type === 'k' || a.type === 'q') && VAL[b.type] >= 3 && VAL[a.type] > VAL[b.type] && p.line.slice(i + 1).some((san) => san.includes('x' + s2)) && !notes.skewer) { tags.add('Skewer'); notes.skewer = { m, front: NAME[a.type], back: NAME[b.type] }; }
        }
      }
    }
    // Discovered attack: another of our sliders now hits something it didn't before.
    for (const [s, x] of pieces(g, player)) {
      if (s === m.to || !'bqr'.includes(x.type)) continue;
      const was = new Set(attacks(before, s));
      const now = attacks(g, s).filter((t) => !was.has(t)).map((t) => [t, g.get(t)]).filter(([, y]) => y && y.color !== player && (y.type === 'k' || VAL[y.type] >= 3));
      if (now.length && !notes.disc) { tags.add('Discovered attack'); notes.disc = { m, by: NAME[x.type], target: NAME[now[0][1].type] }; }
    }
    if (g.in_check()) {
      const k = pieces(g, opp(player)).find(([, x]) => x.type === 'k')[0];
      if (attackers(g, k, player).length >= 2) tags.add('Double check');
    }
    if (m.promotion) tags.add('Promotion');
  }
  const first = moves[0];
  const g0 = new Chess(p.fen); if (p.setup) g0.move(p.setup);
  const mated = g.in_checkmate();
  const pm = Math.ceil(p.line.length / 2);
  if (mated) {
    tags.add('Mate in ' + Math.min(pm, 3));
    const last = moves[moves.length - 1];
    const k = pieces(g, opp(player)).find(([, x]) => x.type === 'k')[0];
    const back = opp(player) === 'b' ? '8' : '1';
    if (k[1] === back && 'rq'.includes(last.piece) && last.to[1] === back) tags.add('Back rank');
  }
  if (minMat <= start - 2 && p.line.length >= 3) tags.add('Sacrifice');
  if (!first.captured && !first.san.includes('+') && !first.promotion && !mated) tags.add('Quiet move');
  const firstHanging = first.captured && attackers(g0, first.to, opp(player)).length === 0;
  if (p.line.length === 1 && firstHanging) tags.add('Hanging piece');
  const forcing = g0.moves().filter((x) => /[x+#]/.test(x)).length;

  let rating = 620 + 280 * (pm - 1) + Math.min(forcing, 12) * 12;
  if (tags.has('Quiet move')) rating += 260;
  if (tags.has('Sacrifice')) rating += 200;
  if (tags.has('Hanging piece')) rating -= 140;
  if (first.captured && !firstHanging) rating += 130;
  if (['Fork', 'Pin', 'Skewer', 'Discovered attack', 'Double check'].some((t) => tags.has(t))) rating += 90;
  if (mated) rating += pm >= 2 ? 120 : -40;
  rating = Math.max(400, Math.min(2400, Math.round(rating / 10) * 10));

  // Explanation in plain words.
  const them = player === 'w' ? 'Black' : 'White';
  const key = first.san, rest = p.line.slice(1);
  const gain = material(g, player) - start;
  let idea;
  if (mated) idea = p.line.length === 1 ? `${key} is checkmate.` : `${key} starts a forced mate: ${p.line.join(' ')}.`;
  else if (tags.has('Hanging piece')) idea = `${key} takes the ${NAME[first.captured]} for free. Nothing defended it after ${p.setup}.`;
  else if (notes.fork) {
    const t = notes.fork.targets.filter((x) => x !== 'king');
    idea = notes.fork.m.san.includes('+')
      ? `${notes.fork.m.san} gives check and attacks the ${t.slice(0, 2).join(' and the ')} at the same time. ${them} must deal with the check first.`
      : `${notes.fork.m.san} attacks the ${t.slice(0, 2).join(' and the ')} at once. ${them} can only save one.`;
  }
  else if (notes.skewer) idea = `${notes.skewer.m.san} attacks the ${notes.skewer.front}. When it moves, the ${notes.skewer.back} behind it falls.`;
  else if (notes.pin) idea = `${notes.pin.m.san} pins the ${notes.pin.front} to the ${notes.pin.back}. It can't move without losing more.`;
  else if (notes.disc) idea = `${notes.disc.m.san} gets out of the way and uncovers your ${notes.disc.by}'s attack on the ${notes.disc.target}.`;
  else if (tags.has('Sacrifice')) idea = `${key} gives up material on purpose. ${rest.length ? `After ${rest[0]}, ` : ''}you win it back with interest.`;
  else if (tags.has('Quiet move')) idea = `${key} isn't a check or a capture, but it creates a threat ${them} can't meet.`;
  else if (first.captured) idea = `${key} wins the ${NAME[first.captured]}. Count it out: the recapture doesn't work for ${them}.`;
  else idea = `${key} is the only move that wins material.`;
  if (!mated && gain >= 2 && !tags.has('Hanging piece')) idea += ` You come out ${gain} point${gain > 1 ? 's' : ''} of material ahead.`;
  return { tags: [...tags], rating, idea };
}

const [matesFile, outFile, ...mined] = process.argv.slice(2);
const mates = JSON.parse(fs.readFileSync(matesFile));
const seen = new Set(mates.map((p) => p.fen.split(' ').slice(0, 2).join(' ')));
let cand = [];
for (const f of mined) for (const p of JSON.parse(fs.readFileSync(f))) cand.push(p);
const out = [...mates];
let id = 0, trivial = 0;
const TRIVIAL_CAP = +(process.env.TRIVIAL_CAP || 110);
for (const p of cand) {
  const k = p.fen.split(' ').slice(0, 2).join(' ');
  if (seen.has(k)) continue;
  seen.add(k);
  const a = analyse(p);
  if (!a) { console.log('bad line', p.fen); continue; }
  if (a.tags.includes('Hanging piece')) { if (trivial >= TRIVIAL_CAP) continue; trivial++; }
  out.push({ id: 't' + (++id), fen: p.fen, setup: p.setup, line: p.line, rating: a.rating, tags: a.tags, idea: a.idea });
}
out.sort((a, b) => a.rating - b.rating);
fs.writeFileSync(outFile, JSON.stringify(out));
const by = {}; for (const p of out) for (const t of p.tags) by[t] = (by[t] || 0) + 1;
const hist = {}; for (const p of out) { const b = Math.floor(p.rating / 200) * 200; hist[b] = (hist[b] || 0) + 1; }
console.log('total', out.length, 'mined kept', id, 'trivial', trivial);
console.log(JSON.stringify(by));
console.log('ratings', JSON.stringify(hist));
