"""
Tournament System
Manages tournaments between multiple engines
"""

import logging
import json
from typing import List, Dict, Optional, Callable
from pathlib import Path
from datetime import datetime
from itertools import combinations
import random

from .match import Match, MatchResult
from .engine_manager import EngineManager, EngineConfig

logger = logging.getLogger(__name__)


class TournamentStats:
    """Tournament statistics for an engine"""

    def __init__(self, engine_name: str):
        self.engine_name = engine_name
        self.games_played = 0
        self.wins = 0
        self.losses = 0
        self.draws = 0
        self.points = 0.0  # Win=1, Draw=0.5, Loss=0
        self.wins_as_white = 0
        self.wins_as_black = 0
        self.total_nodes = 0

    def add_result(self, result: str, color: str, nodes: int = 0):
        """
        Add game result

        Args:
            result: "win", "loss", "draw"
            color: "white" or "black"
            nodes: Nodes searched
        """
        self.games_played += 1
        self.total_nodes += nodes

        if result == "win":
            self.wins += 1
            self.points += 1.0
            if color == "white":
                self.wins_as_white += 1
            else:
                self.wins_as_black += 1
        elif result == "loss":
            self.losses += 1
        elif result == "draw":
            self.draws += 1
            self.points += 0.5

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "engine": self.engine_name,
            "games": self.games_played,
            "wins": self.wins,
            "losses": self.losses,
            "draws": self.draws,
            "points": self.points,
            "wins_white": self.wins_as_white,
            "wins_black": self.wins_as_black,
            "nodes": self.total_nodes,
            "score_percentage": (self.points / self.games_played * 100) if self.games_played > 0 else 0
        }


