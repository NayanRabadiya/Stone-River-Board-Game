# Stones and Rivers Game

This repository contains the code supporting the code for Agent and Engine for the River and Stones.


## Rules
You can find the documentation to get all the rules of the game.

## Dependencies
- Python 3.9
- Pygame
- Numpy 
- Scipy


## Setting up the Environment
```sh
conda create --name stones_river python=3.9
conda activate stones_river
pip install -r requirements.txt
```

## Run Instructions
Here are the instructions used to match ai or human players against each other.


## Main Files
- `gameEngine.py`: It is an instance of the game. It can be run locally on your environment. You can run in GUI or CLI mode.
- `agent.py`: It consists of the implementations of the Random Agent. 


### Human vs Human
```sh
python gameEngine.py --mode hvh
```
### Human vs AI

```sh
python gameEngine.py --mode hvai --circle random
```
### AI vs AI

```sh
python gameEngine.py --mode aivai --circle random --square student
```

### No GUI
```sh
python gameEngine.py --mode aivai --circle random --square student --nogui
```
