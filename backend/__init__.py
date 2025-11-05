"""
Chess Engine Testing Framework
Backend Package
"""

__version__ = "1.0.0"
__author__ = "Chess Engine Testing Framework Contributors"

from .uci_interface import UCIEngine
from .engine_manager import EngineManager, EngineConfig
from .match import Match, MatchResult
from .tournament import Tournament, TournamentStats
from .uci_validator import UCIValidator, validate_engine
from .opening_book import OpeningSuite, PolyglotBook

__all__ = [
    'UCIEngine',
    'EngineManager',
    'EngineConfig',
    'Match',
    'MatchResult',
    'Tournament',
    'TournamentStats',
    'UCIValidator',
    'validate_engine',
    'OpeningSuite',
    'PolyglotBook'
]
