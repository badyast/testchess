"""
Match System
Manages games between two chess engines
"""

import logging
import time
import chess
import chess.pgn
from typing import Optional, Dict, Callable
from datetime import datetime
from pathlib import Path

from .uci_interface import UCIEngine

logger = logging.getLogger(__name__)


class MatchResult:
    """Container for match results"""

    def __init__(self):
        self.winner: Optional[str] = None  # "white", "black", "draw"
        self.reason: str = ""
        self.moves: list = []
        self.pgn: str = ""
        self.time_white: int = 0
        self.time_black: int = 0
        self.nodes_white: int = 0
        self.nodes_black: int = 0


class Match:
    """
    Chess match between two engines

    Features:
    - Full game management
    - Time control
    - Move validation
    - PGN export
    - Live updates via callback
    """

    def __init__(self,
                 white_engine_path: str,
                 black_engine_path: str,
                 time_control: int = 60000,  # 60 seconds per side
                 increment: int = 0,
                 opening_moves: Optional[list] = None,
                 max_moves: int = 200):
        """
        Initialize match

        Args:
            white_engine_path: Path to white engine
            black_engine_path: Path to black engine
            time_control: Time per side in milliseconds
            increment: Increment per move in milliseconds
            opening_moves: List of opening moves to play
            max_moves: Maximum moves before draw
        """
        self.white_engine_path = white_engine_path
        self.black_engine_path = black_engine_path
        self.time_control = time_control
        self.increment = increment
        self.opening_moves = opening_moves or []
        self.max_moves = max_moves

        self.board = chess.Board()
        self.move_times = []
        self.white_engine: Optional[UCIEngine] = None
        self.black_engine: Optional[UCIEngine] = None

        # Time tracking
        self.time_white = time_control
        self.time_black = time_control

        # Statistics
        self.nodes_white = 0
        self.nodes_black = 0

        logger.info(f"Match created: {Path(white_engine_path).stem} vs {Path(black_engine_path).stem}")

    def play(self, update_callback: Optional[Callable] = None) -> MatchResult:
        """
        Play the match

        Args:
            update_callback: Function called after each move with (board, move, info)

        Returns:
            MatchResult object
        """
        result = MatchResult()

        try:
            # Start engines
            logger.info("Starting engines...")
            self.white_engine = UCIEngine(self.white_engine_path)
            self.black_engine = UCIEngine(self.black_engine_path)

            if not self.white_engine.start() or not self.black_engine.start():
                raise RuntimeError("Failed to start engines")

            if not self.white_engine.initialize() or not self.black_engine.initialize():
                raise RuntimeError("Failed to initialize engines")

            # New game
            self.white_engine.new_game()
            self.black_engine.new_game()

            # Play opening moves
            for move_uci in self.opening_moves:
                try:
                    move = chess.Move.from_uci(move_uci)
                    if move in self.board.legal_moves:
                        self.board.push(move)
                        logger.info(f"Opening move: {move_uci}")
                    else:
                        logger.warning(f"Illegal opening move: {move_uci}")
                        break
                except:
                    logger.error(f"Invalid opening move: {move_uci}")
                    break

            # Play game
            move_count = 0
            while not self.board.is_game_over() and move_count < self.max_moves:
                current_engine = self.white_engine if self.board.turn == chess.WHITE else self.black_engine
                current_time = self.time_white if self.board.turn == chess.WHITE else self.time_black
                opponent_time = self.time_black if self.board.turn == chess.WHITE else self.time_white

                # Set position
                move_list = [move.uci() for move in self.board.move_stack]
                current_engine.set_position(moves=move_list)

                # Get move
                start_time = time.time()
                move_result = current_engine.go(
                    wtime=self.time_white if self.board.turn == chess.WHITE else opponent_time,
                    btime=self.time_black if self.board.turn == chess.BLACK else opponent_time,
                    winc=self.increment,
                    binc=self.increment
                )
                elapsed = int((time.time() - start_time) * 1000)

                # Check for move
                if not move_result["bestmove"]:
                    logger.error("Engine returned no move")
                    result.winner = "black" if self.board.turn == chess.WHITE else "white"
                    result.reason = "Engine failure"
                    break

                # Parse and validate move
                try:
                    move = chess.Move.from_uci(move_result["bestmove"])
                except:
                    logger.error(f"Invalid move format: {move_result['bestmove']}")
                    result.winner = "black" if self.board.turn == chess.WHITE else "white"
                    result.reason = "Illegal move"
                    break

                if move not in self.board.legal_moves:
                    logger.error(f"Illegal move: {move}")
                    result.winner = "black" if self.board.turn == chess.WHITE else "white"
                    result.reason = "Illegal move"
                    break

                # Make move
                self.board.push(move)
                move_count += 1

                # Update time
                if self.board.turn == chess.BLACK:  # Just moved white
                    self.time_white = max(0, self.time_white - elapsed + self.increment)
                else:  # Just moved black
                    self.time_black = max(0, self.time_black - elapsed + self.increment)

                # Track statistics
                if move_result["info"]:
                    last_info = move_result["info"][-1]
                    nodes = last_info.get("nodes", 0)
                    if self.board.turn == chess.BLACK:
                        self.nodes_white += nodes
                    else:
                        self.nodes_black += nodes

                # Log move
                color = "White" if self.board.turn == chess.BLACK else "Black"
                logger.info(f"Move {move_count}: {color} plays {move.uci()} "
                           f"(time: {elapsed}ms, remaining: {current_time - elapsed}ms)")

                # Callback for live updates
                if update_callback:
                    try:
                        update_callback(self.board.copy(), move, move_result)
                    except Exception as e:
                        logger.warning(f"Update callback error: {e}")

                # Check time forfeit
                if self.time_white <= 0:
                    result.winner = "black"
                    result.reason = "Time forfeit"
                    break
                if self.time_black <= 0:
                    result.winner = "white"
                    result.reason = "Time forfeit"
                    break

            # Determine result if not already set
            if not result.winner:
                if self.board.is_checkmate():
                    result.winner = "white" if self.board.turn == chess.BLACK else "black"
                    result.reason = "Checkmate"
                elif self.board.is_stalemate():
                    result.winner = "draw"
                    result.reason = "Stalemate"
                elif self.board.is_insufficient_material():
                    result.winner = "draw"
                    result.reason = "Insufficient material"
                elif self.board.is_fifty_moves():
                    result.winner = "draw"
                    result.reason = "Fifty-move rule"
                elif self.board.is_repetition():
                    result.winner = "draw"
                    result.reason = "Threefold repetition"
                elif move_count >= self.max_moves:
                    result.winner = "draw"
                    result.reason = f"Maximum moves ({self.max_moves}) reached"
                else:
                    result.winner = "draw"
                    result.reason = "Game over"

            # Generate PGN
            result.moves = [move.uci() for move in self.board.move_stack]
            result.pgn = self._generate_pgn(result)
            result.time_white = self.time_white
            result.time_black = self.time_black
            result.nodes_white = self.nodes_white
            result.nodes_black = self.nodes_black

            logger.info(f"Match finished: {result.winner} - {result.reason}")
            logger.info(f"Total moves: {len(result.moves)}")

        except Exception as e:
            logger.error(f"Match error: {e}")
            result.winner = "error"
            result.reason = str(e)

        finally:
            # Cleanup
            if self.white_engine:
                self.white_engine.quit()
            if self.black_engine:
                self.black_engine.quit()

        return result

    def _generate_pgn(self, result: MatchResult) -> str:
        """Generate PGN string for the game"""
        game = chess.pgn.Game()

        # Set headers
        game.headers["Event"] = "Engine Match"
        game.headers["Date"] = datetime.now().strftime("%Y.%m.%d")
        game.headers["White"] = Path(self.white_engine_path).stem
        game.headers["Black"] = Path(self.black_engine_path).stem

        # Set result
        if result.winner == "white":
            game.headers["Result"] = "1-0"
        elif result.winner == "black":
            game.headers["Result"] = "0-1"
        else:
            game.headers["Result"] = "1/2-1/2"

        game.headers["Termination"] = result.reason
        game.headers["TimeControl"] = f"{self.time_control // 1000}+{self.increment // 1000}"

        # Add moves
        node = game
        board = chess.Board()
        for move_uci in result.moves:
            try:
                move = chess.Move.from_uci(move_uci)
                node = node.add_variation(move)
                board.push(move)
            except:
                logger.warning(f"Could not add move to PGN: {move_uci}")
                break

        return str(game)

    def save_pgn(self, result: MatchResult, filename: str):
        """Save game to PGN file"""
        try:
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
            with open(filename, 'w') as f:
                f.write(result.pgn)
            logger.info(f"PGN saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save PGN: {e}")
