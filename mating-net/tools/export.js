const { Chess } = require('chess.js');
const { analyse } = require('./solve.js');
const fs = require('fs');
const NAMES = { p: 'pawn', n: 'knight', b: 'bishop', r: 'rook', q: 'queen', k: 'king' };
const VAL = { p: 1, n: 3, b: 3, r: 5, q: 9, k: 0 };

function legal(fen) {
  const c = new Chess(); if (!c.load(fen) || c.in_check() || c.game_over()) return false;
  const p = fen.split(' '); p[1] = p[1] === 'w' ? 'b' : 'w';
  const d = new Chess(); return d.load(p.join(' ')) && !d.in_check();
}
// Mirror the board top-to-bottom and swap colours, so White's puzzle becomes Black's.
function flip(fen) {
  const [board, turn] = fen.split(' ');
  const rows = board.split('/').reverse().map((r) => [...r].map((ch) => /[a-z]/.test(ch) ? ch.toUpperCase() : /[A-Z]/.test(ch) ? ch.toLowerCase() : ch).join(''));
  return `${rows.join('/')} ${turn === 'w' ? 'b' : 'w'} - - 0 1`;
}
function describe(fen, line) {
  const c = new Chess(fen);
  const side = c.turn();
  const tags = new Set();
  const moves = [];
  for (const san of line) moves.push(c.move(san));
  const key = moves[0], mate = moves[moves.length - 1];
  // Board after mate: inspect the mated king.
  const board = c.board();
  let kr, kf;
  board.forEach((row, r) => row.forEach((x, f) => { if (x && x.type === 'k' && x.color !== side) { kr = r; kf = f; } }));
  const backRow = side === 'w' ? 0 : 7;
  if (kr === backRow && (mate.piece === 'r' || mate.piece === 'q') && mate.to[1] === (side === 'w' ? '8' : '1')) tags.add('Back rank');
  if (mate.piece === 'n') {
    let boxed = true;
    for (let dr = -1; dr <= 1; dr++) for (let df = -1; df <= 1; df++) {
      if (!dr && !df) continue;
      const r = kr + dr, f = kf + df;
      if (r < 0 || r > 7 || f < 0 || f > 7) continue;
      const x = board[r][f];
      if (!x || x.color === side) boxed = false;
    }
    if (boxed) tags.add('Smothered');
  }
  if (line.length === 1) tags.add('Mate in 1'); else tags.add('Mate in ' + Math.ceil(line.length / 2));
  const reply = moves[1];
  const sac = reply && reply.to === key.to && reply.captured && VAL[key.piece] >= 3;
  if (sac) tags.add('Sacrifice');
  if (!key.san.includes('+') && !key.san.includes('#') && !key.captured) tags.add('Quiet move');
  tags.add(NAMES[mate.piece][0].toUpperCase() + NAMES[mate.piece].slice(1) + ' mate');

  // Count distracting checks in the start position.
  const s = new Chess(fen);
  const checks = s.moves().filter((m) => m.includes('+') || m.includes('#')).length;
  let rating;
  if (line.length === 1) rating = 700 + (key.captured ? 0 : 80) + Math.min(checks, 6) * 45 + (tags.has('Quiet move') ? 150 : 0);
  else rating = 1200 + (sac ? 160 : 0) + (tags.has('Quiet move') ? 260 : 0) + Math.min(checks, 8) * 25 + (key.piece === 'q' && sac ? 60 : 0);

  const them = side === 'w' ? 'Black' : 'White';
  let idea;
  if (line.length === 1) {
    idea = `${mate.san} is mate. ` + (tags.has('Smothered') ? "The king is surrounded by its own pieces, so the knight can't be stopped." :
      tags.has('Back rank') ? 'The king is stuck on the back rank behind its own pieces.' :
      `Check every square around the king: the ${NAMES[mate.piece]} and its helpers cover them all.`);
  } else if (sac) {
    idea = `${key.san} sacrifices the ${NAMES[key.piece]}. After ${reply.san}, ${them} has pulled a defender out of position and ${mate.san} is mate.`;
  } else if (tags.has('Quiet move')) {
    idea = `${key.san} is a quiet move with no check, but it threatens mate in more than one way. ${them} can't cover everything, and ${mate.san} follows.`;
  } else {
    idea = `${key.san} forces ${reply.san}. Now ${mate.san} is mate.`;
  }
  return { tags: [...tags], rating: Math.round(rating / 10) * 10, idea };
}

const classics = JSON.parse(fs.readFileSync('classics.json'));
const gen = [...JSON.parse(fs.readFileSync('g1.json')), ...JSON.parse(fs.readFileSync('g2.json'))];
const seen = new Set();
const out = [];
let id = 0;
for (const p of classics) {
  if (!legal(p.fen)) { console.log('ILLEGAL classic', p.name); continue; }
  if (p.name === 'Hook mate') continue;
  const d = describe(p.fen, p.line);
  out.push({ id: 'c' + (++id), fen: p.fen, line: p.line, name: p.name, idea: p.idea, tags: ['Classic', ...d.tags], rating: Math.min(d.rating, p.line.length === 1 ? 900 : 1350) });
  seen.add(p.fen.split(' ')[0]);
}
let g = 0, flipped = 0;
for (const p of gen) {
  const board = p.fen.split(' ')[0];
  if (seen.has(board)) continue;
  seen.add(board);
  let fen = p.fen;
  // Turn about 40% into Black-to-move puzzles.
  if (g % 5 === 1 || g % 5 === 3) { fen = flip(fen); flipped++; }
  if (!legal(fen)) { console.log('illegal gen', fen); continue; }
  const a = analyse(fen, p.n);
  if (a.n !== p.n || !a.line || (p.n > 1 && a.keys.length !== 1)) { console.log('reject', fen, JSON.stringify(a)); continue; }
  const d = describe(fen, a.line);
  out.push({ id: 'g' + (++g), fen, line: a.line, idea: d.idea, tags: d.tags, rating: d.rating });
}
out.sort((a, b) => a.rating - b.rating);
fs.writeFileSync('puzzles.json', JSON.stringify(out));
const by = {};
for (const p of out) for (const t of p.tags) by[t] = (by[t] || 0) + 1;
console.log('total', out.length, 'flipped', flipped, JSON.stringify(by));
console.log('ratings', out[0].rating, '…', out[out.length - 1].rating);
