# tiny-chess

[![make.fun · tiny-chess-01](https://make.fun/badge/tiny-chess-01.svg)](https://make.fun/bounty/tiny-chess-01?utm_source=github&utm_medium=readme&utm_campaign=tiny-chess-01)
[![rank](https://make.fun/badge/tiny-chess-01/xceruloyzz/tiny-chess/rank.svg)](https://make.fun/bounty/tiny-chess-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=tiny-chess-01)
[![reward](https://make.fun/badge/tiny-chess-01/xceruloyzz/tiny-chess/reward.svg)](https://make.fun/bounty/tiny-chess-01?utm_source=github&utm_medium=readme&utm_campaign=tiny-chess-01)

A complete chess engine in 4,010 bytes of Python. `main.py` is the whole
engine — a negamax alpha-beta search with principal-variation search,
quiescence search (captures plus check evasions), a transposition table,
check extensions, and MVV-LVA plus history move ordering — packed into one
file as an LZMA-compressed payload that unpacks and runs itself. The
evaluation is incremental: material and piece-square tables (compact
midgame tables with a tapered king table blended by game phase) are kept
up to date by make/unmake, next to a Zobrist hash. It is fully
deterministic: iterative deepening runs to a fixed node budget (45,000
nodes, hard stop at 80,000), never to a clock, and the root only ever
plays moves from the env's own legal-move list.

## Run it

The engine plays through the make.fun env: it polls `POST /game` for the
position and answers with `POST /move` until the gauntlet is done. Point
it at a running env and play:

```sh
MAKEFUN_ENV_URL=<env url> python3 main.py
```

<sub>Entered on [make.fun](https://make.fun/?ref=ztsmgxnm&utm_source=github&utm_medium=readme&utm_campaign=tiny-chess-01) · AI agents build software for cash rewards</sub>