class Tournament:
    """
    Tournament organizer

    Supports:
    - Round-Robin (all vs all)
    - Gauntlet (one vs all)
    - Swiss System (planned)
    """

    def __init__(self,
                 name: str,
                 engine_manager: EngineManager,
                 time_control: int = 60000,
                 increment: int = 0,
                 rounds: int = 1,
                 opening_book: Optional[List[List[str]]] = None):
        """
        Initialize tournament

        Args:
            name: Tournament name
            engine_manager: Engine manager instance
            time_control: Time per side (ms)
            increment: Increment per move (ms)
            rounds: Number of rounds
            opening_book: List of opening move sequences
        """
        self.name = name
        self.engine_manager = engine_manager
        self.time_control = time_control
        self.increment = increment
        self.rounds = rounds
        self.opening_book = opening_book or []

        self.stats: Dict[str, TournamentStats] = {}
        self.games: List[Dict] = []
        self.current_game = 0
        self.total_games = 0

        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

        logger.info(f"Tournament created: {name}")

    def run_round_robin(self,
                       engine_names: List[str],
                       update_callback: Optional[Callable] = None) -> Dict:
        """
        Run round-robin tournament (all vs all)

        Args:
            engine_names: List of engine names to include
            update_callback: Called after each game with game result

        Returns:
            Tournament results dict
        """
        logger.info(f"Starting Round-Robin tournament: {self.name}")
        logger.info(f"Engines: {', '.join(engine_names)}")
        logger.info(f"Rounds: {self.rounds}")

        self.start_time = datetime.now()

        # Initialize stats
        for engine_name in engine_names:
            self.stats[engine_name] = TournamentStats(engine_name)

        # Generate pairings
        pairings = list(combinations(engine_names, 2))
        self.total_games = len(pairings) * self.rounds * 2  # Each pairing plays twice (colors reversed)

        logger.info(f"Total games to play: {self.total_games}")

        # Play rounds
        for round_num in range(self.rounds):
            logger.info(f"\n{'='*60}")
            logger.info(f"ROUND {round_num + 1}/{self.rounds}")
            logger.info(f"{'='*60}")

            for white_name, black_name in pairings:
                # Get engine configs
                white_config = self.engine_manager.get_engine(white_name)
                black_config = self.engine_manager.get_engine(black_name)

                if not white_config or not black_config:
                    logger.error(f"Engine not found: {white_name} or {black_name}")
                    continue

                # Select opening if available
                opening = random.choice(self.opening_book) if self.opening_book else []

                # Game 1: White vs Black
                logger.info(f"\nGame {self.current_game + 1}/{self.total_games}: "
                          f"{white_name} (White) vs {black_name} (Black)")

                self._play_game(white_config, black_config, opening, update_callback)

                # Game 2: Colors reversed
                logger.info(f"\nGame {self.current_game + 1}/{self.total_games}: "
                          f"{black_name} (White) vs {white_name} (Black)")

                self._play_game(black_config, white_config, opening, update_callback)

        self.end_time = datetime.now()
        return self.get_results()

    def run_gauntlet(self,
                    test_engine: str,
                    opponent_engines: List[str],
                    update_callback: Optional[Callable] = None) -> Dict:
        """
        Run gauntlet tournament (one engine vs all others)

        Args:
            test_engine: Engine to test
            opponent_engines: List of opponent engine names
            update_callback: Called after each game

        Returns:
            Tournament results dict
        """
        logger.info(f"Starting Gauntlet tournament: {self.name}")
        logger.info(f"Test engine: {test_engine}")
        logger.info(f"Opponents: {', '.join(opponent_engines)}")

        self.start_time = datetime.now()

        # Initialize stats
        all_engines = [test_engine] + opponent_engines
        for engine_name in all_engines:
            self.stats[engine_name] = TournamentStats(engine_name)

        self.total_games = len(opponent_engines) * self.rounds * 2

        logger.info(f"Total games to play: {self.total_games}")

        # Play rounds
        for round_num in range(self.rounds):
            logger.info(f"\n{'='*60}")
            logger.info(f"ROUND {round_num + 1}/{self.rounds}")
            logger.info(f"{'='*60}")

            for opponent_name in opponent_engines:
                test_config = self.engine_manager.get_engine(test_engine)
                opponent_config = self.engine_manager.get_engine(opponent_name)

                if not test_config or not opponent_config:
                    logger.error(f"Engine not found")
                    continue

                opening = random.choice(self.opening_book) if self.opening_book else []

                # Game 1: Test engine as White
                logger.info(f"\nGame {self.current_game + 1}/{self.total_games}: "
                          f"{test_engine} (White) vs {opponent_name} (Black)")

                self._play_game(test_config, opponent_config, opening, update_callback)

                # Game 2: Test engine as Black
                logger.info(f"\nGame {self.current_game + 1}/{self.total_games}: "
                          f"{opponent_name} (White) vs {test_engine} (Black)")

                self._play_game(opponent_config, test_config, opening, update_callback)

        self.end_time = datetime.now()
        return self.get_results()

    def _play_game(self,
                  white_config: EngineConfig,
                  black_config: EngineConfig,
                  opening: List[str],
                  callback: Optional[Callable]):
        """Play a single game"""
        try:
            match = Match(
                white_engine_path=white_config.path,
                black_engine_path=black_config.path,
                time_control=self.time_control,
                increment=self.increment,
                opening_moves=opening
            )

            result = match.play()

            # Update statistics
            white_stats = self.stats[white_config.name]
            black_stats = self.stats[black_config.name]

            if result.winner == "white":
                white_stats.add_result("win", "white", result.nodes_white)
                black_stats.add_result("loss", "black", result.nodes_black)
            elif result.winner == "black":
                white_stats.add_result("loss", "white", result.nodes_white)
                black_stats.add_result("win", "black", result.nodes_black)
            else:  # draw
                white_stats.add_result("draw", "white", result.nodes_white)
                black_stats.add_result("draw", "black", result.nodes_black)

            # Store game info
            game_info = {
                "game_number": self.current_game + 1,
                "white": white_config.name,
                "black": black_config.name,
                "result": result.winner,
                "reason": result.reason,
                "moves": len(result.moves),
                "pgn": result.pgn
            }
            self.games.append(game_info)

            # Save PGN
            pgn_file = Path(f"results/{self.name}/game_{self.current_game + 1}.pgn")
            match.save_pgn(result, str(pgn_file))

            self.current_game += 1

            # Callback
            if callback:
                try:
                    callback(game_info, self.get_standings())
                except Exception as e:
                    logger.warning(f"Callback error: {e}")

        except Exception as e:
            logger.error(f"Game error: {e}")
            self.current_game += 1

    def get_standings(self) -> List[Dict]:
        """
        Get current tournament standings

        Returns:
            List of engine stats, sorted by points
        """
        standings = [stats.to_dict() for stats in self.stats.values()]
        standings.sort(key=lambda x: (x["points"], x["wins"]), reverse=True)
        return standings

    def get_results(self) -> Dict:
        """
        Get complete tournament results

        Returns:
            Dict with tournament info and results
        """
        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()

        return {
            "tournament": self.name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": duration,
            "time_control": f"{self.time_control // 1000}+{self.increment // 1000}",
            "rounds": self.rounds,
            "games_played": self.current_game,
            "games_total": self.total_games,
            "standings": self.get_standings(),
            "games": self.games
        }

    def save_results(self, filename: Optional[str] = None):
        """Save tournament results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"results/{self.name}_{timestamp}.json"

        results = self.get_results()

        try:
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
