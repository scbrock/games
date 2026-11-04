# Skunk Line

Multiplayer cribbage for 2 to 6 players, each on their own phone. It runs as a
Claude artifact page: the shared game state lives in the artifact's database
and every phone updates live.

Play it: https://claude.ai/artifact/TkCC5yXayaRrgCQKA7CfwB

## Inviting players

Open the page, tap **Share**, and invite each player by email as an **Editor**.
People outside your Claude account can only *watch* unless they're Editors, and
Editor access only works while the page is not also shared by a public link.
Each player signs in with a free Claude account, opens the link, types a name
and taps **Join**. The first person to join starts the game.

## Rules as implemented

- 2 players: 6 cards each, throw 2. 3 players: 5 each, throw 1, plus one card
  from the deck to the crib. 4 players: 5 each, throw 1. 5 players: the dealer
  gets 4, the others 5 and throw 1. 6 players: the dealer and the player before
  them get 4, the others 5 and throw 1. Every hand and the crib end at 4 cards.
- Partnerships are optional with 4 or 6 players (partners sit alternately and
  share a peg).
- Pegging: 15 and 31 for 2, pairs 2/6/12, runs, go and last card. Show:
  fifteens, pairs, runs, flush (crib needs 5), nobs; his heels at the cut.
- First to 121 wins the moment they reach it; skunks under 91 and 61 are called
  out at the end. Scoring is automatic (no muggins).

All hands are stored in the shared game record, so this is built for friendly
games: someone determined could read other hands with developer tools.

This file is the artifact source (no `<html>` wrapper); it only works when
served as a Claude artifact, not from GitHub Pages.
