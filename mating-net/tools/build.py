"""Embed tools/puzzles.json into src.html to produce index.html."""
import json, pathlib
here = pathlib.Path(__file__).resolve().parent.parent
src = (here / "src.html").read_text()
puzzles = json.loads((here / "tools" / "puzzles.json").read_text())
assert src.count("/*PUZZLES*/[]") == 1
(here / "index.html").write_text(src.replace("/*PUZZLES*/[]", json.dumps(puzzles, separators=(",", ":"), ensure_ascii=False)))
print(f"Built index.html with {len(puzzles)} puzzles")
