"""
Student Agent Implementation for River and Stones Game

This file contains the essential utilities and template for implementing your AI agent.
Your task is to complete the StudentAgent class with intelligent move selection.

Game Rules:
- Goal: Get 4 of your stones into the opponent's scoring area
- Pieces can be stones or rivers (horizontal/vertical orientation)  
- Actions: move, push, flip (stone↔river), rotate (river orientation)
- Rivers enable flow-based movement across the board

Your Task:
Implement the choose() method in the StudentAgent class to select optimal moves.
You may add any helper methods and modify the evaluation function as needed.
"""

from collections import deque
import random
import copy
from typing import List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
import json

historyqueue = []


class Piece:
    def __init__(self, owner:str, side:str="stone", orientation:Optional[str]=None):
        self.owner = owner
        self.side = side
        self.orientation = orientation if orientation else "horizontal"
    def copy(self): return Piece(self.owner, self.side, self.orientation)
    def to_dict(self): return {"owner":self.owner,"side":self.side,"orientation":self.orientation}
    @staticmethod
    def from_dict(d:Optional[Dict[str,Any]]):
        if d is None: return None
        return Piece(d["owner"], d.get("side","stone"), d.get("orientation","horizontal"))


# ==================== GAME UTILITIES ====================

def in_bounds(x: int, y: int, rows: int, cols: int) -> bool:
    """Check if coordinates are within board boundaries."""
    return 0 <= x < cols and 0 <= y < rows

def count_piece_in_goal(board,player,rows,cols,score_cols)->int:
    """ Counts the number of pieces in goal for the player """
    
    if player == "circle":
        goal_row = top_score_row()
    else:  
        goal_row = bottom_score_row(rows)
        
    cnt = 0
    for x in score_cols:
        if board[goal_row][x] is not None:
            cnt+=1
    return cnt
      
def game_over(board, rows, score_cols)-> bool:
    """ Check ig game is over or not """
    row1 = top_score_row()
    row2 = bottom_score_row(rows)
    cnt1 = 0
    cnt2 = 0
    for col in score_cols:
        piece1 = board[row1][col]
        if piece1 is not None and piece1.side == "stone":
            cnt1 += 1

        piece2 = board[row2][col]
        if piece2 is not None and piece2.side == "stone":
            cnt2 += 1

    if cnt1 == 4 or cnt2 == 4:
        return True
    return False

def dist_to_empty_goal(dx,dy,board,player,rows,cols,score_cols)->float:
    """Calculates the minimum distance to empty goal from coordinate (dy,dx)"""
    
    if player == "circle":
        goal_row = top_score_row()
    else:
        goal_row = bottom_score_row(rows)

    dist = 1000
    for x in score_cols:
        if board[goal_row][x] is None:
            dist = min(dist,abs(dx-x)+abs(dy-goal_row))
                    
    return dist

def distance_to_goal(x, y, player, rows, cols, score_cols)->float:
    """Compute minimum distance from (y, x) to player's scoring area."""
    if player == "circle":
        goal_y = 2
    else:
        goal_y = rows - 3

    return min(abs(y - goal_y) + abs(x - col) for col in score_cols)

def get_goal_side_rows(player,rows,cols,score_cols)-> List[int]:
    # 5 rows
    if player== "circle":
        return range(0,4)
    else:
        return range(rows-5,rows-1)
    
    
def is_goal_side_rows(fx,fy,player,rows,cols,score_cols)->bool:
    """
    Check if fy is  the 'goal side rows' rows near the score area.
    """
    
    # goal side 5 rows
    if player == "circle":  # suppose Player 1 scores at right
        return fx <= 4
    else:  # Player 2 scores at left
        return fx >= rows - 5 


def has_adjacent_river(board, x, y, rows, cols)->bool:
    """Check if piece has adjacent river"""
    directions = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    for dx, dy in directions:
        nx, ny = x + dx, y + dy
        if in_bounds(nx, ny, rows, cols):
            neighbor = board[ny][nx]
            if neighbor and neighbor.side == "river":
                return True
    return False

