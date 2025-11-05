"""
Opening Book Manager
Supports Polyglot .bin format and custom opening suites
"""

import logging
import struct
import random
from pathlib import Path
from typing import List, Optional, Dict
import chess

logger = logging.getLogger(__name__)


class PolyglotBook:
    """
    Polyglot opening book reader

    Reads .bin files in Polyglot format
    """

    def __init__(self, book_path: str):
        """
        Initialize book

        Args:
            book_path: Path to .bin file
        """
        self.book_path = Path(book_path)
        if not self.book_path.exists():
            raise FileNotFoundError(f"Opening book not found: {book_path}")

        self.entries = []
        self._load_book()

        logger.info(f"Loaded opening book: {self.book_path.name} ({len(self.entries)} entries)")

    def _load_book(self):
        """Load Polyglot book entries"""
        try:
            with open(self.book_path, 'rb') as f:
                while True:
                    # Each entry is 16 bytes
                    data = f.read(16)
                    if len(data) < 16:
                        break

                    # Polyglot format:
                    # uint64 key (zobrist hash)
                    # uint16 move
                    # uint16 weight
                    # uint32 learn
                    key, move, weight, learn = struct.unpack('>QHHI', data)

                    self.entries.append({
                        'key': key,
                        'move': move,
                        'weight': weight,
                        'learn': learn
                    })

        except Exception as e:
            logger.error(f"Failed to load Polyglot book: {e}")
            self.entries = []

    def get_moves(self, board: chess.Board) -> List[Dict]:
        """
        Get available moves from book for position

        Args:
            board: Current board position

        Returns:
            List of move dicts with weights
        """
        # Calculate Polyglot zobrist hash
        key = self._polyglot_hash(board)

        # Find matching entries
        moves = []
        for entry in self.entries:
            if entry['key'] == key:
                try:
                    move = self._decode_move(entry['move'], board)
                    if move:
                        moves.append({
                            'move': move,
                            'weight': entry['weight']
                        })
                except:
                    continue

        return moves

    def get_random_move(self, board: chess.Board) -> Optional[chess.Move]:
        """
        Get weighted random move from book

        Args:
            board: Current position

        Returns:
            Move or None if no book move available
        """
        moves = self.get_moves(board)
        if not moves:
            return None

        # Weight-based selection
        total_weight = sum(m['weight'] for m in moves)
        if total_weight == 0:
            return random.choice(moves)['move']

        r = random.randint(0, total_weight - 1)
        cumulative = 0
        for move_data in moves:
            cumulative += move_data['weight']
            if r < cumulative:
                return move_data['move']

        return moves[0]['move']

    def _decode_move(self, encoded: int, board: chess.Board) -> Optional[chess.Move]:
        """
        Decode Polyglot move encoding

        Format:
        bits 0-5: destination square
        bits 6-11: origin square
        bits 12-14: promotion piece (if any)
        """
        to_square = encoded & 0x3F
        from_square = (encoded >> 6) & 0x3F
        promotion_piece = (encoded >> 12) & 0x7

        # Polyglot uses different square numbering
        # Need to convert from Polyglot to python-chess
        # (This is simplified - full implementation would need proper conversion)

        try:
            # Try to create move
            promotion = None
            if promotion_piece:
                promo_map = {1: chess.KNIGHT, 2: chess.BISHOP, 3: chess.ROOK, 4: chess.QUEEN}
                promotion = promo_map.get(promotion_piece)

            move = chess.Move(from_square, to_square, promotion=promotion)

            if move in board.legal_moves:
                return move

        except:
            pass

        return None

    def _polyglot_hash(self, board: chess.Board) -> int:
        """
        Calculate Polyglot zobrist hash
        (Simplified implementation)

        Note: Full Polyglot hash is complex. This is a placeholder.
        For production use, consider using python-chess polyglot module.
        """
        # This is a simplified hash - not actual Polyglot format
        # In production, use chess.polyglot.zobrist_hash()
        return hash(board.fen()) & 0xFFFFFFFFFFFFFFFF


