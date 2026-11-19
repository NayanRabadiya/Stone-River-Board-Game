# Stones and Rivers — Adversarial Game-Playing Agent

This project implements a bot for **Stones and Rivers**, a two-player abstract
strategy game played on a 13×12 grid, together with the reference game engine
used to run and referee matches (`gameEngine.py`), a shared agent framework
(`agent.py`), and the student-written bot (`student.py`). The game and
scoring rules follow the course specification in `A2.pdf`; this document
describes what is actually implemented in the code, not the specification in
the abstract.

## Game Rules as Implemented

- **Board.** `gameEngine.py` defines `DEFAULT_ROWS = 13`, `DEFAULT_COLS = 12`.
  Each cell holds at most one `Piece(owner, side, orientation)`, where
  `owner ∈ {"circle", "square"}`, `side ∈ {"stone", "river"}`, and
  `orientation ∈ {"horizontal", "vertical"}` (meaningful only for rivers).
- **Starting position** (`default_start_board`): the middle 6 columns get two
  rows of Square stones near the top (rows 3–4) and two rows of Circle
  stones near the bottom (rows `rows-5, rows-4`) — 12 pieces per side, each
  starting on the half of the board nearest the *opponent's* scoring row.
- **Scoring cells.** `score_cols_for(cols)` picks the 4 centre columns.
  `top_score_row() = 2` is Circle's own scoring row; `bottom_score_row(rows) = rows-3` is Square's. A cell only counts toward victory if it holds a
  **stone-side-up** piece owned by that player (`check_win`, `WIN_COUNT = 4`).
