# Doubles

A 2048-style sliding-tile puzzle built for iPhone. It's one HTML file with no
build step and no dependencies.

**How to play:** swipe to slide every tile in that direction. Two tiles with the
same number merge into one with double the value. Reach 2048 to win, then keep
going if you like. Undo takes back one move. Your game and best score are saved
on the device.

## Play it on your iPhone

1. Host this folder anywhere that serves static files. With GitHub Pages:
   repo **Settings → Pages → Deploy from a branch**, pick the branch and
   `/ (root)`, then open `https://<user>.github.io/games/doubles/`.
2. Open the page in Safari, tap **Share → Add to Home Screen**.
3. Launch it from the Home Screen icon. It runs full screen like an app.

## Run it locally

Open `index.html` in any browser. Arrow keys or WASD work on a keyboard, and
you can drag with the mouse to swipe.

## Files

- `index.html`: the whole game (markup, styles, logic)
- `manifest.webmanifest`, `icon-180.png`: Home Screen name and icon