def score_cols_for(cols: int) -> List[int]:
    """Get the column indices for scoring areas."""
    w = 4
    start = max(0, (cols - w) // 2)
    return list(range(start, start + w))


def top_score_row() -> int:
    """Get the row index for Circle's scoring area."""
    return 2


def bottom_score_row(rows: int) -> int:
    """Get the row index for Square's scoring area."""
    return rows - 3


def is_opponent_score_cell(
    x: int, y: int, player: str, rows: int, cols: int, score_cols: List[int]
) -> bool:
    """Check if a cell is in the opponent's scoring area."""
    if player == "circle":
        return (y == bottom_score_row(rows)) and (x in score_cols)
    else:
        return (y == top_score_row()) and (x in score_cols)


def is_own_score_cell(
    x: int, y: int, player: str, rows: int, cols: int, score_cols: List[int]
) -> bool:
    """Check if a cell is in the player's own scoring area."""
    if player == "circle":
        return (y == top_score_row()) and (x in score_cols)
    else:
        return (y == bottom_score_row(rows)) and (x in score_cols)


def get_opponent(player: str) -> str:
    """Get the opponent player identifier."""
    return "square" if player == "circle" else "circle"




#-------------------- some heuristic functions for move pruning ----------

def score_move(move, board, player, rows, cols, score_cols):
    """calculates the score of this move based on some parameters for move/push types"""
    
    fx, fy = move["to"]
    sx, sy = move["from"]
    score = 0

    if move["action"] == "move":
        
        if not is_goal_side_rows(sx,sy,player,rows,cols,score_cols) and  is_goal_side_rows(fx,fy,player,rows,cols,score_cols):
            score += 10
        if is_goal_side_rows(sx,sy,player,rows,cols,score_cols) and sx not in score_cols and fx in score_cols :
            score += 10 
        if  is_own_score_cell(fx, fy, player, rows, cols, score_cols):
            if not is_own_score_cell(sx, sy, player, rows, cols, score_cols):
                score += 5000
            else:
                score+=10
        
        dist = dist_to_empty_goal(fx,fy,board,player,rows,cols,score_cols)
        
        score-=dist
        
        
        
    # 4. For pushes: increase opponent distance from goal
    opponent = get_opponent(player)
    if move["action"] == "push":
        fx,fy = move["to"]
        pushed_piece_owner = board[fy][fx].owner
        
        dest_x, dest_y = move["pushed_to"]
        if pushed_piece_owner == player:
            score -= distance_to_goal(dest_x,dest_y,player,rows,cols,score_cols) * 0.1 
            if not is_own_score_cell(sx,sy,player,rows,cols,score_cols) and is_own_score_cell(dest_x,dest_y,player,rows,cols,score_cols):
                score+= 1000
        else:
            score += distance_to_goal(dest_x, dest_y, opponent, rows, cols, score_cols) * 0.1
        # Prefer pushes to cells with no adjacent rivers
    return score


def score_flow_move(move, board, player, rows, cols, score_cols):
    """calculates the score of this move based on some parameters for rotate/flip types"""
    x, y = move["from"]
    piece = board[y][x]
    score = 0
    
    # Save original state
    original_side = piece.side
    original_orientation = getattr(piece, "orientation", None)
    
    
    # Temporarily apply the move
    if move["action"] == "flip":
        if is_own_score_cell(x,y,player,rows,cols,score_cols) and piece.side =="river" :
            score +=100
        # elif is_own_score_cell(x,y,player,rows,cols,score_cols) and piece.side =="stone":
        #     score +=1
        piece.side = "river" if piece.side == "stone" else "stone"
        
    elif move["action"] == "rotate":
        piece.orientation = "vertical" if original_orientation == "horizontal" else "horizontal"

    # Determine if this move is a river push scenario
    river_push = move["action"] == "push" and getattr(piece, "side", "stone") == "river"

    # Compute flow destinations
    flow_cells = get_river_flow_destinations(
        board,
        x, y,               # starting river cell
        x, y,               # source position (self)
        player,
        rows,
        cols,
        score_cols,
        river_push=river_push
    )

    # Only consider safe cells (not in opponent score)
    safe_flow = [
        (fx, fy)
        for fx, fy in flow_cells
        if not is_opponent_score_cell(fx, fy, player, rows, cols, score_cols)
    ]
    
    goal_side_flow = [
        (fx,fy)
        for fx,fy in safe_flow
        if is_goal_side_rows(fx,fy,player,rows,cols,score_cols)
    ]
    
    in_goal_flow = [
        (fx,fy)
        for fx,fy in safe_flow
        if is_own_score_cell(fx,fy,player,rows,cols,score_cols)
    ]

    # Base score = number of safe flow cells
    # score += len(safe_flow)
    score += len(goal_side_flow) # bonus for goal side flow
    score += len(in_goal_flow) *5 # bonus for flow in goal

    # Bonus for connecting to existing rivers
    # if move["action"] in ("flip", "rotate") and piece.side == "river" and has_adjacent_river(board, x, y, rows, cols):
    #     score += 2

    # Revert piece to original state
    piece.side = original_side
    piece.orientation = original_orientation

    return score



# ==================== generate moves ======================

def get_river_flow_destinations(
    board: List[List[Optional["Piece"]]],
    rx: int,
    ry: int,
    sx: int,
    sy: int,
    player: str,
    rows: int,
    cols: int,
    score_cols: List[int],
    river_push: bool = False
) -> List[Tuple[int, int]]:
    """
    Compute all possible destinations for a piece entering a river and river pushes to piece.

    Args:
        board: Current board state
        rx, ry: River entry coordinates
        sx, sy: Source piece coordinates (ignored as obstacle)
        player: Current player
        rows, cols: Board dimensions
        score_cols: List of scoring columns
        river_push: True if a river piece is pushing a stone

    Returns:
        List of unique (y, x) coordinates where the piece can end up
    """

    destinations = set()
    visited = set()
    queue = deque([(rx, ry)])

    while queue:
        x, y = queue.popleft()
        if (x, y) in visited or not in_bounds(x, y, rows, cols):
            continue
        visited.add((x, y))

        cell = board[y][x]

        # In river-push, allow BFS even if starting cell is a stone
        if river_push and (x, y) == (rx, ry):
            is_river = True
        else:
            is_river = cell is not None and cell.side == "river"

        if not is_river:
            # Empty cell: valid destination, it's not opponent's scoring area
            if cell is None and not is_opponent_score_cell(x, y, player, rows, cols, score_cols):
                destinations.add((x, y))
            continue

        # Determine flow directions based on orientation
        orientation = cell.orientation
        dirs = [(1, 0), (-1, 0)] if orientation == "horizontal" else [(0, 1), (0, -1)]

        for dx, dy in dirs:
            nx, ny = x + dx, y + dy
            while in_bounds(nx, ny, rows, cols):
                
                # Block opponent scoring area
                if is_opponent_score_cell(nx, ny, player, rows, cols, score_cols):
                    break

                # Skip source cell (for push) so stone can flow
                if (nx, ny) == (sx, sy):
                    nx += dx
                    ny += dy
                    continue

                next_cell = board[ny][nx]

                if next_cell is None:
                    destinations.add((nx, ny))
                    nx += dx
                    ny += dy
                    continue

                if next_cell.side == "river":
                    if (nx, ny) not in visited:
                        queue.append((nx, ny))
                    break 
                break  # blocked by stone

    return list(destinations)


def compute_valid_targets(
    board: List[List[Optional[Piece]]],
    sx: int,
    sy: int,
    player: str,
    rows: int,
    cols: int,
    score_cols: List[int],
) -> Dict[str, Any]:
    if not in_bounds(sx, sy, rows, cols):
        return {"moves": set(), "pushes": []}

    p = board[sy][sx]
    if p is None or p.owner != player:
        return {"moves": set(), "pushes": []}

    moves = set()
    pushes = []
    dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]

    for dx, dy in dirs:
        tx, ty = sx + dx, sy + dy
        if not in_bounds(tx, ty, rows, cols):
            continue

        # block entering opponent score cell
        if is_opponent_score_cell(tx, ty, player, rows, cols, score_cols):
            continue

        target_piece = board[ty][tx]

        if target_piece is None:
            # Normal move
            moves.add((tx, ty))

        elif target_piece.side == "river":
            # Cannot push rivers; compute river flow for moves
            flow = get_river_flow_destinations(
                board, tx, ty, sx, sy, player, rows, cols, score_cols
            )
            for fx, fy in flow:
                moves.add((fx, fy))

        elif target_piece.side == "stone":
            # Handle push logic
            if p.side == "stone":
                # Stone pushes stone: next cell in same direction must be empty
                px, py = tx + dx, ty + dy
                if (
                    in_bounds(px, py, rows, cols)
                    and board[py][px] is None
                    and not is_opponent_score_cell(px, py, target_piece.owner, rows, cols, score_cols)
                ):
                    pushes.append(((tx, ty), (px, py)))

            elif p.side == "river":
                # River pushes stone: simulate river replacing stone
                original_piece = board[ty][tx]
                board[ty][tx] = p  # temporarily place river
                flow = get_river_flow_destinations(
                    board,
                    tx, ty,
                    sx, sy,  # original river position will act as obstacle
                    original_piece.owner,
                    rows, cols,
                    score_cols,
                    river_push=True
                )
                board[ty][tx] = original_piece  # restore stone

                for fx, fy in flow:
                    # Cannot move back to original river position
                    if (fx, fy) == (sx, sy):
                        continue
                    if not is_opponent_score_cell(fx, fy, original_piece.owner, rows, cols, score_cols):
                        pushes.append(((tx, ty), (fx, fy)))

    return {"moves": moves, "pushes": pushes}