class OpeningSuite:
    """
    Opening suite manager

    Manages collections of opening lines for tournaments
    """

    def __init__(self):
        self.openings: List[Dict] = []

    def load_from_pgn(self, pgn_path: str, max_moves: int = 10):
        """
        Load openings from PGN file

        Args:
            pgn_path: Path to PGN file
            max_moves: Maximum moves to extract per game
        """
        import chess.pgn

        path = Path(pgn_path)
        if not path.exists():
            logger.error(f"PGN file not found: {pgn_path}")
            return

        try:
            with open(pgn_path) as f:
                while True:
                    game = chess.pgn.read_game(f)
                    if game is None:
                        break

                    moves = []
                    board = game.board()
                    for i, move in enumerate(game.mainline_moves()):
                        if i >= max_moves:
                            break
                        moves.append(move.uci())

                    if moves:
                        opening_name = game.headers.get("Opening", "Unknown")
                        self.openings.append({
                            "name": opening_name,
                            "moves": moves
                        })

            logger.info(f"Loaded {len(self.openings)} openings from {pgn_path}")

        except Exception as e:
            logger.error(f"Failed to load openings from PGN: {e}")

    def load_from_epd(self, epd_path: str):
        """
        Load openings from EPD file

        Args:
            epd_path: Path to EPD file
        """
        path = Path(epd_path)
        if not path.exists():
            logger.error(f"EPD file not found: {epd_path}")
            return

        try:
            with open(epd_path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue

                    # Parse EPD
                    parts = line.split(';')
                    fen = parts[0].strip()

                    # Convert FEN to moves from startpos
                    # (Simplified - actual implementation would track moves)
                    self.openings.append({
                        "name": "EPD Position",
                        "fen": fen,
                        "moves": []
                    })

            logger.info(f"Loaded {len(self.openings)} positions from {epd_path}")

        except Exception as e:
            logger.error(f"Failed to load EPD: {e}")

    def add_opening(self, name: str, moves: List[str]):
        """
        Add opening manually

        Args:
            name: Opening name
            moves: List of moves in UCI format
        """
        self.openings.append({
            "name": name,
            "moves": moves
        })

    def add_common_openings(self):
        """Add some common openings"""
        common = [
            ("Italian Game", ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4"]),
            ("Sicilian Defense", ["e2e4", "c7c5"]),
            ("French Defense", ["e2e4", "e7e6"]),
            ("Caro-Kann Defense", ["e2e4", "c7c6"]),
            ("Queen's Gambit", ["d2d4", "d7d5", "c2c4"]),
            ("King's Indian Defense", ["d2d4", "g8f6", "c2c4", "g7g6"]),
            ("Ruy Lopez", ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5"]),
            ("Scotch Game", ["e2e4", "e7e5", "g1f3", "b8c6", "d2d4"]),
            ("English Opening", ["c2c4"]),
            ("Réti Opening", ["g1f3"]),
        ]

        for name, moves in common:
            self.add_opening(name, moves)

        logger.info(f"Added {len(common)} common openings")

    def get_random_opening(self) -> List[str]:
        """
        Get random opening

        Returns:
            List of moves in UCI format
        """
        if not self.openings:
            return []

        opening = random.choice(self.openings)
        return opening.get("moves", [])

    def get_all_openings(self) -> List[Dict]:
        """Get all openings"""
        return self.openings


# Convenience function for python-chess polyglot support
def load_polyglot_book(book_path: str):
    """
    Load Polyglot book using python-chess

    Args:
        book_path: Path to .bin file

    Returns:
        chess.polyglot.MemoryMappedReader or None
    """
    try:
        import chess.polyglot
        return chess.polyglot.open_reader(book_path)
    except Exception as e:
        logger.warning(f"Could not load book with python-chess polyglot: {e}")
        logger.info("Falling back to custom reader")
        return PolyglotBook(book_path)
