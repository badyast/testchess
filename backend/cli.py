"""
Command Line Interface for Chess Engine Testing
"""

import argparse
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/chess_testing.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

from engine_manager import EngineManager
from uci_validator import validate_all_engines
from match import Match
from tournament import Tournament
from opening_book import OpeningSuite


def cmd_list_engines(args):
    """List all engines"""
    manager = EngineManager()

    engines = manager.list_engines()

    if not engines:
        print("No engines found. Run 'discover' command first.")
        return

    print(f"\n{'='*60}")
    print(f"{'Engine Name':<30} {'Status':<10} {'Path':<20}")
    print(f"{'='*60}")

    for engine in engines:
        status = "Enabled" if engine.enabled else "Disabled"
        print(f"{engine.name:<30} {status:<10} {engine.path:<20}")

    print(f"{'='*60}")
    print(f"Total: {len(engines)} engines\n")


def cmd_discover(args):
    """Discover engines"""
    print("Discovering engines in Engines/ directory...")
    manager = EngineManager()
    manager.discover_engines()
    print(f"Discovery complete. Found {len(manager.engines)} engines.")
    cmd_list_engines(args)


def cmd_validate(args):
    """Validate engines"""
    print("\n" + "="*60)
    print("UCI COMPATIBILITY VALIDATION")
    print("="*60 + "\n")

    results = validate_all_engines("Engines")

    print("\n" + "="*60)
    print("VALIDATION SUMMARY")
    print("="*60)

    for result in results:
        status_icon = "✓" if result["compatible"] else "✗"
        print(f"\n{status_icon} {result['engine']}")
        print(f"   Score: {result['score']:.1f}% ({result['passed']}/{result['total']} tests passed)")

        if result['issues']:
            print(f"   Issues:")
            for issue in result['issues']:
                print(f"      - {issue}")

        if result['warnings']:
            print(f"   Warnings:")
            for warning in result['warnings']:
                print(f"      - {warning}")

    print("\n" + "="*60 + "\n")


def cmd_match(args):
    """Run a match between two engines"""
    white_path = f"Engines/{args.white}.exe"
    black_path = f"Engines/{args.black}.exe"

    if not Path(white_path).exists():
        print(f"Error: White engine not found: {white_path}")
        return

    if not Path(black_path).exists():
        print(f"Error: Black engine not found: {black_path}")
        return

    print(f"\n{'='*60}")
    print(f"MATCH: {args.white} (White) vs {args.black} (Black)")
    print(f"Time Control: {args.time}ms + {args.increment}ms")
    print(f"{'='*60}\n")

    match = Match(
        white_engine_path=white_path,
        black_engine_path=black_path,
        time_control=args.time,
        increment=args.increment
    )

    result = match.play()

    print(f"\n{'='*60}")
    print(f"MATCH RESULT")
    print(f"{'='*60}")
    print(f"Winner: {result.winner}")
    print(f"Reason: {result.reason}")
    print(f"Moves: {len(result.moves)}")
    print(f"{'='*60}\n")

    # Save PGN
    pgn_file = f"results/match_{args.white}_vs_{args.black}.pgn"
    match.save_pgn(result, pgn_file)
    print(f"PGN saved to: {pgn_file}\n")


