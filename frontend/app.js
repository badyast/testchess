// Chess Engine Testing Framework - Frontend JavaScript

let board = null;
let game = new Chess();
let ws = null;
let engines = [];
let selectedEngines = [];

// Initialize
$(document).ready(function() {
    initChessboard();
    connectWebSocket();
    loadEngines();
    addLog('System gestartet', 'info');
});

// Initialize chessboard
function initChessboard() {
    const config = {
        draggable: false,
        position: 'start',
        pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png'
    };
    board = Chessboard('myBoard', config);
}

// WebSocket connection
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    ws = new WebSocket(wsUrl);

    ws.onopen = function() {
        addLog('WebSocket verbunden', 'info');
    };

    ws.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
    };

    ws.onclose = function() {
        addLog('WebSocket getrennt', 'warning');
        // Reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
    };

    ws.onerror = function(error) {
        addLog('WebSocket Fehler: ' + error, 'error');
    };
}

// Handle WebSocket messages
function handleWebSocketMessage(data) {
    switch(data.type) {
        case 'move':
            game.load(data.fen);
            board.position(data.fen);
            updateMoveCount();
            addLog(`Zug: ${data.move}`, 'info');
            break;

        case 'match_start':
            addLog(`Match gestartet: ${data.white} vs ${data.black}`, 'info');
            updateStatus(`Match läuft: ${data.white} vs ${data.black}`);
            $('#white-engine-name').text(data.white);
            $('#black-engine-name').text(data.black);
            game.reset();
            board.start();
            break;

        case 'match_end':
            addLog(`Match beendet! Gewinner: ${data.winner} (${data.reason})`, 'info');
            updateStatus(`Match beendet: ${data.winner} gewinnt`);
            break;

        case 'tournament_start':
            addLog(`Turnier gestartet: ${data.name}`, 'info');
            updateStatus(`Turnier läuft: ${data.name}`);
            $('#standings-container').removeClass('hidden');
            break;

        case 'tournament_progress':
            updateStandings(data.standings);
            addLog(`Spiel ${data.game.game_number}: ${data.game.result}`, 'info');
            break;

        case 'tournament_end':
            addLog('Turnier beendet!', 'info');
            updateStatus('Turnier abgeschlossen');
            updateStandings(data.results.standings);
            break;

        case 'pong':
            // Heartbeat response
            break;

        default:
            console.log('Unknown message type:', data.type);
    }
}

// Load engines from API
function loadEngines() {
    $.get('/api/engines', function(data) {
        engines = data.engines;
        renderEnginesList();
        addLog(`${engines.length} Engines geladen`, 'info');
    }).fail(function() {
        addLog('Fehler beim Laden der Engines', 'error');
    });
}

// Render engines list
function renderEnginesList() {
    const container = $('#engines-list');
    container.empty();

    engines.forEach(engine => {
        const item = $('<div>')
            .addClass('engine-item')
            .text(engine.name)
            .attr('data-engine', engine.name)
            .click(function() {
                toggleEngineSelection(engine.name);
            });

        if (selectedEngines.includes(engine.name)) {
            item.addClass('selected');
        }

        container.append(item);
    });
}

// Toggle engine selection
function toggleEngineSelection(engineName) {
    const index = selectedEngines.indexOf(engineName);

    if (index > -1) {
        // Deselect
        selectedEngines.splice(index, 1);
    } else {
        // Select (max 2 for match)
        if (selectedEngines.length >= 2) {
            selectedEngines.shift(); // Remove first
        }
        selectedEngines.push(engineName);
    }

    renderEnginesList();
    addLog(`Engine ausgewählt: ${engineName}`, 'info');
}

// Discover engines
function discoverEngines() {
    addLog('Suche nach Engines...', 'info');

    $.post('/api/engines/discover', function(data) {
        addLog(data.message, 'info');
        loadEngines();
    }).fail(function() {
        addLog('Fehler beim Suchen der Engines', 'error');
    });
}

// Validate all engines
function validateAllEngines() {
    if (engines.length === 0) {
        addLog('Keine Engines zum Validieren', 'warning');
        return;
    }

    addLog('Validiere alle Engines...', 'info');

    engines.forEach(engine => {
        $.post(`/api/engines/${engine.name}/validate`, function(data) {
            const status = data.compatible ? '✓' : '✗';
            const score = data.score.toFixed(1);
            addLog(`${status} ${engine.name}: ${score}% (${data.passed}/${data.total})`,
                   data.compatible ? 'info' : 'warning');

            if (data.issues.length > 0) {
                data.issues.forEach(issue => {
                    addLog(`  - ${issue}`, 'warning');
                });
            }
        }).fail(function() {
            addLog(`Fehler beim Validieren von ${engine.name}`, 'error');
        });
    });
}

// Start match
function startMatch() {
    if (selectedEngines.length !== 2) {
        alert('Bitte wählen Sie genau 2 Engines aus!');
        return;
    }

    const timeControl = parseInt($('#match-time').val());
    const increment = parseInt($('#match-increment').val());

    const request = {
        white_engine: selectedEngines[0],
        black_engine: selectedEngines[1],
        time_control: timeControl,
        increment: increment
    };

    $.ajax({
        url: '/api/match',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(request),
        success: function(data) {
            addLog(data.message, 'info');
        },
        error: function() {
            addLog('Fehler beim Starten des Matches', 'error');
        }
    });
}

// Start tournament
function startTournament() {
    if (selectedEngines.length < 2) {
        alert('Bitte wählen Sie mindestens 2 Engines aus!');
        return;
    }

    const request = {
        name: $('#tournament-name').val(),
        tournament_type: $('#tournament-type').val(),
        engines: selectedEngines,
        rounds: parseInt($('#tournament-rounds').val()),
        time_control: parseInt($('#tournament-time').val()),
        increment: 0,
        use_openings: $('#use-openings').is(':checked')
    };

    $.ajax({
        url: '/api/tournament',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(request),
        success: function(data) {
            addLog(data.message, 'info');
        },
        error: function() {
            addLog('Fehler beim Starten des Turniers', 'error');
        }
    });
}

// Update standings table
function updateStandings(standings) {
    const tbody = $('#standings-body');
    tbody.empty();

    standings.forEach((stats, index) => {
        const row = $('<tr>')
            .append($('<td>').text(index + 1))
            .append($('<td>').text(stats.engine))
            .append($('<td>').text(stats.points.toFixed(1)));

        tbody.append(row);
    });
}

// Update status text
function updateStatus(text) {
    $('#status-text').text(text);
}

// Update move count
function updateMoveCount() {
    const history = game.history();
    $('#move-count').text(Math.floor(history.length / 2) + 1);
}

// Add log entry
function addLog(message, type = 'info') {
    const logPanel = $('#log-panel');
    const timestamp = new Date().toLocaleTimeString();
    const entry = $('<div>')
        .addClass('log-entry')
        .addClass(`log-${type}`)
        .text(`[${timestamp}] ${message}`);

    logPanel.append(entry);

    // Auto-scroll to bottom
    logPanel.scrollTop(logPanel[0].scrollHeight);

    // Keep max 100 entries
    const entries = logPanel.children();
    if (entries.length > 100) {
        entries.first().remove();
    }
}

// Ping WebSocket to keep alive
setInterval(function() {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
    }
}, 30000);
