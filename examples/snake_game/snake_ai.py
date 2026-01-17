"""Simple Snake AI - intentionally inefficient for evolution testing.

This is a deliberately bad implementation that evolution agents should improve.
The AI makes random moves most of the time, leading to low scores.
"""

import random
from typing import Literal

Move = Literal["up", "down", "left", "right"]

# Game constants
GRID_SIZE = 20
INITIAL_SNAKE_LENGTH = 3


class SnakeGame:
    """A simple Snake game implementation."""

    def __init__(self, grid_size: int = GRID_SIZE):
        self.grid_size = grid_size
        self.reset()

    def reset(self):
        """Reset the game state."""
        # Snake starts in the middle
        mid = self.grid_size // 2
        self.snake = [(mid, mid - i) for i in range(INITIAL_SNAKE_LENGTH)]
        self.direction = "right"
        self.food = self._spawn_food()
        self.score = 0
        self.game_over = False
        self.moves_without_food = 0
        self.max_moves_without_food = self.grid_size * self.grid_size

    def _spawn_food(self) -> tuple[int, int]:
        """Spawn food at a random location not occupied by the snake."""
        while True:
            food = (random.randint(0, self.grid_size - 1),
                    random.randint(0, self.grid_size - 1))
            if food not in self.snake:
                return food

    def get_head(self) -> tuple[int, int]:
        """Get the snake's head position."""
        return self.snake[0]

    def move(self, direction: Move) -> bool:
        """Move the snake in the given direction.

        Returns True if the game continues, False if game over.
        """
        if self.game_over:
            return False

        # Update direction (can't reverse)
        opposites = {"up": "down", "down": "up", "left": "right", "right": "left"}
        if direction != opposites.get(self.direction):
            self.direction = direction

        # Calculate new head position
        head_x, head_y = self.snake[0]
        if self.direction == "up":
            new_head = (head_x - 1, head_y)
        elif self.direction == "down":
            new_head = (head_x + 1, head_y)
        elif self.direction == "left":
            new_head = (head_x, head_y - 1)
        else:  # right
            new_head = (head_x, head_y + 1)

        # Check for collisions
        if (new_head[0] < 0 or new_head[0] >= self.grid_size or
            new_head[1] < 0 or new_head[1] >= self.grid_size or
            new_head in self.snake):
            self.game_over = True
            return False

        # Move snake
        self.snake.insert(0, new_head)

        # Check for food
        if new_head == self.food:
            self.score += 10
            self.food = self._spawn_food()
            self.moves_without_food = 0
        else:
            self.snake.pop()
            self.moves_without_food += 1

        # Prevent infinite loops
        if self.moves_without_food > self.max_moves_without_food:
            self.game_over = True
            return False

        return True


class SnakeAI:
    """AI controller for the Snake game.

    This is an intentionally BAD implementation that mostly makes random moves.
    Evolution agents should improve this to get higher scores.
    """

    def __init__(self):
        pass

    def get_move(self, game: SnakeGame) -> Move:
        """Decide the next move for the snake.

        Improved implementation: Uses BFS to find the shortest path to food,
        falling back to a greedy safe move if no path exists.
        """
        head = game.get_head()
        food = game.food
        grid_size = game.grid_size
        snake_set = set(game.snake)

        # BFS to find shortest path to food
        queue = [(head, [])]
        visited = {head}
        
        opposites = {"up": "down", "down": "up", "left": "right", "right": "left"}
        
        move_offsets = {
            "up": (-1, 0),
            "down": (1, 0),
            "left": (0, -1),
            "right": (0, 1)
        }

        while queue:
            (curr_x, curr_y), path = queue.pop(0)
            
            if (curr_x, curr_y) == food:
                if path:
                    return path[0]
            
            for move, (dx, dy) in move_offsets.items():
                # Cannot reverse direction on the first move
                if not path and move == opposites.get(game.direction):
                    continue
                
                next_pos = (curr_x + dx, curr_y + dy)
                
                if (0 <= next_pos[0] < grid_size and
                    0 <= next_pos[1] < grid_size and
                    next_pos not in snake_set and
                    next_pos not in visited):
                    visited.add(next_pos)
                    queue.append((next_pos, path + [move]))

        # Fallback: Greedy safe move
        head_x, head_y = head
        safe_moves = []
        for move, (dx, dy) in move_offsets.items():
            if move == opposites.get(game.direction):
                continue
            next_pos = (head_x + dx, head_y + dy)
            if (0 <= next_pos[0] < grid_size and
                0 <= next_pos[1] < grid_size and
                next_pos not in snake_set):
                safe_moves.append((move, next_pos))

        if not safe_moves:
            return game.direction

        best_move = safe_moves[0][0]
        min_dist = float('inf')
        for move, (nx, ny) in safe_moves:
            dist = abs(nx - food[0]) + abs(ny - food[1])
            if dist < min_dist:
                min_dist = dist
                best_move = move
        return best_move

    def play_game(self, grid_size: int = GRID_SIZE) -> int:
        """Play a complete game and return the final score."""
        game = SnakeGame(grid_size)

        while not game.game_over:
            move = self.get_move(game)
            game.move(move)

        return game.score


def benchmark(num_games: int = 10, grid_size: int = GRID_SIZE) -> float:
    """Run benchmark games and return average score."""
    ai = SnakeAI()
    total_score = 0

    for _ in range(num_games):
        score = ai.play_game(grid_size)
        total_score += score

    return total_score / num_games


if __name__ == "__main__":
    # Run a quick test
    avg_score = benchmark(num_games=10)
    print(f"Average score over 10 games: {avg_score}")
