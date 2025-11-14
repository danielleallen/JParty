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
        // Update player name or final answer
        var nameElement = document.getElementById("player-name");
        var nameBox = document.getElementById("name-box");
        var logoElement = document.getElementById("logo");
        
        // Check if we should show final answer (takes priority over name)
        if (state.finalanswer !== undefined && state.finalanswer !== null && state.finalanswer !== "") {
            nameBox.classList.remove("no-player");
            logoElement.style.display = "none";
            nameElement.style.display = "block";
            nameElement.textContent = state.finalanswer;
        } else if (state.name) {
            nameBox.classList.remove("no-player");
            logoElement.style.display = "none";
            nameElement.style.display = "block";
            if (state.name.substring(0, 21) === "data:image/png;base64") {
                // It's a signature image
                nameElement.innerHTML = '<img src="' + state.name + '" alt="Player Signature">';
            } else {
                nameElement.textContent = state.name;
            }
        } else {
            nameBox.classList.add("no-player");
            nameElement.textContent = "";
            nameElement.style.display = "none";
            logoElement.style.display = "block";
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
        
        // Apply extra-condensed font if score has 6 digits
        var absScore = Math.abs(score);
        var digitCount = absScore.toString().length;
        if (digitCount >= 6) {
            scoreElement.classList.add("condensed");
        } else {
            scoreElement.classList.remove("condensed");
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
            [1, 2, 3, 4, 5, 6, 7, 8, 9], // Stage 5: all 9
            [2, 3, 4, 5, 6, 7, 8], // Stage 4: center 7
            [3, 4, 5, 6, 7], // Stage 3: center 5
            [4, 5, 6],     // Stage 2: center 3
            [5],           // Stage 1: center light
            [],            // Stage 0: no lights
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
        var logoElement = document.getElementById("logo");
        nameBox.classList.add("no-player");
        nameElement.textContent = "";
        nameElement.style.display = "none";
        logoElement.style.display = "block";
        var scoreElement = document.getElementById("player-score");
        scoreElement.textContent = "$0";
        scoreElement.classList.remove("condensed");
        scoreElement.classList.remove("negative");
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

function positionAnsweringBox() {
    var lightsContainer = document.getElementById('lights-container');
    var scoreBox = document.getElementById('score-box');
    var answeringBox = document.getElementById('answering-box');
    var nameBox = document.getElementById('name-box');
    
    if (!lightsContainer || !scoreBox || !answeringBox || !nameBox) {
        return;
    }
    
    // Target position: 13.5/28.1 of screen height (this is where the border should be)
    var targetBorderPosition = (13.5 / 28.1) * window.innerHeight;
    
    // Get actual heights after layout
    var lightsHeight = lightsContainer.offsetHeight;
    var scoreHeight = scoreBox.offsetHeight;
    
    // Calculate answering box height so that lights + score + answering = target position
    var answeringBoxHeight = targetBorderPosition - lightsHeight - scoreHeight;
    
    // Ensure minimum height
    if (answeringBoxHeight > 50) {
        answeringBox.style.height = answeringBoxHeight + 'px';
    } else {
        answeringBox.style.height = '50px';
    }
    
    // Verify the border is at the right position (for debugging)
    var actualBorderPosition = lightsHeight + scoreHeight + answeringBox.offsetHeight;
    console.log('Target border position: ' + targetBorderPosition + 'px, Actual: ' + actualBorderPosition + 'px');
}

$(document).ready(function() {
    updater.start();
    
    // Position answering box initially and on resize
    setTimeout(function() {
        positionAnsweringBox();
    }, 100);
    
    window.addEventListener('resize', function() {
        setTimeout(positionAnsweringBox, 50);
    });
    
    // Handle page visibility changes to reconnect if needed
    document.addEventListener("visibilitychange", function() {
        if (!document.hidden && (!updater.socket || updater.socket.readyState !== WebSocket.OPEN)) {
            console.log("Page visible, checking connection...");
            updater.start();
        }
        setTimeout(positionAnsweringBox, 100);
    });
});