- **Actions**, all validated by `validate_and_apply_move`: `move` (one
  orthogonal step, or a step into a river that then flows), `push` (a stone
  shoves an adjacent stone one cell, or a river shoves an adjacent stone
  through a full river-flow chain and then flips itself back to a stone),
  `flip` (stone↔river, orientation required going to river), and `rotate`
  (toggle a river's orientation). Entering the opponent's score cells, or
  opening a flip/rotate that would let flow reach them, is always rejected.
- **Clocks & draws.** Each player has a clock (`TIME_PER_PLAYER`, default 60s,
  overridable via `--time` in minutes). Wall time spent inside an AI's
  `choose()` call is deducted from that player's clock; hitting zero loses
  the game (or draws it if both hit zero on the same check). Both `run_cli`
  and `run_gui` also cap play at 1000 half-moves before forcing a draw — the
  spec PDF describes a 500-move cap, the shipped engine uses 1000.
  `compute_final_scores` implements the PDF's scoring formulas exactly: a
  winner scores `100 − (n_lose + m_lose/10)`; a draw gives each side
  `30 + margin/4` with `margin = 39 + (n_self + m_self/10) − (n_opp + m_opp/10)`, where `n_*`/`m_*` come from `count_scoring_pieces` (stones
  already home) and `count_reachable_in_one` (stones one move/push from
  home, found by re-running `compute_valid_targets` on every stone).

## Move Generation & River-Flow BFS

Move generation is implemented **twice**, independently: once in `agent.py`
(`BaseAgent.generate_all_moves`, used by `RandomAgent`), and once again,
duplicated almost line-for-line but reimplemented from scratch, inside
`student.py`. The student agent carries its own private `Piece` class
and its own `compute_valid_targets` / `get_river_flow_destinations` /
`validate_and_apply_move`, and never imports `gameEngine.py` — it is a
fully self-contained rules engine, presumably so the bot file can be graded
in isolation. The two copies agree on behaviour but are separate code paths;
a bug fixed in one is not automatically fixed in the other.

The core primitive both copies share is a **BFS over river cells**
(`get_river_flow_destinations`). Starting from the cell a piece is entering,
if that cell holds a river the search fans out along the river's
orientation (`(±1,0)` for horizontal, `(0,±1)` for vertical); it keeps
walking that line, recording every empty cell as a candidate destination,
until it hits a stone (blocked) or another river (enqueue that river's
position and continue the search from there, now following *its*
orientation). Any step that would land in the opponent's score cells is
excluded from the frontier before it's ever queued. `compute_valid_targets`
then wraps this: for each of the piece's 4 neighbours, an empty cell is a
plain move, a river cell hands off to the BFS for a (possibly long-range)
move, and a stone-occupied cell is either a one-cell stone-push (checked
directly) or, if the mover is itself a river, a push that resolves through
the same BFS (`river_push=True`, which treats the mover's own cell as the
river source so the target can flow through/around it). `generate_all_moves`
walks every board cell owned by the current player and calls
`compute_valid_targets` on it, then appends flip moves (2 orientations for
a stone, 1 for a river) and a rotate move for rivers. A module-level list,
`historyqueue`, records the `StudentAgent`'s last 4 moves across calls;
`generate_all_moves` filters those exact moves back out of the freshly
generated list as a cheap anti-repetition/anti-cycling measure — it is not
a general position-repetition detector, just a fixed-length recency filter
on move dicts.

## Search Algorithm — What `maxValue` Actually Does

The bot's decision routine is `get_best_move(board, player, ...)` →
`maxValue(board, player, ..., ply, move_cnt)` → `evaluate_simple(...)`. The
naming (`maxValue`) evokes textbook minimax, but reading the recursion shows
it is **not adversarial two-player search**: at every level `maxValue`
regenerates candidate moves for the *same* `player` argument it started
with — it never flips to the opponent and never takes a `min`. Concretely:

```
get_best_move(board, player):
    depth, move_cnt = 1, 30
    moves = generate_heuristic_moves(board, player, ..., move_cnt)   # candidate filter
    for move in moves:
        child = simulate_move(board, move, player, ...)
        val = maxValue(child, player, ..., ply=depth, move_cnt)      # same player!
        keep move with best val
    return best move

maxValue(board, player, ..., ply, move_cnt):
    if ply == 0 or game_over(board, ...):
        return evaluate_simple(board, player, ...) + ply*100
    moves = generate_heuristic_moves(board, player, ..., move_cnt)   # same player again
    return max(maxValue(simulate_move(board, m, player, ...), player, ..., ply-1, move_cnt)
               for m in moves)
```

With `depth = 1`, this expands exactly two plies, both belonging to the
mover: `get_best_move` picks a first move, `maxValue` (ply 1) picks a
second move on top of it, and at ply 0 the resulting board is scored by
`evaluate_simple` and the best two-move combination wins. In effect the
search asks "what's the best pair of moves I can make in a row?", with **no
model of how the opponent would respond in between** — it is a shallow
greedy lookahead dressed in minimax-style naming, not a minimax/alpha-beta
tree over both players. There is accordingly no min layer, no alpha-beta
pruning, and no transposition table anywhere in the file. `choose()`
receives `current_player_time` and `opponent_time` (the remaining clocks in
seconds) but neither value is read anywhere in `get_best_move` or
`maxValue` — depth (`1`) and the candidate cap (`move_cnt = 30`) are fixed
constants, so there is no iterative deepening or any other time-adaptive
behaviour despite the framework plumbing both clocks through to the agent.

The only pruning that does happen is *pre-search move filtering*, in
`generate_heuristic_moves`: every legal move is scored by a fast static
heuristic — `score_move` for `move`/`push` actions (rewards entering the
goal-side rows, landing in the scoring columns, reducing Manhattan distance
to the nearest empty own-goal cell via `dist_to_empty_goal`, and pushing an
opponent stone further from *its* goal or a friendly stone closer to
one's own), `score_flow_move` for `flip`/`rotate` actions (rewards river
orientations whose flow reaches goal-side rows or lands directly in the
goal, computed by temporarily flipping/rotating the piece, running
`get_river_flow_destinations`, then reverting it). `generate_heuristic_moves`
keeps only the top `move_cnt // 3` flip/rotate moves and top
`2 * (move_cnt // 3)` move/push moves by that score, shuffles the survivors,
and hands that list to `maxValue`. If the player already has all 4 stones
home, the candidate list collapses to just "flip a river sitting in the
goal back to a stone" (the only way to still win).

## Evaluation Function

`evaluate_simple(board, player, rows, cols, score_cols)` is a weighted
linear sum of hand-engineered features, one extractor function each:

| Feature                             | Extractor                  | Meaning                                                                          | Weight                         |
| ----------------------------------- | -------------------------- | -------------------------------------------------------------------------------- | ------------------------------ |
| `all_piece_in_goal`               | `eval_pieces_in_goal`    | 1 if 4 stones already home                                                       | `100000.0`                   |
| `stone_goal` / `opp_stone_goal` | `eval_stone_in_goal`     | stones already in own/opp goal                                                   | `500` / `-100.0`           |
| `river_goal` / `opp_river_goal` | `eval_river_in_goal`     | rivers sitting in own/opp goal                                                   | `500` / `-50.0`            |
| `row_dist` / `opp_row_dist`     | `eval_dist_to_goal_row`  | summed row-distance of own/opp pieces to their goal row                          | `-10.05107003095954` / `2` |
| `col_dist` / `opp_col_dist`     | `eval_dist_to_goal_cols` | column distance to nearest empty goal cell, for pieces already on goal-side rows | `-10.06` / `5.04`          |
| `near_river` / `opp_near_river` | `eval_piece_near_river`  | pieces adjacent to any river                                                     | `4.9617...` / `-4.9982...` |
| `flow_score` / `opp_flow_score` | `eval_flow_score`        | river-flow destinations landing on goal-side rows / inside the goal              | `2` / `-0.01`              |
| `river_beside_goal`               | `eval_river_beside_goal` | horizontal rivers flanking the goal columns                                      | `600`                        |

`total = sum(weight[k] * feature[k] for k in features)`. **No
training/optimization code exists anywhere in this repository** — no
gradient descent, self-play loop, or data-fitting script appears in
`student.py`, `agent.py`, or `gameEngine.py`; the weights are plain
Python float literals inside `evaluate_simple`. Several of them are
non-round, many-decimal values (`-10.05107003095954`,
`4.961702380952383`, `-4.998166666666669`) that look like the output of
some offline tuning process — but that process, if it existed, is not part
of the checked-in code, only its resulting numbers are. When
`all_piece_in_goal == 1` (the player already has 4 stones home),
`evaluate_simple` short-circuits to a reduced feature set — just
`stone_goal * 100` and `opp_stone_goal`, everything else zeroed — so once
the game is essentially won the heuristic stops caring about positional
features and only reasons about keeping/regaining scoring pieces.

## Game Loop & Turn Structure

`gameEngine.py` is the sole entry point (`main()`) and the authoritative
referee, with its own separate copy of `validate_and_apply_move` /
`compute_valid_targets` / `get_river_flow_destinations` — distinct from,
but behaviourally equivalent to, the one embedded in `student.py`.
Both `run_cli` (`--nogui`, ASCII/emoji board via `board_to_ascii`) and
`run_gui` (pygame) share the same turn loop: alternate
`current = "circle"/"square"`; on an AI turn, call
`agent.choose(board, rows, cols, score_cols, own_time, opp_time)`, time the
call, deduct elapsed wall time from that player's clock, validate/apply the
returned move dict, then check `check_win` before flipping `current` to the
opponent. `run_gui` additionally supports full interactive human play
(`M`/`P`/`F`/`R`/`Esc`/`S` keys for move/push/flip/rotate/cancel/save-board)
and renders pieces, river-flow arrow glyphs, score zones, timers and a
status bar. `agent.py`'s `get_agent(player, strategy)` factory resolves
`strategy` dynamically: `"random"` builds the built-in `RandomAgent`, and
every other name is treated as a filename — `get_agent("circle", "student2")` imports `student2.py` (from the same directory as `agent.py`)
and instantiates whatever concrete class in it defines a `choose(...)`
method. This is duck-typed rather than an `issubclass(BaseAgent)` check, so
a strategy file is free to define its own standalone `BaseAgent`/`choose`
contract instead of importing `agent.BaseAgent` — `student.py` does exactly
that. If the file doesn't exist, or defines zero or multiple ambiguous
agent classes, `get_agent` raises `ValueError` immediately rather than
falling back to a placeholder.

## How to Run

Dependencies (`requirements.txt`): `pygame>=2.0.0`, `numpy>=1.21.0`,
`scipy>=1.7.0` — numpy/scipy are listed but not actually imported anywhere
in the three source files.

```sh
py -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt

python gameEngine.py --mode hvh                                   # human vs human, GUI
python gameEngine.py --mode hvai --circle random                  # human vs AI, GUI
python gameEngine.py --mode aivai --circle random --square student            # AI vs AI, GUI
python gameEngine.py --mode aivai --circle random --square student --nogui    # AI vs AI, text
python gameEngine.py --mode aivai --circle student --square student --time 5 # 5 min/player
```

`--time` is minutes per player (default 1.0, matching the assignment's
1-minute-per-game evaluation budget).

## Testing Notes

No self-play logging or benchmark results are checked into the repo. The
only test code is a smoke test at the bottom of `student.py`
(`test_student_agent`) that just confirms `choose()` returns a move without
raising; `saved_board.json` is a one-off mid-game snapshot from pressing
`S` in the GUI, not benchmark data; `commands.txt` lists ad-hoc commands
used during development with no retained output.

## Usage

This section walks through actually installing and running the code, based
on `requirements.txt`, `gameEngine.py`'s `argparse` setup (`main()`, line
1166), and `commands.txt`. `NOTES.md` documents the same commands (it is the
original assignment scaffold's usage note); the walkthrough below adds the
GUI/CLI mechanics and flags a couple of things `NOTES.md` and the CLI's own
`--help` don't make obvious.

### 1. Prerequisites (required)

- **Python 3.9** — this is what `NOTES.md` specifies for the conda
  environment; `requirements.txt`'s header comment says "3.8+". Either
  works in practice since nothing in the three source files uses
  version-specific syntax.
- The three packages in `requirements.txt`: `pygame>=2.0.0`,
  `numpy>=1.21.0`, `scipy>=1.7.0`. As noted above, numpy/scipy are declared
  but never `import`ed by `gameEngine.py`, `agent.py`, or `student.py`
  — only `pygame` is actually required for the GUI to start, and even
  `pygame` is optional if you always pass `--nogui` (`run_gui` checks `if not pygame:` and refuses to start, printing `"pygame not available; use --nogui"`, but `run_cli` never imports it).

### 2. Setup (required)

Either a venv or the conda environment from `commands.txt`/`NOTES.md` works;
`gameEngine.py` itself doesn't care which. Using the venv form already
present in this folder:

```sh
py -m venv venv
.\venv\Scripts\Activate
pip install -r requirements.txt
```

or, per `commands.txt`/`NOTES.md`:

```sh
conda create --name stones_river python=3.9
conda activate stones_river
pip install -r requirements.txt
```

### 3. Running a game (required — pick one mode)

All invocations are `python gameEngine.py` with flags parsed by `main()`:
`--mode {hvh,hvai,aivai}` (default `hvai`), `--circle`/`--square <strategy>`
(default `random` for both; no longer a fixed `choices=[...]` list — any
string works), `--nogui` (flag, default off = GUI), `--time <minutes-per-player>` (float, default `1.0`), and `--load <path>` (default
`None`, see the caveat below). `--circle`/`--square random` builds the
built-in `RandomAgent`; any other value `<name>` is resolved by `get_agent`
to a file `<name>.py` next to `agent.py` — `--circle student` loads
`student.py`, and `--circle student2` would load `student2.py` if you add
one alongside it (per the Game Loop section above, no `student2.py` ships
in this folder, so selecting `student2` currently raises `ValueError: Unknown strategy 'student2': no file 'student2.py' found in ...` instead of
falling back to a placeholder).

```sh
python gameEngine.py --mode hvh                                    # human vs human, GUI (default)
python gameEngine.py --mode hvai --circle random                   # human vs AI, GUI
python gameEngine.py --mode aivai --circle random --square student # AI vs AI, GUI
python gameEngine.py --mode aivai --circle random --square student --nogui   # AI vs AI, text-only
python gameEngine.py --mode aivai --circle student --square student2 --time 5  # 5 min/player/side
```

The last two lines are pulled directly from `commands.txt`; the rest match
`gameEngine.py`'s `argparse` defaults and choices.

**Mode-to-side-assignment quirk:** in `hvai` mode, `run_cli`/`run_gui` do
*not* read a separate "which side is human" flag. They decide purely from
`circle_strategy`: `if circle_strategy=="random": players={"circle":"ai", "square":"human"} else: players={"circle":"human","square":"ai"}`. So
`--mode hvai --circle random` gives you Circle-AI vs Square-human, and
`--mode hvai --circle student` gives you Circle-human vs Square-AI (using
whatever `--square` strategy you passed, default `random`) — `--square` is
never consulted to decide *who* is the AI, only *which* AI. This isn't
documented anywhere in the code or `NOTES.md`; it's only visible by reading
the `if/else` in `run_cli`/`run_gui`.

### 4. Expected output

- **GUI mode** (default, no `--nogui`): a pygame window titled `River and Stones - <MODE> Mode`, showing the 13×12 board, pieces, river-flow arrow
  glyphs, score-zone highlighting, a status/message bar, and both players'
  countdown timers. Human turns are played by **mouse + keyboard**: click a
  piece you own to select it, press `M`/`P`/`F`/`R` to enter Move / Push /
  Flip / Rotate mode (a flip additionally needs `H` or `V` afterward when
  going stone→river, or `F` again when going river→stone), then click the
  destination square(s) — `Esc` clears the current selection, `S` writes
  the current board to `saved_board.json` via `save_board_to_file`. AI
  turns happen automatically; the loop caps at 1000 half-moves
  (`if turn > 1000: print("Turn limit reached -> draw")`) and ends by
  showing the winner or draw in the status bar.
- **`--nogui` (CLI/ASCII mode)**: `run_cli` prints a welcome banner, the
  mode and strategies, then loops printing `board_to_ascii(...)` (an
  emoji/ASCII rendering of the grid), a turn header (`Turn N: <SIDE>'s move`) and both remaining clocks (`format_time`). On an AI turn
  it prints `🤖 AI <side> is thinking...`, then `AI <side> -> <move-dict>`
  and the validator's `Result: <msg>`. On a human turn it prints the four
  accepted JSON move shapes (`move`, `push`, `flip`, `rotate` — exact
  dict keys shown in the CLI output) and prompts `<side> move JSON: ` via
  `input()`; typing `q` quits. The loop ends by printing `🎉 WINNER: <SIDE> 🎉` (or a timeout/draw message) followed by
  `Final Scores -> Circle: X.X | Square: X.X`, computed by
  `compute_final_scores` per the scoring formulas above.
- A **human vs human** or **human vs AI** run pauses on `input("\nPress Enter to continue...")` between the CLI's own printed turns as a
  readability throttle — this only fires in `--nogui` mode, not the GUI.

### 5. Loading a saved board — caveat (optional, currently non-functional)

`--load <path>` is parsed by `argparse` and threaded as the `load_file`
parameter into both `run_cli(mode, circle_strategy, square_strategy, load_file, rows, cols, time_per_player)` and the equivalent `run_gui(...)`
signature — but **neither function body ever reads `load_file`**. Both
unconditionally start from `board = default_start_board(rows, cols)`. The
plumbing to actually load a board exists (`load_board_from_file(path)`,
which reads a JSON file shaped like `saved_board.json` — `{"board": [[cell or null, ...], ...]}` with each cell `{"owner": "circle"|"square", "side": "stone"|"river", "orientation": "horizontal"|"vertical"}`, reconstructed via
`Piece.from_dict`) and to save one (`S` key in the GUI, always to the fixed
filename `saved_board.json`), but the load side is dead code as shipped:
passing `--load saved_board.json` is accepted silently and has **no effect**
on the board actually used. This is a gap in the current source, not an
assumption — confirmed by reading both call sites of `load_file` in
`gameEngine.py`, where the parameter is never referenced again after the
function signature.
