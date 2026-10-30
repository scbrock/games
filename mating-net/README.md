# Mating Net

A chess tactics trainer for iPhone. It teaches a way of thinking, not just
answers: every puzzle comes with a coach that walks you through the same
routine strong players use, and a library of ideas explains what to look for
and how to apply it.

## What's inside

- **Puzzles at your level.** On first launch you pick your strength (or type your
  chess.com / Lichess rating). Puzzles are chosen near your rating, and an
  Elo-style rating moves up and down as you solve. A clean solve scores fully, a
  solve with a hint scores half, and a wrong move, Solution, or Skip is a miss.
- **The coach** ("Think it through"), under the board on every puzzle:
  1. What did their last move change? Shows new attacks and anything it left undefended.
  2. Checks, 3. Captures (undefended targets ringed in red), 4. Threats.
  5. Loose pieces on both sides and the enemy king's free squares.
  6. Candidate moves and how to calculate them.
  Each step has a Show button that marks the board and lists the moves.
- **Blunder check** (optional, in Progress → Settings): before each move is
  played you confirm it after asking "what are their checks and captures?".
- **Learn tab:**
  - *How to think*: the five-step routine and rules for calculating well.
  - *Tactics*: loose pieces, fork, pin, skewer, discovered attack, double check,
    sacrifice/decoy/deflection, back-rank weakness, promotion, quiet moves,
    removing the defender, the in-between move. Each has what it is, signs to
    look for, how to apply it, and a Practise button for puzzles of that type.
  - *Checkmates*: mating ideas plus 18 named patterns to practise.
  - *Strategy*: king safety, improving your worst piece, open files and outposts,
    pawn structure, prophylaxis, endgame basics.
- **After each puzzle:** an explanation of the idea, the move list, and "what to
  notice next time", linked to the matching idea in the library.
- **Progress tab:** rating graph, accuracy, streaks, accuracy by theme, a "Work on
  next" list of your weakest themes with Practise buttons, and settings.

## Where the puzzles come from

All puzzles are generated and checked by tools in `tools/`:

- **Checkmates** (`gen.js`, `classics.js`, `export.js`, `solve.js`): random
  attacking positions and hand-written classics, each proven by a brute-force mate
  solver to have a forced mate in the stated number of moves and, for mate in 2,
  exactly one correct first move.
- **Tactics** (`mine.js`, `engine.js`, `export2.js`): Stockfish plays itself at
  low depth so it makes realistic mistakes. When a move hands the opponent a
  winning shot, full-strength Stockfish checks that exactly one reply wins
  clearly (at least two pawns better than the alternatives), extends the line
  while each move stays the only good one, and keeps it only if it ends in mate
  or a real material gain. `export2.js` then detects the motif (fork, pin,
  skewer, discovered attack, double check, sacrifice, promotion, quiet move,
  loose piece, mate), estimates a difficulty rating and writes the explanation.

Puzzle ratings are estimates from line length and motif, not ratings measured
from thousands of players, so treat them as approximate.

`tools/build.py` embeds `tools/puzzles.json` into `src.html` to produce
`index.html`. To mine more (needs Node; run `npm install chess.js@0.10.3
stockfish@18.0.8` in `tools/`):

```
cd tools
node mine.js 900 low1.json 1 0 low          # repeat with different seeds
node export2.js puzzles-mates.json puzzles.json low*.json
python3 build.py
```

## On your iPhone

The app loads the chess rules library (chess.js) and fonts from public CDNs, so
it needs an internet connection. Open the GitHub Pages address in Safari and
tap **Share → Add to Home Screen**.
