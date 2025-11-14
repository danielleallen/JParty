var updater = {
    socket: null,
    playerNumber: null,
    reconnectAttempts: 0,
    maxReconnectAttempts: 10,
    reconnectDelay: 3000,
    lightsInterval: null,
    lightsRunning: false,
    currentLightStage: 0,

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
        var nameBox = document.getElementById("name-box");
        if (state.name) {
            nameBox.classList.remove("no-player");
            if (state.name.substring(0, 21) === "data:image/png;base64") {
                // It's a signature image
                nameElement.innerHTML = '<img src="' + state.name + '" alt="Player Signature">';
            } else {
                nameElement.textContent = state.name;
            }
        } else {
            nameBox.classList.add("no-player");
            nameElement.textContent = "";
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

        // Update answering box
        var answeringBox = document.getElementById("answering-box");
        if (state.active) {
            answeringBox.classList.add("active");
        } else {
            answeringBox.classList.remove("active");
        }

        // Update lights animation
        if (state.buzzed && !this.lightsRunning) {
            this.runLights();
        } else if (!state.buzzed && this.lightsRunning) {
            this.stopLights();
        }
    },

    runLights: function() {
        if (this.lightsRunning) {
            return;
        }
        this.lightsRunning = true;
        this.currentLightStage = 0;
        var self = this;
        
        // Clear all lights first
        var lights = document.querySelectorAll('.light');
        lights.forEach(function(light) {
            light.classList.remove('active');
        });

        // Light pattern: center (5), then center 3 (4-6), then center 5 (3-7), then center 7 (2-8), then all 9
        var lightPatterns = [
            [5],           // Stage 1: center light
            [4, 5, 6],     // Stage 2: center 3
            [3, 4, 5, 6, 7], // Stage 3: center 5
            [2, 3, 4, 5, 6, 7, 8], // Stage 4: center 7
            [1, 2, 3, 4, 5, 6, 7, 8, 9] // Stage 5: all 9
        ];

        // Start animation sequence
        this.lightsInterval = setInterval(function() {
            if (self.currentLightStage < lightPatterns.length) {
                // Clear all lights
                lights.forEach(function(light) {
                    light.classList.remove('active');
                });
                
                // Activate lights for current stage
                var currentPattern = lightPatterns[self.currentLightStage];
                currentPattern.forEach(function(lightNum) {
                    var lightToActivate = document.querySelector('.light[data-light="' + lightNum + '"]');
                    if (lightToActivate) {
                        lightToActivate.classList.add('active');
                    }
                });
                
                self.currentLightStage++;
            } else {
                // All lights are on, stop the interval
                clearInterval(self.lightsInterval);
                self.lightsInterval = null;
            }
        }, 1000); // 1 second per stage, matching PlayerWidget timing
    },

    stopLights: function() {
        if (this.lightsInterval) {
            clearInterval(this.lightsInterval);
            this.lightsInterval = null;
        }
        this.lightsRunning = false;
        this.currentLightStage = 0;
        var lights = document.querySelectorAll('.light');
        lights.forEach(function(light) {
            light.classList.remove('active');
        });
    },

    showNoPlayer: function() {
        var nameElement = document.getElementById("player-name");
        var nameBox = document.getElementById("name-box");
        nameBox.classList.add("no-player");
        nameElement.textContent = "";
        document.getElementById("player-score").textContent = "$0";
        document.getElementById("answering-box").classList.remove("active");
        this.stopLights();
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

