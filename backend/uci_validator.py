"""
UCI Protocol Validator
Tests engine UCI compatibility and identifies issues
"""

import logging
from typing import Dict, List
from pathlib import Path

from .uci_interface import UCIEngine

logger = logging.getLogger(__name__)


class UCIValidator:
    """
    Validates UCI protocol implementation

    Tests:
    - Basic UCI handshake
    - isready response
    - Position setting
    - Search functionality
    - Time management
    """

    def __init__(self, engine_path: str):
        """
        Initialize validator

        Args:
            engine_path: Path to engine executable
        """
        self.engine_path = Path(engine_path)
        self.results: Dict[str, bool] = {}
        self.issues: List[str] = []
        self.warnings: List[str] = []

    def validate(self) -> Dict:
        """
        Run full validation suite

        Returns:
            Dict with results, issues, and warnings
        """
        logger.info(f"Starting UCI validation for: {self.engine_path}")

        try:
            with UCIEngine(str(self.engine_path)) as engine:
                self._test_startup(engine)
                self._test_initialization(engine)
                self._test_position(engine)
                self._test_search(engine)
                self._test_time_management(engine)
                self._test_stop_command(engine)

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            self.issues.append(f"Critical error: {e}")

        # Calculate score
        passed = sum(1 for result in self.results.values() if result)
        total = len(self.results)
        score = (passed / total * 100) if total > 0 else 0

        return {
            "engine": self.engine_path.name,
            "score": score,
            "passed": passed,
            "total": total,
            "results": self.results,
            "issues": self.issues,
            "warnings": self.warnings,
            "compatible": len(self.issues) == 0 and score >= 70
        }

    def _test_startup(self, engine: UCIEngine):
        """Test engine startup"""
        test_name = "Engine Startup"
        try:
            success = engine.process is not None and engine.running
            self.results[test_name] = success

            if not success:
                self.issues.append("Engine failed to start")
            else:
                logger.info(f"✓ {test_name}")

        except Exception as e:
            self.results[test_name] = False
            self.issues.append(f"Startup error: {e}")

    def _test_initialization(self, engine: UCIEngine):
        """Test UCI initialization"""
        test_name = "UCI Initialization"
        try:
            success = engine.initialize()
            self.results[test_name] = success

            if not success:
                self.issues.append("Engine did not respond with 'uciok'")
            else:
                logger.info(f"✓ {test_name}")
                logger.info(f"  Engine: {engine.name} by {engine.author}")

                # Check for common options
                if "Hash" not in engine.options:
                    self.warnings.append("No Hash option found")
                if "Threads" not in engine.options:
                    self.warnings.append("No Threads option found")

                # Check mate search support
                if not engine.supports_mate_search:
                    self.warnings.append("No mate search support detected")

        except Exception as e:
            self.results[test_name] = False
            self.issues.append(f"Initialization error: {e}")

    def _test_position(self, engine: UCIEngine):
        """Test position command"""
        test_name = "Position Command"
        try:
            # Test startpos
            engine.set_position()
            ready1 = engine.is_ready(timeout=5)

            # Test with moves
            engine.set_position(moves=["e2e4", "e7e5"])
            ready2 = engine.is_ready(timeout=5)

            # Test FEN position
            fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
            engine.set_position(fen=fen)
            ready3 = engine.is_ready(timeout=5)

            success = ready1 and ready2 and ready3
            self.results[test_name] = success

            if not success:
                self.issues.append("Position command failed or engine not ready")
            else:
                logger.info(f"✓ {test_name}")

        except Exception as e:
            self.results[test_name] = False
            self.issues.append(f"Position test error: {e}")

    def _test_search(self, engine: UCIEngine):
        """Test search functionality"""
        test_name = "Search Functionality"
        try:
            engine.new_game()
            engine.set_position()

            # Test depth-limited search
            result = engine.go(depth=5)

            success = (
                result["bestmove"] is not None and
                len(result["bestmove"]) >= 4
            )

            self.results[test_name] = success

            if not success:
                self.issues.append("Search failed or no bestmove returned")
            else:
                logger.info(f"✓ {test_name}")
                logger.info(f"  Best move: {result['bestmove']}")

                # Check info lines
                if not result["info"]:
                    self.warnings.append("No info lines during search")

        except Exception as e:
            self.results[test_name] = False
            self.issues.append(f"Search test error: {e}")

    def _test_time_management(self, engine: UCIEngine):
        """Test time control"""
        test_name = "Time Management"
        try:
            engine.new_game()
            engine.set_position()

            # Test with time control (1 second)
            result = engine.go(wtime=1000, btime=1000)

            success = result["bestmove"] is not None

            self.results[test_name] = success

            if not success:
                self.issues.append("Time-controlled search failed")
            else:
                logger.info(f"✓ {test_name}")

        except Exception as e:
            self.results[test_name] = False
            self.issues.append(f"Time management test error: {e}")

    def _test_stop_command(self, engine: UCIEngine):
        """Test stop command"""
        test_name = "Stop Command"
        try:
            engine.new_game()
            engine.set_position()

            # Start infinite search
            engine.go(infinite=True)

            import time
            time.sleep(0.5)

            # Stop search
            engine.stop()

            # Check engine is ready
            ready = engine.is_ready(timeout=5)

            self.results[test_name] = ready

            if not ready:
                self.warnings.append("Stop command may not work properly")
            else:
                logger.info(f"✓ {test_name}")

        except Exception as e:
            self.results[test_name] = False
            self.warnings.append(f"Stop command test issue: {e}")


def validate_engine(engine_path: str) -> Dict:
    """
    Convenience function to validate an engine

    Args:
        engine_path: Path to engine executable

    Returns:
        Validation results dict
    """
    validator = UCIValidator(engine_path)
    return validator.validate()


def validate_all_engines(engines_dir: str = "Engines") -> List[Dict]:
    """
    Validate all engines in directory

    Args:
        engines_dir: Directory containing engine executables

    Returns:
        List of validation results
    """
    engines_path = Path(engines_dir)
    results = []

    if not engines_path.exists():
        logger.error(f"Engines directory not found: {engines_dir}")
        return results

    exe_files = list(engines_path.glob("*.exe"))
    logger.info(f"Found {len(exe_files)} engines to validate")

    for exe_file in exe_files:
        logger.info(f"\n{'='*60}")
        logger.info(f"Validating: {exe_file.name}")
        logger.info(f"{'='*60}")

        result = validate_engine(str(exe_file))
        results.append(result)

        # Print summary
        status = "✓ COMPATIBLE" if result["compatible"] else "✗ ISSUES FOUND"
        logger.info(f"\n{status} - Score: {result['score']:.1f}%")

        if result["issues"]:
            logger.warning("Issues:")
            for issue in result["issues"]:
                logger.warning(f"  - {issue}")

        if result["warnings"]:
            logger.info("Warnings:")
            for warning in result["warnings"]:
                logger.info(f"  - {warning}")

    return results
