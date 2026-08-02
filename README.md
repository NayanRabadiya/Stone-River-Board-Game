# Stones and Rivers — AI Game Agent

An AI agent for the Stones and Rivers board game.

## Game Overview

Stones and Rivers is a two-player strategy board game played on a **13 × 12 grid**. The two players are **Circle** and **Square**. Each player starts with 12 stones arranged in two rows near their own end of the board and tries to advance them to the opponent's scoring area.

### Board Layout

```
Row  2        [ scoring area — 4 centre cols ]   ← Circle scores here
Row  3–4      [ Square's starting stones       ]
     …
Row  8–9      [ Circle's starting stones       ]
Row 10        [ scoring area — 4 centre cols ]   ← Square scores here
```



- The **scoring area** is the 4 centre columns of the designated row (cols 4–7 on a 12-wide board).
- Players move *toward* the opponent's end — Circle moves up, Square moves down.

### Piece Types

| Piece | Description |
|-------|-------------|
| **Stone** | Standard piece. Moves one step at a time. |
| **River** | A flipped stone with a *horizontal* or *vertical* orientation. Acts as a conduit — pieces entering it travel along its direction. |

### Actions (one per turn)

| Action | Who can do it | Description |
|--------|--------------|-------------|
| **Move** | Any piece | Move one step (up/down/left/right) into an empty cell. If the adjacent cell holds a river, the piece flows along the river network and lands at the first empty cell reachable via connected rivers. |
| **Push** | Stone → Stone | Push an adjacent stone one step further in the same direction. The destination cell must be empty. |
| **River push** | River → Stone | A river piece pushes an adjacent stone; the stone is carried through the river's flow network to any reachable empty cell. |
| **Flip** | Any piece | Toggle between stone and river. Stone → River requires choosing an orientation (H or V). River → Stone removes orientation. |
| **Rotate** | River only | Switch orientation between horizontal and vertical. |

### Movement & Flow Rules

- **River flow**: when a piece enters a river cell it keeps travelling in the river's orientation direction, jumping across connected rivers, until it reaches an empty cell.
- **Rivers cannot push rivers.**
- **Blocked flow**: a river's flow stops at any stone or board edge.

### Restrictions

- A piece **cannot enter the opponent's scoring area** directly (by move, push, or flow).
- A push or river-push **cannot land the pushed piece in its own opponent's scoring area**.
- **Flip/Rotate is forbidden** if the resulting river orientation would create a flow path into the opponent's scoring area.

### Win Condition

The first player to place **4 stones** (stone side up, not rivers) in the opponent's scoring row wins.

### Scoring (timed games)

| Outcome | Winner's score | Loser's score |
|---------|---------------|--------------|
| Win | `100 − (n + m/10)` | `n + m/10` |
| Draw | `30 + MarginScore/4` each | — |

Where *n* = opponent's stones already in scoring area, *m* = opponent's stones reachable in one move. Running out of time is a loss.

## Project Structure

```
A2/
├── gameEngine.py       # Game engine — runs locally with GUI or CLI
├── agent.py            # Baseline random agent
├── student_agent.py    # Custom AI agent (implemented)
├── saved_board.json    # Saved board state for testing
├── requirements.txt    # Python dependencies
```

## Tech Stack

- **Language**: Python 3.9
- **Libraries**: Pygame, NumPy, SciPy

## Setup

```bash
# Option A — conda
conda create --name stones_river python=3.9
conda activate stones_river
pip install -r requirements.txt

# Option B — venv
py -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt
```

## Run

```bash
# Human vs Human
python gameEngine.py --mode hvh

# Human vs AI (random agent plays circle)
python gameEngine.py --mode hvai --circle random

# AI vs AI — random vs student agent (5s time limit)
python gameEngine.py --mode aivai --circle random --square student --time 5

# AI vs AI — student vs student
python gameEngine.py --mode aivai --circle student --square student2 --time 5

# Headless mode (no GUI)
python gameEngine.py --mode aivai --circle random --square student --nogui
```

## Agent Implementation

The custom agent is in [student_agent.py](student_agent.py). The game engine calls `StudentAgent.choose()` each turn.

**Algorithm: Minimax with heuristic move pruning**

- `get_best_move` / `maxValue` — depth-1 minimax search
- `generate_heuristic_moves` — prunes the move space into top-N candidates, split across move/push and flip/rotate categories
- `evaluate_simple` — weighted linear evaluation over 14 board features:
  - Stones/rivers in own scoring area
  - Opponent stones/rivers in their scoring area
  - Row and column distance of all pieces to goal
  - Pieces adjacent to rivers (flow opportunity)
  - River placement beside the goal row
  - Flow reachability into the goal area
- `historyqueue` — tracks the last 4 moves to avoid immediate repetition

The baseline random agent is in [agent.py](agent.py).

