var updater = {
    socket: null,
    playerNumber: null,
    reconnectAttempts: 0,
    maxReconnectAttempts: 10,
    reconnectDelay: 3000,

    start: function() {
        this.playerNumber = typeof playerNumber !== 'undefined' ? playerNumber : 0;
        var url = "ws://" + location.host + "/lecternsocket?player=" + this.playerNumber;
        updater.socket = new WebSocket(url);
        
        updater.socket.onopen = function(event) {
            console.log("Lectern WebSocket connected for player " + updater.playerNumber);
            updater.reconnectAttempts = 0;
        };
        
        updater.socket.onmessage = function(event) {
            var jsondata = JSON.parse(event.data);
            updater.handleMessage(jsondata);
        };
        
        updater.socket.onerror = function(error) {
            console.error("WebSocket error:", error);
        };
        
        updater.socket.onclose = function(event) {
            console.log("WebSocket closed");
            updater.handleReconnect();
        };
    },

    handleMessage: function(jsondata) {
        switch (jsondata.message) {
            case "PLAYER_STATE":
                updater.updatePlayerState(JSON.parse(jsondata.text));
                break;
            case "NO_PLAYER":
                updater.showNoPlayer();
                break;
            default:
                console.log("Unknown message:", jsondata.message);
        }
    },

    updatePlayerState: function(state) {
        // Update player name
        var nameElement = document.getElementById("player-name");
        if (state.name) {
            if (state.name.substring(0, 21) === "data:image/png;base64") {
                // It's a signature image
                nameElement.innerHTML = '<img src="' + state.name + '" alt="Player Signature">';
            } else {
                nameElement.textContent = state.name;
            }
        }

        // Update score
        var scoreElement = document.getElementById("player-score");
        var score = state.score || 0;
        scoreElement.textContent = "$" + score.toLocaleString();
        
        // Update score color based on positive/negative
        if (score < 0) {
            scoreElement.classList.add("negative");
        } else {
            scoreElement.classList.remove("negative");
        }

        // Update status indicator
        var statusElement = document.getElementById("status-indicator");
        statusElement.classList.remove("active", "buzzed");
        
        if (state.buzzed) {
            statusElement.classList.add("buzzed");
        } else if (state.active) {
            statusElement.classList.add("active");
        }
    },

    showNoPlayer: function() {
        document.getElementById("player-name").textContent = "No player assigned";
        document.getElementById("player-score").textContent = "$0";
        var statusElement = document.getElementById("status-indicator");
        statusElement.classList.remove("active", "buzzed");
    },

    handleReconnect: function() {
        if (updater.reconnectAttempts < updater.maxReconnectAttempts) {
            updater.reconnectAttempts++;
            console.log("Attempting to reconnect (" + updater.reconnectAttempts + "/" + updater.maxReconnectAttempts + ")...");
            setTimeout(function() {
                updater.start();
            }, updater.reconnectDelay);
        } else {
            console.error("Max reconnection attempts reached");
            document.getElementById("player-name").textContent = "Connection lost";
        }
    }
};

$(document).ready(function() {
    updater.start();
    
    // Handle page visibility changes to reconnect if needed
    document.addEventListener("visibilitychange", function() {
        if (!document.hidden && (!updater.socket || updater.socket.readyState !== WebSocket.OPEN)) {
            console.log("Page visible, checking connection...");
            updater.start();
        }
    });
});