def cmd_tournament(args):
    """Run a tournament"""
    manager = EngineManager()

    # Get engines
    if args.engines:
        engine_names = args.engines.split(',')
    else:
        engines = manager.list_engines(enabled_only=True)
        engine_names = [e.name for e in engines]

    if len(engine_names) < 2:
        print("Error: Need at least 2 engines for tournament")
        return

    print(f"\n{'='*60}")
    print(f"TOURNAMENT: {args.name}")
    print(f"Type: {args.type}")
    print(f"Engines: {', '.join(engine_names)}")
    print(f"Rounds: {args.rounds}")
    print(f"Time Control: {args.time}ms + {args.increment}ms")
    print(f"{'='*60}\n")

    # Setup opening book
    opening_book = None
    if args.openings:
        suite = OpeningSuite()
        suite.add_common_openings()
        opening_book = [suite.get_random_opening() for _ in range(10)]

    # Create tournament
    tournament = Tournament(
        name=args.name,
        engine_manager=manager,
        time_control=args.time,
        increment=args.increment,
        rounds=args.rounds,
        opening_book=opening_book
    )

    # Callback for progress
    def progress_callback(game_info, standings):
        print(f"\nGame {game_info['game_number']} completed:")
        print(f"  {game_info['white']} vs {game_info['black']}: {game_info['result']}")
        print(f"\nCurrent Standings:")
        for i, stats in enumerate(standings[:5], 1):
            print(f"  {i}. {stats['engine']:<20} {stats['points']:.1f} pts "
                  f"(+{stats['wins']} ={stats['draws']} -{stats['losses']})")

    # Run tournament
    if args.type == "roundrobin":
        results = tournament.run_round_robin(engine_names, update_callback=progress_callback)
    elif args.type == "gauntlet":
        if len(engine_names) < 2:
            print("Error: Gauntlet needs at least 2 engines (1 test + opponents)")
            return
        test_engine = engine_names[0]
        opponents = engine_names[1:]
        results = tournament.run_gauntlet(test_engine, opponents, update_callback=progress_callback)
    else:
        print(f"Error: Unknown tournament type: {args.type}")
        return

    # Print final results
    print(f"\n{'='*60}")
    print(f"FINAL STANDINGS")
    print(f"{'='*60}")
    print(f"{'Rank':<6} {'Engine':<20} {'Points':<8} {'W-D-L':<12} {'Score%':<8}")
    print(f"{'='*60}")

    for i, stats in enumerate(results["standings"], 1):
        wdl = f"{stats['wins']}-{stats['draws']}-{stats['losses']}"
        print(f"{i:<6} {stats['engine']:<20} {stats['points']:<8.1f} {wdl:<12} {stats['score_percentage']:<8.1f}")

    print(f"{'='*60}\n")

    # Save results
    tournament.save_results()
    print(f"Tournament results saved to results/{args.name}_*.json\n")


def cmd_info(args):
    """Show engine information"""
    manager = EngineManager()
    info = manager.get_engine_info(args.engine)

    if not info:
        print(f"Error: Engine not found or failed to initialize: {args.engine}")
        return

    print(f"\n{'='*60}")
    print(f"ENGINE INFORMATION")
    print(f"{'='*60}")
    print(f"Name: {info['name']}")
    print(f"Author: {info['author']}")
    print(f"Path: {info['path']}")
    print(f"Mate Search: {'Yes' if info['supports_mate_search'] else 'No'}")
    print(f"\nUCI Options ({len(info['options'])}):")

    for name, opt_info in info['options'].items():
        print(f"  - {name}")
        if 'type' in opt_info:
            print(f"      Type: {opt_info['type']}")
        if 'default' in opt_info:
            print(f"      Default: {opt_info['default']}")

    print(f"{'='*60}\n")


def main():
    """Main entry point"""
    # Create necessary directories
    Path("logs").mkdir(exist_ok=True)
    Path("results").mkdir(exist_ok=True)
    Path("config").mkdir(exist_ok=True)

    parser = argparse.ArgumentParser(
        description="Chess Engine Testing Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # List command
    subparsers.add_parser('list', help='List all engines')

    # Discover command
    subparsers.add_parser('discover', help='Discover engines in Engines directory')

    # Validate command
    subparsers.add_parser('validate', help='Validate UCI compatibility of all engines')

    # Info command
    parser_info = subparsers.add_parser('info', help='Show engine information')
    parser_info.add_argument('engine', help='Engine name')

    # Match command
    parser_match = subparsers.add_parser('match', help='Run a match between two engines')
    parser_match.add_argument('white', help='White engine name (without .exe)')
    parser_match.add_argument('black', help='Black engine name (without .exe)')
    parser_match.add_argument('--time', type=int, default=60000, help='Time per side (ms)')
    parser_match.add_argument('--increment', type=int, default=0, help='Increment per move (ms)')

    # Tournament command
    parser_tournament = subparsers.add_parser('tournament', help='Run a tournament')
    parser_tournament.add_argument('name', help='Tournament name')
    parser_tournament.add_argument('--type', choices=['roundrobin', 'gauntlet'], default='roundrobin',
                                  help='Tournament type')
    parser_tournament.add_argument('--engines', help='Comma-separated engine names (default: all enabled)')
    parser_tournament.add_argument('--rounds', type=int, default=1, help='Number of rounds')
    parser_tournament.add_argument('--time', type=int, default=60000, help='Time per side (ms)')
    parser_tournament.add_argument('--increment', type=int, default=0, help='Increment per move (ms)')
    parser_tournament.add_argument('--openings', action='store_true', help='Use opening book')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Route to command handler
    commands = {
        'list': cmd_list_engines,
        'discover': cmd_discover,
        'validate': cmd_validate,
        'match': cmd_match,
        'tournament': cmd_tournament,
        'info': cmd_info
    }

    handler = commands.get(args.command)
    if handler:
        try:
            handler(args)
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
        except Exception as e:
            logger.error(f"Error: {e}", exc_info=True)
            print(f"\nError: {e}")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
