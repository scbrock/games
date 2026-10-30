const { analyse } = require('./solve.js');
const { Chess } = require('chess.js');
const C = [
  ["Back-rank mate", "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1", "The king is trapped behind its own pawns. A rook on the back rank finishes it."],
  ["Smothered mate", "6rk/6pp/8/6N1/8/8/8/6K1 w - - 0 1", "The king is boxed in by its own pieces, so a lone knight is enough."],
  ["Anastasia's mate", "8/4Nppk/8/8/8/R7/8/6K1 w - - 0 1", "The knight on e7 seals g8 and g6. The rook delivers mate down the open h-file."],
  ["Scholar's mate", "r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4", "f7 is defended only by the king early in the game. Queen and bishop hit it together."],
  ["Fool's mate", "rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq - 0 2", "White weakened the e1-h4 diagonal. The fastest mate in chess."],
  ["Arabian mate", "7k/1R6/5N2/8/8/8/8/6K1 w - - 0 1", "Rook and knight work together in the corner: the knight guards the rook and covers g8."],
  ["Lolli's mate", "5rk1/5p1p/5PpQ/8/8/8/6PP/6K1 w - - 0 1", "A pawn on f6 supports the queen on g7, right next to the king."],
  ["Epaulette mate", "3rkr2/8/8/8/8/1Q6/8/6K1 w - - 0 1", "The king's own rooks sit on its shoulders and block its escape."],
  ["Corridor mate", "1k6/ppp5/8/8/8/8/8/K5R1 w - - 0 1", "The pawns form a wall. One check along the open rank is mate."],
  ["Back-rank mate (as Black)", "3r2k1/8/8/8/8/8/5PPP/6K1 b - - 0 1", "Same idea from the other side: White never made an escape square for the king."],
  ["Boden's mate", "2kr4/p2n4/8/8/5B2/8/4B3/6K1 w - - 0 1", "Two bishops on crossing diagonals trap a castled king."],
  ["Opera mate", "4kb2/5p2/8/6B1/8/8/8/3R2K1 w - - 0 1", "Rook on the back rank, protected by the bishop. Named after Morphy's famous game at the Paris opera."],
  ["Knight's corner mate (as Black)", "6k1/8/8/8/8/4n3/PP6/KR6 b - - 0 1", "A king cornered behind its own pieces can't escape a knight check."],
  ["Philidor's legacy", "r6k/6pp/7N/8/2Q5/8/6PP/6K1 w - - 0 1", "Sacrifice the queen to force the rook onto g8, then the knight smothers the king."],
  ["Anastasia's sacrifice", "5r1k/4Nppp/8/7Q/8/R7/8/6K1 w - - 0 1", "Give up the queen to drag the king onto the open h-file."],
  ["Doubled rooks", "2r3k1/5ppp/8/8/8/8/3R1PPP/3R2K1 w - - 0 1", "Two rooks beat one defender on the back rank: the first is captured, the second mates."],
  ["Lawnmower", "6k1/8/8/8/8/8/R7/1R4K1 w - - 0 1", "Rooks take turns cutting off ranks until the king runs out of room."],
  ["Damiano's mate", "5rk1/6p1/6P1/7Q/8/8/8/6K1 w - - 0 1", "The pawn on g6 supports the queen, so it can land right next to the king."],
  ["Rook roller (as Black)", "6k1/r7/1r6/8/8/8/5PPP/6K1 b - - 0 1", "Rooks working on adjacent ranks drive the king to the edge."],
];
const out = [];
for (const [name, fen, idea] of C) {
  const t = Date.now();
  const r = analyse(fen, 3);
  console.log(name.padEnd(30), r.error || (r.n ? `mate in ${r.n} keys=${r.keys.join(',')} line=${(r.line || []).join(' ')}` : 'NO MATE <=3'), Date.now() - t + 'ms');
  if (r.n && (r.n === 1 || r.keys.length === 1)) out.push({ name, fen, idea, n: r.n, line: r.line, keys: r.keys });
}
require('fs').writeFileSync('classics.json', JSON.stringify(out));
console.log('kept', out.length, 'of', C.length);
