# Heap Go Solver

A Python implementation of a Heap Go player developed for CMPUT 455 — Search and Planning in Artificial Intelligence at the University of Alberta.

Uses negamax search, alpha-beta pruning, and a transposition table to evaluate game positions under optimal play.

**Status:** Completed

## Overview

Heap Go Solver analyzes game positions to determine the winner assuming both players play optimally.

The solver evaluates possible moves using negamax search, with alpha-beta pruning and a transposition table to improve search efficiency. It also supports configurable time limits to handle computationally challenging positions.

The project explores adversarial search, game-state evaluation, and optimization techniques for solving strategic games.

## Technologies

- **Language:** Python 3
- **Algorithms:** Negamax search, alpha-beta pruning
- **Optimization:** Transposition table, move ordering
- **Concepts:** Game-tree search, optimal play, time-limited computation

## How It Works

### 1. Negamax Search

The solver evaluates possible moves by calculating the best achievable future score difference for the current player.

It recursively considers the opponent's best responses and selects moves that maximize the current player's eventual score advantage.

### 2. Alpha-Beta Pruning

Alpha-beta pruning eliminates branches that cannot improve the outcome of the current search.

This reduces the number of positions that need to be evaluated and helps the solver explore the game tree more efficiently.

### 3. Transposition Table

The solver caches previously evaluated game positions in a transposition table.

Equivalent positions are represented using sorted heaps, allowing the solver to reuse results when the same position is reached through different move sequences. Cached entries also store bounds on the evaluated score to support alpha-beta pruning.

### 4. Move Ordering

Legal moves are sorted by the points gained immediately, with higher-scoring moves explored first.

This helps alpha-beta pruning eliminate unnecessary branches earlier in the search.

### 5. Time-Limited Search

The solver supports configurable time limits for each search operation.

It periodically checks elapsed time and raises a timeout when the search exceeds its deadline. If the solver cannot complete its search in time, it does not report an unverified winner.

### 6. Computer Move Generation

The move-generation command uses the solver to find a winning move whenever possible.

If the current player cannot force a win, or the search times out, the solver falls back to a random legal move so that gameplay can continue.

## Key Features

- Evaluates Heap Go positions under optimal play
- Identifies winning moves when a winning strategy exists
- Uses negamax search with alpha-beta pruning
- Caches evaluated positions using a transposition table
- Improves search efficiency through move ordering
- Supports configurable search time limits
- Handles search timeouts without guessing the outcome
- Supports both Black and White as the current player

## Project Structure

```text
heap-go-solver/
└── a2.py    # Game logic, search algorithms, and command interface
```

## Example Workflow

1. Set up a Heap Go position.
2. Configure the search time limit.
3. Run the solver to evaluate the position.
4. Identify a winning move if the current player can force a win.
5. Generate a computer move using the solver or fall back to a random legal move when necessary.

## Current Limitations

- Search performance depends on the complexity of the game position and the available time.
- Difficult positions may exceed the configured time limit.
- When a search times out, the solver cannot guarantee that it has determined the correct outcome.

## What I Learned

- Implementing negamax search for adversarial games
- Using alpha-beta pruning to reduce search complexity
- Designing a transposition table to reuse search results
- Improving search performance through move ordering
- Managing time-limited recursive algorithms
- Evaluating game states using score differences and optimal play

---

*An educational project exploring adversarial search, search optimization, and algorithmic problem-solving.*
