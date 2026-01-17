"""Simple Snake AI - intentionally inefficient for evolution testing.

This is a deliberately bad implementation that evolution agents should improve.
The AI makes random moves most of the time, leading to low scores.
"""

import random
from typing import Literal
from collections import deque

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

        Advanced implementation:
        1. Find shortest path to food.
        2. If path exists, simulate it and check if tail is reachable.
        3. If safe, follow path to food.
        4. Otherwise, follow the tail.
        5. If still no move, pick the move with most free space.
        """
        head = game.get_head()
        food = game.food
        grid_size = game.grid_size
        snake = game.snake
        snake_set = set(snake)
        
        move_offsets = {
            "up": (-1, 0),
            "down": (1, 0),
            "left": (0, -1),
            "right": (0, 1)
        }
        opposites = {"up": "down", "down": "up", "left": "right", "right": "left"}

        def get_path(start, target, current_snake):
            current_snake_set = set(current_snake)
            queue = [(start, [])]
            visited = {start}
            while queue:
                (curr_x, curr_y), path = queue.pop(0)
                if (curr_x, curr_y) == target:
                    return path
                for move, (dx, dy) in move_offsets.items():
                    next_pos = (curr_x + dx, curr_y + dy)
                    if (0 <= next_pos[0] < grid_size and
                        0 <= next_pos[1] < grid_size and
                        next_pos not in current_snake_set and
                        next_pos not in visited):
                        visited.add(next_pos)
                        queue.append((next_pos, path + [move]))
            return None

        def is_path_safe(path_to_food):
            # Simulate following the path to food
            temp_snake = list(snake)
            for move in path_to_food:
                dx, dy = move_offsets[move]
                new_head = (temp_snake[0][0] + dx, temp_snake[0][1] + dy)
                temp_snake.insert(0, new_head)
                if new_head == food:
                    # Snake grows, tail stays
                    pass
                else:
                    temp_snake.pop()
            
            # After reaching food, can we reach the tail?
            # The tail is temp_snake[-1]
            # We need to be able to reach it to not get trapped.
            # Use a simplified snake set for the check
            return get_path(temp_snake[0], temp_snake[-1], temp_snake[:-1]) is not None

        # 1. Try to find shortest path to food
        path_to_food = get_path(head, food, snake)
        if path_to_food:
            if is_path_safe(path_to_food):
                return path_to_food[0]

        # 2. If no safe path to food, try to follow tail
        # To follow tail, we want to reach the position where the tail currently is.
        # As we move, the tail will move away, so this is generally safe.
        path_to_tail = get_path(head, snake[-1], snake[:-1])
        if path_to_tail:
            return path_to_tail[0]

        # 3. Fallback: move to the neighbor that has the most free space
        best_move = None
        max_free_space = -1
        
        for move, (dx, dy) in move_offsets.items():
            if move == opposites.get(game.direction):
                continue
            next_pos = (head[0] + dx, head[1] + dy)
            if (0 <= next_pos[0] < grid_size and
                0 <= next_pos[1] < grid_size and
                next_pos not in snake_set):
                
                # Count free space using BFS
                free_space = 0
                q = [next_pos]
                v = {next_pos} | snake_set
                while q:
                    curr = q.pop(0)
                    free_space += 1
                    for _, (mdx, mdy) in move_offsets.items():
                        np = (curr[0] + mdx, curr[1] + mdy)
                        if (0 <= np[0] < grid_size and
                            0 <= np[1] < grid_size and
                            np not in v):
                            v.add(np)
                            q.append(np)
                
                if free_space > max_free_space:
                    max_free_space = free_space
                    best_move = move
        
        if best_move:
            return best_move
            
        return game.direction

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
