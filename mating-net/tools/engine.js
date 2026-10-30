// Promise wrapper around the stockfish npm package (Stockfish 18, WASM).
const init = require('stockfish');
class Engine {
  async start(flavor = 'lite-single') {
    this.e = await init(flavor);
    this.waiter = null;
    this.e.listener = (line) => { if (this.waiter) this.waiter(line); };
    await this.cmd('uci', (l) => l === 'uciok');
    await this.cmd('setoption name Hash value 32');
    await this.ready();
    return this;
  }
  cmd(c, until) {
    if (!until) { this.e.sendCommand(c); return Promise.resolve(); }
    return new Promise((res) => {
      const lines = [];
      this.waiter = (l) => { lines.push(l); if (until(l)) { this.waiter = null; res(lines); } };
      this.e.sendCommand(c);
    });
  }
  ready() { return this.cmd('isready', (l) => l === 'readyok'); }
  // Scores are from the side to move: {move, cp, mate, pv} best first.
  async analyse(fen, depth = 12, multipv = 1) {
    await this.cmd(`setoption name MultiPV value ${multipv}`);
    await this.cmd(`position fen ${fen}`);
    const lines = await this.cmd(`go depth ${depth}`, (l) => l.startsWith('bestmove'));
    const best = {};
    for (const l of lines) {
      if (!l.startsWith('info') || !l.includes(' pv ') || / (lower|upper)bound/.test(l)) continue;
      const mp = +(l.match(/ multipv (\d+)/)?.[1] || 1), d = +(l.match(/ depth (\d+)/)[1]);
      const cp = l.match(/ score cp (-?\d+)/), mate = l.match(/ score mate (-?\d+)/);
      const pv = l.split(' pv ')[1].trim().split(' ');
      if (!best[mp] || best[mp].depth <= d) best[mp] = { depth: d, cp: cp ? +cp[1] : null, mate: mate ? +mate[1] : null, pv, move: pv[0] };
    }
    const bm = lines[lines.length - 1].split(' ')[1];
    const out = Object.keys(best).sort((a, b) => a - b).map((k) => best[k]);
    if (!out.length && bm && bm !== '(none)') out.push({ move: bm, cp: 0, mate: null, pv: [bm] });
    return out;
  }
}
// A single comparable number from the mover's view; mates dominate.
const score = (r) => r == null ? -99999 : r.mate != null ? (r.mate > 0 ? 100000 - r.mate * 100 : -100000 - r.mate * 100) : r.cp;
module.exports = { Engine, score };
