# Mating Net

A chess puzzle trainer for iPhone that teaches you to spot checkmates.
172 puzzles: mate in 1 and mate in 2, about a third of them played as Black,
plus 18 named classic patterns (back-rank, smothered, Anastasia's, Arabian,
Boden's, Opera, Epaulette, Philidor's legacy and more).

## How it helps you improve

- **Adaptive rating.** You start at 1000. Each puzzle has a difficulty rating,
  and the next puzzle is picked close to your rating, so it gets harder as you
  get better. Solving cleanly scores full points; solving with a hint scores
  half; a wrong move, Solution, or Skip counts as a miss.
- **Learn from every puzzle.** After each one you get a short explanation of the
  idea (the sacrifice, the back-rank weakness, the smothered king) and the full
  move list.
- **Any winning move counts.** If you find a different forced mate than the
  stored one, the app checks it with its own mate search and accepts it, and
  your opponent always plays the most stubborn defence.
- **Patterns tab** to practise the classic named mates without affecting your
  rating.
- **Stats tab** with your rating graph, accuracy, streaks, accuracy by theme,
  and recent results. Progress is saved on the device.

Move by tapping a piece and then a square, or by dragging. Hint highlights the
piece to move, a second hint shows the square.

## Puzzle quality

Every puzzle is verified by a brute-force mate solver (`tools/solve.js`): the
mate exists, takes exactly the stated number of moves, and (for mate in 2) has
exactly one correct first move. `tools/gen.js` generates candidate positions,
`tools/classics.js` checks the hand-written classics, `tools/export.js` tags,
rates, explains and flips puzzles into `tools/puzzles.json`, and
`tools/build.py` embeds them into `src.html` to produce `index.html`.

To regenerate (needs Node and `npm install chess.js@0.10.3` in `tools/`):

```
cd tools
node gen.js 420 40 45 g1.json && node gen.js 420 40 45 g2.json
node classics.js && node export.js
python3 build.py
```

## On your iPhone

The app loads the chess rules library (chess.js) and fonts from public CDNs, so
it needs an internet connection. Host this folder on any static host (for
example GitHub Pages, then `https://<user>.github.io/games/mating-net/`), open
it in Safari and tap **Share → Add to Home Screen**.
