"""
UCI Protocol Interface for Chess Engines
Robust implementation with Windows .exe support
Special handling for non-standard UCI implementations
"""

import subprocess
import threading
import queue
import time
import logging
from typing import Optional, Dict, List, Callable
from pathlib import Path
import re

logger = logging.getLogger(__name__)


class UCIEngine:
    """
    UCI Protocol Handler for Chess Engines

    Features:
    - Windows .exe support
    - Robust error handling
    - Timeout management
    - Non-standard UCI compatibility
    - Real-time output monitoring
    """

    def __init__(self, engine_path: str, timeout: int = 30):
        """
        Initialize UCI Engine

        Args:
            engine_path: Path to engine executable (.exe)
            timeout: Default timeout for commands in seconds
        """
        self.engine_path = Path(engine_path)
        if not self.engine_path.exists():
            raise FileNotFoundError(f"Engine not found: {engine_path}")

        self.timeout = timeout
        self.process: Optional[subprocess.Popen] = None
        self.output_queue: queue.Queue = queue.Queue()
        self.reader_thread: Optional[threading.Thread] = None
        self.running = False

        # Engine info
        self.name = "Unknown"
        self.author = "Unknown"
        self.options: Dict[str, Dict] = {}
        self.supports_mate_search = False

        logger.info(f"UCI Engine initialized: {self.engine_path}")

    def start(self) -> bool:
        """Start the engine process"""
        try:
            # Windows-specific: CREATE_NO_WINDOW flag to suppress console
            startupinfo = None
            if hasattr(subprocess, 'STARTUPINFO'):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self.process = subprocess.Popen(
                [str(self.engine_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                startupinfo=startupinfo
            )

            self.running = True

            # Start output reader thread
            self.reader_thread = threading.Thread(
                target=self._read_output,
                daemon=True
            )
            self.reader_thread.start()

            logger.info(f"Engine process started: PID {self.process.pid}")
            return True

        except Exception as e:
            logger.error(f"Failed to start engine: {e}")
            return False

    def _read_output(self):
        """Background thread to read engine output"""
        while self.running and self.process:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if line:
                    self.output_queue.put(line)
                    logger.debug(f"<< {line}")
            except Exception as e:
                logger.error(f"Error reading output: {e}")
                break

    def send_command(self, command: str):
        """Send command to engine"""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Engine not started")

        try:
            logger.debug(f">> {command}")
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()
        except Exception as e:
            logger.error(f"Error sending command '{command}': {e}")
            raise

    def read_until(self, expected: str, timeout: Optional[int] = None) -> List[str]:
        """
        Read output until expected string appears

        Args:
            expected: String to wait for (e.g., "uciok", "readyok")
            timeout: Timeout in seconds (uses default if None)

        Returns:
            List of output lines
        """
        if timeout is None:
            timeout = self.timeout

        lines = []
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                line = self.output_queue.get(timeout=0.1)
                lines.append(line)

                if expected in line:
                    return lines

            except queue.Empty:
                continue

        logger.warning(f"Timeout waiting for '{expected}'. Got {len(lines)} lines.")
        return lines

    def initialize(self) -> bool:
        """
        Initialize engine with UCI protocol

        Returns:
            True if successful, False otherwise
        """
        try:
            # Send UCI command
            self.send_command("uci")

            # Wait for uciok with extended timeout for slow engines
            lines = self.read_until("uciok", timeout=10)

            if not any("uciok" in line for line in lines):
                logger.error("Engine did not respond with 'uciok'")
                logger.error(f"Received: {lines}")
                return False

            # Parse engine info
            for line in lines:
                if line.startswith("id name"):
                    self.name = line[8:].strip()
                elif line.startswith("id author"):
                    self.author = line[10:].strip()
                elif line.startswith("option name"):
                    self._parse_option(line)

            logger.info(f"Engine initialized: {self.name} by {self.author}")
            logger.info(f"Options found: {len(self.options)}")

            # Check for mate search support (look for "mate" in option names)
            self.supports_mate_search = any(
                "mate" in opt.lower() for opt in self.options.keys()
            )

            # Test readyok
            if not self.is_ready():
                logger.warning("Engine not ready after initialization")
                return False

            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False

    def _parse_option(self, line: str):
        """Parse UCI option line"""
        # Example: option name Hash type spin default 16 min 1 max 65536
        match = re.match(r'option name (.+?)(?:\s+type\s+(.+))?$', line)
        if match:
            name = match.group(1).strip()
            rest = match.group(2) if match.group(2) else ""

            option_info = {"raw": line}

            # Parse type
            if "type" in rest:
                type_match = re.search(r'type (\w+)', rest)
                if type_match:
                    option_info["type"] = type_match.group(1)

            # Parse default
            if "default" in rest:
                default_match = re.search(r'default (\S+)', rest)
                if default_match:
                    option_info["default"] = default_match.group(1)

            self.options[name] = option_info

    def is_ready(self, timeout: int = 5) -> bool:
        """Check if engine is ready"""
        try:
            self.send_command("isready")
            lines = self.read_until("readyok", timeout=timeout)
            return any("readyok" in line for line in lines)
        except Exception as e:
            logger.error(f"is_ready failed: {e}")
            return False

    def new_game(self):
        """Start a new game"""
        self.send_command("ucinewgame")
        time.sleep(0.1)  # Give engine time to reset
        self.is_ready()

    def set_position(self, fen: Optional[str] = None, moves: Optional[List[str]] = None):
        """
        Set board position

        Args:
            fen: FEN string (None for starting position)
            moves: List of moves in UCI format (e.g., ["e2e4", "e7e5"])
        """
        if fen:
            cmd = f"position fen {fen}"
        else:
            cmd = "position startpos"

        if moves:
            cmd += " moves " + " ".join(moves)

        self.send_command(cmd)

    def go(self,
           wtime: Optional[int] = None,
           btime: Optional[int] = None,
           winc: Optional[int] = None,
           binc: Optional[int] = None,
           movestogo: Optional[int] = None,
           depth: Optional[int] = None,
           nodes: Optional[int] = None,
           movetime: Optional[int] = None,
           infinite: bool = False) -> Dict:
        """
        Start calculation

        Args:
            wtime: White time remaining (ms)
            btime: Black time remaining (ms)
            winc: White increment (ms)
            binc: Black increment (ms)
            movestogo: Moves to next time control
            depth: Search depth limit
            nodes: Node count limit
            movetime: Fixed time per move (ms)
            infinite: Search until 'stop' command

        Returns:
            Dict with bestmove and info
        """
        cmd_parts = ["go"]

        if infinite:
            cmd_parts.append("infinite")
        else:
            if wtime is not None:
                cmd_parts.append(f"wtime {wtime}")
            if btime is not None:
                cmd_parts.append(f"btime {btime}")
            if winc is not None:
                cmd_parts.append(f"winc {winc}")
            if binc is not None:
                cmd_parts.append(f"binc {binc}")
            if movestogo is not None:
                cmd_parts.append(f"movestogo {movestogo}")
            if depth is not None:
                cmd_parts.append(f"depth {depth}")
            if nodes is not None:
                cmd_parts.append(f"nodes {nodes}")
            if movetime is not None:
                cmd_parts.append(f"movetime {movetime}")

        cmd = " ".join(cmd_parts)
        self.send_command(cmd)

        # Wait for bestmove (with generous timeout)
        lines = self.read_until("bestmove", timeout=max(60, self.timeout))

        result = {
            "bestmove": None,
            "ponder": None,
            "info": [],
            "raw_output": lines
        }

        # Parse output
        for line in lines:
            if line.startswith("info"):
                result["info"].append(self._parse_info(line))
            elif line.startswith("bestmove"):
                parts = line.split()
                if len(parts) >= 2:
                    result["bestmove"] = parts[1]
                if len(parts) >= 4 and parts[2] == "ponder":
                    result["ponder"] = parts[3]

        return result

    def _parse_info(self, line: str) -> Dict:
        """Parse UCI info line"""
        info = {"raw": line}

        # Common patterns
        patterns = {
            "depth": r"depth (\d+)",
            "seldepth": r"seldepth (\d+)",
            "score_cp": r"score cp (-?\d+)",
            "score_mate": r"score mate (-?\d+)",
            "nodes": r"nodes (\d+)",
            "nps": r"nps (\d+)",
            "time": r"time (\d+)",
            "pv": r"pv (.+)$",
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, line)
            if match:
                value = match.group(1)
                if key == "pv":
                    info[key] = value.split()
                else:
                    info[key] = int(value) if value.lstrip('-').isdigit() else value

        return info

    def stop(self):
        """Stop current calculation"""
        self.send_command("stop")
        time.sleep(0.1)

    def quit(self):
        """Shutdown engine"""
        try:
            if self.process:
                self.send_command("quit")
                self.running = False

                # Wait for process to terminate
                self.process.wait(timeout=5)
                logger.info("Engine terminated gracefully")
        except Exception as e:
            logger.warning(f"Error during quit: {e}")
            if self.process:
                self.process.kill()
                logger.warning("Engine killed forcefully")

    def __enter__(self):
        """Context manager entry"""
        self.start()
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.quit()