def generate_all_moves(
    board: List[List[Optional["Piece"]]],
    player: str,
    rows: int,
    cols: int,
    score_cols: List[int]
) -> List[Dict[str, Any]]:
    
    """
    Generate all valid moves for the current player on the board.
    Uses compute_valid_targets to ensure only legal moves/pushes.
    Supports move, push, flip, and rotate actions.
    """
    moves = []

    for y in range(rows):
        for x in range(cols):
            piece = board[y][x]
            if not piece or piece.owner != player:
                continue

            # ------------------- Compute valid moves & pushes -------------------
            valid_info = compute_valid_targets(board, x, y, player, rows, cols, score_cols)

            # Add normal moves
            for to in valid_info['moves']:
                moves.append({
                    "action": "move",
                    "from": [x, y],
                    "to": list(to)
                })

            # Add valid pushes (with opponent-score restriction)
            for from_cell, pushed_cell in valid_info['pushes']:
                px, py = pushed_cell
                target_piece = board[from_cell[1]][from_cell[0]] if in_bounds(from_cell[0], from_cell[1], rows, cols) else None

                # Only skip if the pushed piece would land in *opponent's* scoring area
                if target_piece and is_opponent_score_cell(px, py, target_piece.owner, rows, cols, score_cols):
                    continue

                moves.append({
                    "action": "push",
                    "from": [x, y],
                    "to": list(from_cell),
                    "pushed_to": list(pushed_cell)
                })

            # ------------------- Flips -------------------
            if piece.side == "stone":
                # Flip stone -> river
                for ori in ("horizontal", "vertical"):
                    moves.append({
                        "action": "flip",
                        "from": [x, y],
                        "orientation": ori
                    })
            else:
                # Flip river -> stone
                moves.append({
                    "action": "flip",
                    "from": [x, y]
                })

                # Rotate river piece
                new_ori = "vertical" if piece.orientation == "horizontal" else "horizontal"
                moves.append({
                    "action": "rotate",
                    "from": [x, y],
                    "orientation": new_ori
                })

    # ------------------- remove duplicate moves -------------------
    seen = set()
    unique_moves = []
    moves = [m for m in moves if m not in historyqueue]
    for m in moves:
        key = (
            m["from"][0],
            m["from"][1],
            tuple(m["to"]) if m.get("to") else None,
            tuple(m["pushed_to"]) if m.get("pushed_to") else None,
            m.get("orientation", None),
            m["action"]
        )
        if key not in seen:
            seen.add(key)
            unique_moves.append(m)

    return unique_moves

