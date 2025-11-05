"""
Web Application
FastAPI backend for chess engine testing
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
import json

from engine_manager import EngineManager
from uci_validator import validate_engine
from match import Match
from tournament import Tournament
from opening_book import OpeningSuite

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="Chess Engine Testing Framework")

# Global engine manager
engine_manager = EngineManager()

# Active WebSocket connections
active_connections: List[WebSocket] = []


# Pydantic models
class EngineInfo(BaseModel):
    name: str
    path: str
    enabled: bool


class MatchRequest(BaseModel):
    white_engine: str
    black_engine: str
    time_control: int = 60000
    increment: int = 0


class TournamentRequest(BaseModel):
    name: str
    tournament_type: str
    engines: List[str]
    rounds: int = 1
    time_control: int = 60000
    increment: int = 0
    use_openings: bool = False


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting: {e}")


manager = ConnectionManager()


# API Endpoints

@app.get("/")
async def root():
    """Serve main page"""
    return FileResponse("frontend/index.html")


@app.get("/api/engines")
async def get_engines():
    """Get list of all engines"""
    engines = engine_manager.list_engines()
    return {
        "engines": [
            {
                "name": e.name,
                "path": e.path,
                "enabled": e.enabled,
                "time_control": e.time_control
            }
            for e in engines
        ]
    }


@app.get("/api/engines/{engine_name}")
async def get_engine_info(engine_name: str):
    """Get detailed engine information"""
    info = engine_manager.get_engine_info(engine_name)
    if not info:
        raise HTTPException(status_code=404, detail="Engine not found")
    return info


@app.post("/api/engines/discover")
async def discover_engines():
    """Discover engines in Engines directory"""
    engine_manager.discover_engines()
    engines = engine_manager.list_engines()
    return {
        "message": f"Discovered {len(engines)} engines",
        "engines": [e.name for e in engines]
    }


@app.post("/api/engines/{engine_name}/validate")
async def validate_engine_endpoint(engine_name: str):
    """Validate engine UCI compatibility"""
    config = engine_manager.get_engine(engine_name)
    if not config:
        raise HTTPException(status_code=404, detail="Engine not found")

    result = validate_engine(config.path)
    return result


@app.post("/api/match")
async def run_match(request: MatchRequest):
    """Run a match between two engines"""
    white_config = engine_manager.get_engine(request.white_engine)
    black_config = engine_manager.get_engine(request.black_engine)

    if not white_config or not black_config:
        raise HTTPException(status_code=404, detail="Engine not found")

    # Run match in background
    asyncio.create_task(run_match_async(
        white_config.path,
        black_config.path,
        request.time_control,
        request.increment
    ))

    return {
        "message": "Match started",
        "white": request.white_engine,
        "black": request.black_engine
    }


async def run_match_async(white_path: str, black_path: str, time_control: int, increment: int):
    """Run match and broadcast updates"""
    def update_callback(board, move, info):
        # Broadcast move update
        asyncio.create_task(manager.broadcast({
            "type": "move",
            "fen": board.fen(),
            "move": move.uci(),
            "turn": "white" if board.turn else "black"
        }))

    match = Match(
        white_engine_path=white_path,
        black_engine_path=black_path,
        time_control=time_control,
        increment=increment
    )

    await manager.broadcast({
        "type": "match_start",
        "white": Path(white_path).stem,
        "black": Path(black_path).stem
    })

    result = match.play(update_callback=update_callback)

    await manager.broadcast({
        "type": "match_end",
        "winner": result.winner,
        "reason": result.reason,
        "moves": len(result.moves),
        "pgn": result.pgn
    })


@app.post("/api/tournament")
async def run_tournament_endpoint(request: TournamentRequest):
    """Run a tournament"""
    # Validate engines
    for engine_name in request.engines:
        if not engine_manager.get_engine(engine_name):
            raise HTTPException(status_code=404, detail=f"Engine not found: {engine_name}")

    # Setup opening book
    opening_book = None
    if request.use_openings:
        suite = OpeningSuite()
        suite.add_common_openings()
        opening_book = [suite.get_random_opening() for _ in range(10)]

    # Create tournament
    tournament = Tournament(
        name=request.name,
        engine_manager=engine_manager,
        time_control=request.time_control,
        increment=request.increment,
        rounds=request.rounds,
        opening_book=opening_book
    )

    # Run tournament in background
    asyncio.create_task(run_tournament_async(tournament, request))

    return {
        "message": "Tournament started",
        "name": request.name,
        "type": request.tournament_type,
        "engines": request.engines
    }


async def run_tournament_async(tournament: Tournament, request: TournamentRequest):
    """Run tournament and broadcast updates"""
    def progress_callback(game_info, standings):
        asyncio.create_task(manager.broadcast({
            "type": "tournament_progress",
            "game": game_info,
            "standings": standings
        }))

    await manager.broadcast({
        "type": "tournament_start",
        "name": request.name,
        "engines": request.engines
    })

    if request.tournament_type == "roundrobin":
        results = tournament.run_round_robin(request.engines, update_callback=progress_callback)
    else:  # gauntlet
        test_engine = request.engines[0]
        opponents = request.engines[1:]
        results = tournament.run_gauntlet(test_engine, opponents, update_callback=progress_callback)

    tournament.save_results()

    await manager.broadcast({
        "type": "tournament_end",
        "results": results
    })


@app.get("/api/results")
async def get_results():
    """Get list of result files"""
    results_dir = Path("results")
    if not results_dir.exists():
        return {"results": []}

    files = []
    for file_path in results_dir.glob("**/*.json"):
        files.append({
            "name": file_path.stem,
            "path": str(file_path),
            "size": file_path.stat().st_size,
            "modified": file_path.stat().st_mtime
        })

    return {"results": files}


@app.get("/api/results/{result_name}")
async def get_result_detail(result_name: str):
    """Get specific result file"""
    result_file = Path(f"results/{result_name}.json")

    if not result_file.exists():
        raise HTTPException(status_code=404, detail="Result not found")

    with open(result_file) as f:
        data = json.load(f)

    return data


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Echo back for ping/pong
            await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Static files
app.mount("/static", StaticFiles(directory="frontend"), name="static")


if __name__ == "__main__":
    import uvicorn

    # Create directories
    Path("logs").mkdir(exist_ok=True)
    Path("results").mkdir(exist_ok=True)
    Path("config").mkdir(exist_ok=True)

    # Discover engines on startup
    engine_manager.discover_engines()

    logger.info("Starting Chess Engine Testing Framework Web Server")
    logger.info("Access at: http://localhost:8000")

    uvicorn.run(app, host="0.0.0.0", port=8000)