def generate_heuristic_moves(board, player, rows, cols, score_cols,move_cnt)->List[Dict[str, Any]]:
    """ Selects  best moves based on some score"""
    
    no_of_piece_in_goal = count_piece_in_goal(board,player,rows,cols,score_cols)
    moves = generate_all_moves(board, player, rows, cols, score_cols)
    filtered_moves = []
    
    if no_of_piece_in_goal == 4:
        for move in moves:
            if move['action'] == "flip" :  
                sx,sy = move["from"]
                piece = board[sy][sx]
                if piece.side == "river" and is_own_score_cell(sx,sy,player,rows,cols,score_cols):
                    filtered_moves.append(move)                             
    else:
        action_flip_rotate_moves = [m for m in moves if m["action"] in ("flip", "rotate")]
        action_flip_rotate_moves = sorted(action_flip_rotate_moves, key=lambda m: score_flow_move(m, board, player, rows, cols, score_cols), reverse=True)
        action_flip_rotate_moves = action_flip_rotate_moves[:move_cnt//3]

        action_push_move_moves = [m for m in moves if m["action"] in ("push","move")]
        action_push_move_moves = sorted(action_push_move_moves,key=lambda m: score_move(m, board, player, rows, cols, score_cols),reverse=True)
        action_push_move_moves = action_push_move_moves[:2*(move_cnt//3)]

        filtered_moves = action_flip_rotate_moves + action_push_move_moves
    
    random.shuffle(filtered_moves)
    return filtered_moves

# ==================== BOARD EVALUATION ====================

def eval_stone_in_goal(board: List[List[Any]], player, row, col, score_cols: List[int])->float:
    """evaluation for stone count in goal"""
    if player == "circle":
        scoreRow = top_score_row()
    else:
        scoreRow = bottom_score_row(row)
        
    score = 0
    for y in score_cols:
        piece = board[scoreRow][y]
        if piece and piece.owner == player and piece.side == "stone":
            score += 1
    return score

def eval_river_in_goal(board: List[List[Any]], player, row, col, score_cols: List[int])->float:
    """evaluation for river count in goal"""
    
    if player == "circle":
        scoreRow = top_score_row()
    else:
        scoreRow = bottom_score_row(row)
    score = 0

    for y in score_cols:
        piece = board[scoreRow][y]
        if piece and piece.owner == player and piece.side == "river":
            score += 1
    return score

def eval_pieces_in_goal(board,player,rows,cols,score_cols)->float:
    """evaluation for 4 pieces in goal"""
    cnt = count_piece_in_goal(board,player,rows,cols,score_cols)
    score = 0      
    if cnt == 4:
        score = 1
    return score
    
def eval_dist_to_goal_row(board,player,rows,cols,score_cols)->float:
    """row distance of all pieces from goal row"""
    if player == "circle":
        goal_row = top_score_row()
    else:
        goal_row = bottom_score_row(rows)    
    score = 0
    
    for y in range(rows):
        for x in range(cols):
            piece = board[y][x]
            if piece is not None and piece.owner == player:
                score += abs(y-goal_row)
    return score

def eval_dist_to_goal_cols(board,player,rows,cols,score_cols)->float:
    """minimum columns distance of all pieces from goal columns (only if pieces in goal area)"""
    
    goal_side_rows = get_goal_side_rows(player,rows,cols,score_cols)
    if player=="circle" :
        goal_row = top_score_row() 
    else :
        goal_row = bottom_score_row(rows)
    score = 0
    for y in range(rows):
        for x in range(cols):
            piece = board[y][x]
            if piece is not None and piece.owner == player and y in goal_side_rows:
                minS = 1000
                for col in score_cols:
                    if board[goal_row][col] is not None:
                        minS = min(minS,abs(x-col))
                if minS != 1000:
                    score+=minS  
    return score

def eval_piece_near_river(board: List[List[Any]], player, rows, cols,score_cols)->float:
    """ number of player pieces near river """
    score = 0
    for y in range(rows):
        for x in range(cols):
            piece = board[y][x]
            if piece and piece.owner == player and not is_own_score_cell(x,y,player,rows,cols,score_cols):
                for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                    nx, ny = x + dx, y + dy
                    if in_bounds(nx, ny, rows, cols):
                        neighbor = board[ny][nx]
                        if neighbor and neighbor.side == "river":
                            score+=1
                            break
    return score

def eval_river_beside_goal(board,player,rows,cols,score_cols)->float:
    """ evaluation for the two position near player score area """
    score = 0
    if player == "circle":
        goal_row = top_score_row()
    else:
        goal_row = bottom_score_row(rows)
        
    side_boxes = [min(score_cols)-1,max(score_cols)+1]
    
    for col in side_boxes:
        piece = board[goal_row][col]
        if piece is not None and piece.side =="river" and piece.orientation == "horizontal":
            score+=1
    return score
        
def eval_flow_score(board,player,rows,cols,score_cols)->float:
    """ evaluation for flow in score area of player """    
    goal_area = get_goal_side_rows(player,rows,cols,score_cols)
    flow_score = 0
    for y in range(rows):
        for x in range(cols):
            piece = board[y][x]
            if piece is not None and piece.side =="river":
                flow = get_river_flow_destinations(board,x,y,x,y,player,rows,cols,score_cols)
                
                good_flow = [
                    (fx,fy) for fx,fy in flow
                    if fy in goal_area
                ]
                very_good_flow = [
                    (fx,fy) for fx,fy in good_flow
                    if is_own_score_cell(fx,fy,player,rows,cols,score_cols)
                ]
                
                flow_score += (len(good_flow) + len(very_good_flow))

    return flow_score
        
            
def evaluate_simple(board, player, rows, cols, score_cols)->float:
    """
    Combine all simple evaluation functions with given weights.
    """
    weights = {
        "all_piece_in_goal": 100000.0,
        "stone_goal": 500,
        "opp_stone_goal": -100.0,
        "river_goal": 500,
        "opp_river_goal": -50.0,
        "row_dist": -10.05107003095954,
        "opp_row_dist": 2,
        "col_dist": -10.059999999999999,
        "opp_col_dist": 5.04,
        "near_river": 4.961702380952383,
        "opp_near_river": -4.998166666666669,
        "flow_score": 2,
        "opp_flow_score": -0.01,
        "river_beside_goal": 600
    }   
    opponent = get_opponent(player)
    
    all_piece_in_goal=eval_pieces_in_goal(board,player,rows,cols,score_cols)
    
    if all_piece_in_goal == 1:
        stone_goal = eval_stone_in_goal(board, player, rows, cols, score_cols) *100
        opp_stone_goal = eval_stone_in_goal(board, opponent, rows, cols, score_cols)
        river_goal = 0
        opp_river_goal = 0
        row_dist = 0
        opp_row_dist = 0
        col_dist = 0
        opp_col_dist = 0
        near_river = 0
        opp_near_river = 0
        river_beside_goal  = 0
        flow_score = 0
        opp_flow_score = 0
    else:
        stone_goal = eval_stone_in_goal(board, player, rows, cols, score_cols) 
          
        opp_stone_goal = eval_stone_in_goal(board, opponent, rows, cols, score_cols)

        river_goal = eval_river_in_goal(board, player, rows, cols, score_cols)
        opp_river_goal = eval_river_in_goal(board, opponent, rows, cols, score_cols)
    
        row_dist = eval_dist_to_goal_row(board, player, rows, cols, score_cols)
        opp_row_dist = eval_dist_to_goal_row(board, opponent, rows, cols, score_cols)
    
        col_dist = eval_dist_to_goal_cols(board, player, rows, cols, score_cols)
        opp_col_dist = eval_dist_to_goal_cols(board, opponent, rows, cols, score_cols)
    
        near_river = eval_piece_near_river(board, player, rows, cols,score_cols)
        opp_near_river = eval_piece_near_river(board, opponent, rows, cols,score_cols)

        river_beside_goal  = eval_river_beside_goal(board,player,rows,cols,score_cols)
    
        flow_score = eval_flow_score(board,player,rows,cols,score_cols)
        opp_flow_score = eval_flow_score(board,opponent,rows,cols,score_cols)
    
    
    features ={
        "all_piece_in_goal":all_piece_in_goal,
        "stone_goal": stone_goal,
        "opp_stone_goal": opp_stone_goal,
        "river_goal": river_goal,
        "opp_river_goal": opp_river_goal,
        "row_dist":row_dist,
        "opp_row_dist":opp_row_dist,
        "col_dist":col_dist,
        "opp_col_dist":opp_col_dist,
        "near_river": near_river,
        "opp_near_river": opp_near_river,
        "flow_score":flow_score,
        "opp_flow_score":opp_flow_score,
        "river_beside_goal": river_beside_goal
    }

    total = sum(weights[k] * features[k] for k in features)
    return total


# ===================== simmulate for minimax
def validate_and_apply_move(
    board: List[List[Optional["Piece"]]],
    move: Dict[str, Any],
    player: str,
    rows: int,
    cols: int,
    score_cols: List[int]
) -> Tuple[bool, str]:
    """
    Validate and apply a move for the stones & river game.
    Supports actions: move, push, flip, rotate.

    Returns:
        Tuple[bool, str]: (success flag, message)
    """
    # Validate input type
    if not isinstance(move, dict):
        return False, "move must be a dict"

    action = move.get("action")

    # -------------------
    # MOVE ACTION
    # -------------------
    if action == "move":
        fr = move.get("from")
        to = move.get("to")
        if not fr or not to:
            return False, "move needs 'from' and 'to'"
        fx, fy = int(fr[0]), int(fr[1])
        tx, ty = int(to[0]), int(to[1])

        if not (in_bounds(fx, fy, rows, cols) and in_bounds(tx, ty, rows, cols)):
            return False, "out of bounds"
        if is_opponent_score_cell(tx, ty, player, rows, cols, score_cols):
            return False, "cannot move into opponent score cell"

        piece = board[fy][fx]
        if piece is None or piece.owner != player:
            return False, "invalid piece"

        # Normal move into empty cell
        if board[ty][tx] is None:
            board[ty][tx] = piece
            board[fy][fx] = None
            return True, "moved"

        # Move with push
        pushed = move.get("pushed_to")
        if not pushed:
            return False, "destination occupied; 'pushed_to' required"
        ptx, pty = int(pushed[0]), int(pushed[1])
        dx, dy = tx - fx, ty - fy

        if (ptx, pty) != (tx + dx, ty + dy):
            return False, "'pushed_to' must be in line with move direction"
        if not in_bounds(ptx, pty, rows, cols):
            return False, "pushed_to out of bounds"
        if is_opponent_score_cell(ptx, pty, player, rows, cols, score_cols):
            return False, "cannot push into opponent score cell"
        if board[pty][ptx] is not None:
            return False, "'pushed_to' not empty"

        # Apply move + push
        board[pty][ptx] = board[ty][tx]  # pushed piece
        board[ty][tx] = piece            # mover occupies destination
        board[fy][fx] = None             # origin cleared
        return True, "move + push applied"

    # -------------------
    # PUSH ACTION
    # -------------------
    elif action == "push":
        fr = move.get("from")
        to = move.get("to")
        pushed = move.get("pushed_to")
        if not fr or not to or not pushed:
            return False, "push needs 'from', 'to', and 'pushed_to'"

        fx, fy = int(fr[0]), int(fr[1])
        tx, ty = int(to[0]), int(to[1])
        px, py = int(pushed[0]), int(pushed[1])

        if not all(in_bounds(x, y, rows, cols) for x, y in [(fx, fy), (tx, ty), (px, py)]):
            return False, "out of bounds"

        piece = board[fy][fx]
        target = board[ty][tx]
        if piece is None or piece.owner != player:
            return False, "invalid piece"
        if target is None:
            return False, "'to' must be occupied"
        if board[py][px] is not None:
            return False, "'pushed_to' not empty"
        if piece.side == "river" and target.side == "river":
            return False, "rivers cannot push rivers"

        pushed_player = target.owner
        if is_opponent_score_cell(tx, ty, player, rows, cols, score_cols) or \
           is_opponent_score_cell(px, py, pushed_player, rows, cols, score_cols):
            return False, "push would enter opponent score cell"

        # Validate against computed valid pushes
        valid_info = compute_valid_targets(board, fx, fy, player, rows, cols, score_cols)
        if ((tx, ty), (px, py)) not in valid_info['pushes']:
            return False, "push pair invalid"

        # Apply push
        board[py][px] = board[ty][tx]  # pushed piece
        board[ty][tx] = piece          # mover occupies target
        board[fy][fx] = None           # origin cleared

        # If mover was river, convert back to stone
        if board[ty][tx].side == "river":
            board[ty][tx].side = "stone"
            board[ty][tx].orientation = None

        return True, "push applied"

    # -------------------
    # FLIP ACTION
    # -------------------
    elif action == "flip":
        fr = move.get("from")
        if not fr:
            return False, "flip needs 'from'"
        fx, fy = int(fr[0]), int(fr[1])
        if not in_bounds(fx, fy, rows, cols):
            return False, "out of bounds"
        piece = board[fy][fx]
        if piece is None or piece.owner != player:
            return False, "invalid piece"

        # Stone -> River
        if piece.side == "stone":
            ori = move.get("orientation")
            if ori not in ("horizontal", "vertical"):
                return False, "stone -> river needs valid orientation"

            # Check that resulting flow won't reach opponent score
            piece.side = "river"
            piece.orientation = ori
            flow = get_river_flow_destinations(board, fx, fy, fx, fy, player, rows, cols, score_cols)
            piece.side = "stone"  # revert temporarily
            piece.orientation = None
            for x, y in flow:
                if is_opponent_score_cell(x, y, player, rows, cols, score_cols):
                    return False, "flip would allow flow into opponent score"

            # Commit flip
            piece.side = "river"
            piece.orientation = ori
            return True, "flipped to river"

        # River -> Stone
        piece.side = "stone"
        piece.orientation = None
        return True, "flipped to stone"

    # -------------------
    # ROTATE ACTION
    # -------------------
    elif action == "rotate":
        fr = move.get("from")
        if not fr:
            return False, "rotate needs 'from'"
        fx, fy = int(fr[0]), int(fr[1])
        if not in_bounds(fx, fy, rows, cols):
            return False, "out of bounds"
        piece = board[fy][fx]
        if piece is None or piece.owner != player:
            return False, "invalid piece"
        if piece.side != "river":
            return False, "rotate only on river"

        # Toggle orientation
        piece.orientation = "horizontal" if piece.orientation == "vertical" else "vertical"

        # Check resulting river flow
        flow = get_river_flow_destinations(board, fx, fy, fx, fy, player, rows, cols, score_cols)
        for x, y in flow:
            if is_opponent_score_cell(x, y, player, rows, cols, score_cols):
                # Revert orientation
                piece.orientation = "horizontal" if piece.orientation == "vertical" else "vertical"
                return False, "rotation allows flow into opponent score"

        return True, "rotated"

    # -------------------
    # UNKNOWN ACTION
    # -------------------
    return False, "unknown action"

def simulate_move(
    board: List[List[Any]],
    move: Dict[str, Any],
    player: str,
    rows: int,
    cols: int,
    score_cols: List[int],
) -> Tuple[bool, Any]:
    """
    Simulate a move on a copy of the board.

    Returns:
        (success: bool, new_board or error_message)
    """

    board_copy = copy.deepcopy(board)
    success, message = validate_and_apply_move(
        board_copy, move, player, rows, cols, score_cols
    )

    if success:
        return True, board_copy
    else:
        return False, message



def get_best_move(board,player,rows,cols,score_cols) -> Dict[str, Any]:
    """return the move with best evaluation function"""
    maxVal = -float("inf")
    maxMove = None
    move_cnt = 30
    depth = 1
  
    moves = generate_heuristic_moves(board, player, rows, cols, score_cols,move_cnt)
    for move in moves:
        success, result = simulate_move(board, move, player, rows, cols, score_cols)
        if success:
            child_board = result
            childVal = maxValue(child_board,player,rows,cols,score_cols,depth,move_cnt)
            if childVal > maxVal:
                maxVal = childVal
                maxMove = move

    return maxMove


def maxValue(board,player,rows,cols,score_cols,ply,move_cnt) -> float:
    if ply == 0 or game_over(board,rows,score_cols):
        return evaluate_simple(board, player, rows, cols, score_cols) + ply * 100

    moves = generate_heuristic_moves(board, player, rows, cols, score_cols,move_cnt)
    if not moves:  # No moves available
        return evaluate_simple(board, player, rows, cols, score_cols)
    
    maxVal = -float("inf")
    for move in moves:
        success, child_board = simulate_move(board, move, player, rows, cols, score_cols)
        if success:
            childVal = maxValue(child_board,player,rows,cols,score_cols,ply-1,move_cnt)
            maxVal = max(maxVal, childVal)
    return maxVal

# ==================== BASE AGENT CLASS ====================

class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    """

    def __init__(self, player: str):
        """Initialize agent with player identifier."""
        self.player = player
        self.opponent = get_opponent(player)

    @abstractmethod
    def choose(
        self, board: List[List[Any]], rows: int, cols: int, score_cols: List[int]
    ) -> Optional[Dict[str, Any]]:
        """
        Choose the best move for the current board state.

        Args:
            board: 2D list representing the game board
            rows, cols: Board dimensions
            score_cols: List of column indices for scoring areas

        Returns:
            Dictionary representing the chosen move, or None if no moves available
        """
        pass

# ==================== STUDENT AGENT IMPLEMENTATION ====================

class StudentAgent(BaseAgent):
    """
    Student Agent Implementation
    
    TODO: Implement your AI agent for the River and Stones game.
    The goal is to get 4 of your stones into the opponent's scoring area.
    
    You have access to these utility functions:
    - generate_all_moves(): Get all legal moves for current player
    - basic_evaluate_board(): Basic position evaluation 
    - simulate_move(): Test moves on board copy
    - count_stones_in_scoring_area(): Count stones in scoring positions
    """
    
    def __init__(self, player: str):
        super().__init__(player)
        # TODO: Add any initialization you need
    
    def choose(self, board: List[List[Any]], rows: int, cols: int, score_cols: List[int], current_player_time: float, opponent_time: float) -> Optional[Dict[str, Any]]:
        """
        Choose the best move for the current board state.
        
        Args:
            board: 2D list representing the game board
            rows, cols: Board dimensions  
            score_cols: Column indices for scoring areas
            
        Returns:
            Dictionary representing your chosen move
        """
        my_move = get_best_move(board, self.player, rows, cols, score_cols)

        if not my_move:
            return None
        
        historyqueue.append(my_move)
        if len(historyqueue)>4:
            historyqueue.pop(0)
        
        return my_move

# ==================== TESTING HELPERS ====================

def test_student_agent():
    """
    Basic test to verify the student agent can be created and make moves.
    """
    print("Testing StudentAgent...")
    
    try:
        from gameEngine import default_start_board, DEFAULT_ROWS, DEFAULT_COLS
        
        rows, cols = DEFAULT_ROWS, DEFAULT_COLS
        score_cols = score_cols_for(cols)
        board = default_start_board(rows, cols)
        
        agent = StudentAgent("circle")
        move = agent.choose(board, rows, cols, score_cols,1.0,1.0)
        
        if move:
            print("✓ Agent successfully generated a move")
        else:
            print("✗ Agent returned no move")
    
    except ImportError:
        agent = StudentAgent("circle")
        print("✓ StudentAgent created successfully")

if __name__ == "__main__":
    # Run basic test when file is executed directly
    test_student_agent()

