import { OtherPlayer } from './otherPlayer.js';
import { v4 as uuidv4 } from 'uuid';

/**
 * Class to manage multiplayer connections and player synchronization
 */
export class MultiplayerManager {
  constructor(scene, localPlayer) {
    this.scene = scene;
    this.localPlayer = localPlayer;
    this.otherPlayers = new Map(); // Map of player IDs to OtherPlayer instances
    this.socket = null;
    this.playerId = uuidv4(); // Generate unique ID for this player
    this.playerName = localStorage.getItem('playerName') || 'Player'; // Get player name from localStorage
    this.connected = false;
    this.lastPositionUpdate = 0;
    this.lastRotationUpdate = 0;
    
    // Position and rotation update throttling (in milliseconds)
    this.positionUpdateInterval = 100; // Send position updates every 100ms
    this.rotationUpdateInterval = 100; // Send rotation updates every 100ms
    
    // Store last sent position and rotation to avoid sending duplicates
    this.lastSentPosition = { x: 0, y: 0, z: 0 };
    this.lastSentRotation = { x: 0, y: 0, z: 0 };
    
    // SuperSaiyan mode state
    this.isSuperSaiyanMode = false;
  }
  
  /**
   * Initialize the WebSocket connection
   */
  connect() {
    // Clean up existing connection first
    this.disconnect();
    
    // Get the BACKEND_URL from environment
    const backendUrl = process.env.REACT_APP_BACKEND_URL || '';
    
    // Create WebSocket URL by replacing http/https with ws/wss
    let wsBaseUrl = '';
    if (backendUrl) {
      // Replace http with ws, keeping the rest of the URL the same
      wsBaseUrl = backendUrl.replace(/^http/, 'ws');
    } else {
      // Fallback to direct connection to current host
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      wsBaseUrl = `${protocol}//${window.location.host}`;
    }
    
    // Use /api/ws consistently for all environments
    const wsUrl = `${wsBaseUrl}/api/ws/${this.playerId}`;
    
    console.log(`Connecting to WebSocket server at ${wsUrl}`);
    console.log(`Player ID: ${this.playerId}, Name: ${this.playerName}`);
    
    this.socket = new WebSocket(wsUrl);
    
    this.socket.onopen = () => {
      console.log('WebSocket connection established');
      this.connected = true;
      
      // Send initial player information
      this.socket.send(JSON.stringify({
        type: 'connect',
        name: this.playerName
      }));
    };
    
    this.socket.onmessage = (event) => {
      this.handleMessage(JSON.parse(event.data));
    };
    
    // Make the multiplayer instance globally accessible for chat
    window.multiplayer = this;
    
    this.socket.onclose = (event) => {
      console.log('WebSocket connection closed', event.code, event.reason);
      this.connected = false;
      
      // Only attempt to reconnect if it wasn't a manual close
      if (event.code !== 1000 && event.code !== 1001) {
        // Attempt to reconnect after 5 seconds
        console.log('Attempting to reconnect in 5 seconds...');
        setTimeout(() => {
          if (!this.connected) {
            this.connect();
          }
        }, 5000);
      }
    };
    
    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }
  
  /**
   * Handle incoming WebSocket messages
   * @param {Object} message - The parsed message from the server
   */
  handleMessage(message) {
    // Log all incoming messages for debugging
    console.log('Received WebSocket message:', message);
    
    // Ignore messages about our own player
    if ((message.type === 'player_state_update' && message.player_id === this.playerId) ||
        (message.type === 'player_joined' && message.player && message.player.id === this.playerId)) {
      console.log('Ignoring message about own player');
      return;
    }
    
    switch (message.type) {
      case 'player_joined':
        console.log('Player joined event received:', message.player);
        if (message.player && message.player.id !== this.playerId) {
          this.handlePlayerJoined(message.player);
        }
        break;
        
      case 'player_left':
        console.log('Player left event received:', message.player_id);
        if (message.player_id !== this.playerId) {
          this.handlePlayerLeft(message.player_id);
        }
        break;
        
      case 'player_state_update':
        console.log('Player state update:', message.player_id, message.state);
        if (message.player_id !== this.playerId) {
          this.handlePlayerStateUpdate(message.player_id, message.state);
        }
        break;
        
      case 'existing_players':
        console.log('Existing players:', message.players);
        // Filter out our own player from the list if present
        const filteredPlayers = message.players.filter(p => p.id !== this.playerId);
        this.handleExistingPlayers(filteredPlayers);
        break;
        
      case 'block_update':
        console.log('Block update:', message.data);
        this.handleBlockUpdate(message.data);
        break;
        
      case 'chat_message':
        console.log('Chat message received:', message);
        this.handleChatMessage(message.player_id, message.text);
        break;
        
      case 'supersaiyan_toggle':
        console.log('SuperSaiyan toggle received:', message.player_id, message.active);
        if (message.player_id !== this.playerId) {
          this.handleSuperSaiyanToggle(message.player_id, message.active);
        }
        break;
        
      default:
        console.warn('Unknown message type:', message.type);
    }
  }
  
  /**
   * Handle chat message from another player
   * @param {String} playerId - ID of the player who sent the message
   * @param {String} text - The chat message text
   */
  handleChatMessage(playerId, text) {
    console.log(`Chat from ${playerId}: ${text}`);
    
    // Find the other player instance
    const player = this.otherPlayers.get(playerId);
    if (player) {
      // Display chat bubble above the player
      player.showChatBubble(text);
      
      // Also display the message in the console
      console.log(`${player.playerName}: ${text}`);
      
      // Show a status message briefly
      document.getElementById('status').textContent = `${player.playerName}: ${text}`;
      setTimeout(() => {
        document.getElementById('status').textContent = '';
      }, 5000);
    }
  }
  
  /**
   * Send a chat message to all players
   * @param {String} text - The chat message text
   */
  sendChatMessage(text) {
    if (!this.connected) return;
    
    this.socket.send(JSON.stringify({
      type: 'chat_message',
      text: text
    }));
    
    // Show our own chat bubble above our player
    // This is a bit of a hack since we don't have a model for our own player
    document.getElementById('status').textContent = `You: ${text}`;
    setTimeout(() => {
      document.getElementById('status').textContent = '';
    }, 5000);
  }
  
  /**
   * Handle a new player joining
   * @param {Object} playerData - Data for the new player
   */
  handlePlayerJoined(playerData) {
    console.log('Player joined:', playerData);
    
    // Create a new OtherPlayer instance
    const otherPlayer = new OtherPlayer(
      playerData.id,
      playerData.name,
      playerData.position,
      playerData.rotation
    );
    
    // Add it to the scene and our map
    this.scene.add(otherPlayer);
    this.otherPlayers.set(playerData.id, otherPlayer);
    
    // Log the active other players
    console.log(`Active players: ${this.otherPlayers.size}`, 
                Array.from(this.otherPlayers.keys()));
    
    // Display a status message
    document.getElementById('status').textContent = `${playerData.name} joined`;
    setTimeout(() => {
      document.getElementById('status').textContent = '';
    }, 3000);
  }
  
  /**
   * Handle a player leaving
   * @param {String} playerId - ID of the player who left
   */
  handlePlayerLeft(playerId) {
    const player = this.otherPlayers.get(playerId);
    
    if (player) {
      console.log('Player left:', player.name);
      
      // Display a status message
      document.getElementById('status').textContent = `${player.name} left`;
      setTimeout(() => {
        document.getElementById('status').textContent = '';
      }, 3000);
      
      // Remove the player from the scene and our map
      this.scene.remove(player);
      this.otherPlayers.delete(playerId);
    }
  }
  
  /**
   * Handle state updates for other players
   * @param {String} playerId - ID of the player whose state changed
   * @param {Object} stateData - New state data
   */
  handlePlayerStateUpdate(playerId, stateData) {
    // Debug logging
    console.log(`Updating player ${playerId} state:`, stateData);
    console.log('Current other players:', Array.from(this.otherPlayers.keys()));
    
    const player = this.otherPlayers.get(playerId);
    
    if (player) {
      console.log(`Found player ${playerId} - ${player.name}`);
      
      // Update position and rotation if they're included in the state update
      if (stateData.position) {
        console.log(`Updating position for ${player.name}:`, stateData.position);
        player.updatePosition(stateData.position);
      }
      
      if (stateData.rotation) {
        console.log(`Updating rotation for ${player.name}:`, stateData.rotation);
        player.updateRotation(stateData.rotation);
      }
    } else {
      console.warn(`Player ${playerId} not found in otherPlayers map`);
    }
  }
  
  /**
   * Handle receiving existing players when joining a game
   * @param {Array} players - Array of player data objects
   */
  handleExistingPlayers(players) {
    console.log('Existing players:', players);
    
    players.forEach(playerData => {
      // Create a new OtherPlayer instance for each existing player
      const otherPlayer = new OtherPlayer(
        playerData.id,
        playerData.name,
        playerData.position,
        playerData.rotation
      );
      
      // Add it to the scene and our map
      this.scene.add(otherPlayer);
      this.otherPlayers.set(playerData.id, otherPlayer);
    });
    
    // Display a status message
    if (players.length > 0) {
      document.getElementById('status').textContent = `${players.length} other player(s) in the world`;
      setTimeout(() => {
        document.getElementById('status').textContent = '';
      }, 3000);
    }
  }
  
  /**
   * Handle block updates from other players
   * @param {Object} blockData - Data about the block update
   */
  handleBlockUpdate(blockData) {
    // Update the world with the block change
    if (blockData.action === 'add') {
      this.localPlayer.world.addBlock(
        blockData.x,
        blockData.y,
        blockData.z,
        blockData.blockId
      );
    } else if (blockData.action === 'remove') {
      this.localPlayer.world.removeBlock(
        blockData.x,
        blockData.y,
        blockData.z
      );
    }
  }
  
  /**
   * Send the player's current position to the server
   */
  sendPositionUpdate() {
    if (!this.connected) return;
    
    const now = Date.now();
    const position = this.localPlayer.position;
    
    // Check if enough time has passed since last update and position has changed
    if (now - this.lastPositionUpdate > this.positionUpdateInterval &&
        (this.lastSentPosition.x !== position.x ||
         this.lastSentPosition.y !== position.y ||
         this.lastSentPosition.z !== position.z)) {
      
      this.socket.send(JSON.stringify({
        type: 'position_update',
        position: {
          x: position.x,
          y: position.y,
          z: position.z
        }
      }));
      
      // Store position and timestamp
      this.lastSentPosition = { x: position.x, y: position.y, z: position.z };
      this.lastPositionUpdate = now;
    }
  }
  
  /**
   * Send the player's current rotation to the server
   */
  sendRotationUpdate() {
    if (!this.connected) return;
    
    const now = Date.now();
    const rotation = this.localPlayer.camera.rotation;
    
    // Check if enough time has passed since last update and rotation has changed
    if (now - this.lastRotationUpdate > this.rotationUpdateInterval &&
        (this.lastSentRotation.x !== rotation.x ||
         this.lastSentRotation.y !== rotation.y ||
         this.lastSentRotation.z !== rotation.z)) {
      
      this.socket.send(JSON.stringify({
        type: 'rotation_update',
        rotation: {
          x: rotation.x,
          y: rotation.y,
          z: rotation.z
        }
      }));
      
      // Store rotation and timestamp
      this.lastSentRotation = { x: rotation.x, y: rotation.y, z: rotation.z };
      this.lastRotationUpdate = now;
    }
  }
  
  /**
   * Send block update to the server when a player adds or removes a block
   * @param {String} action - 'add' or 'remove'
   * @param {Number} x - X coordinate
   * @param {Number} y - Y coordinate
   * @param {Number} z - Z coordinate
   * @param {Number} blockId - ID of the block (for 'add' actions)
   */
  sendBlockUpdate(action, x, y, z, blockId = null) {
    if (!this.connected) return;
    
    const blockData = {
      action,
      x,
      y,
      z
    };
    
    if (action === 'add' && blockId !== null) {
      blockData.blockId = blockId;
    }
    
    this.socket.send(JSON.stringify({
      type: 'block_update',
      data: blockData
    }));
  }
  
  /**
   * Toggle SuperSaiyan mode for the local player
   */
  toggleSuperSaiyanMode() {
    if (!this.connected) return;
    
    // Toggle the state
    this.isSuperSaiyanMode = !this.isSuperSaiyanMode;
    console.log(`SuperSaiyan mode ${this.isSuperSaiyanMode ? 'activated' : 'deactivated'} for local player`);
    
    // Play appropriate sound effect
    if (window.audioManager) {
      window.audioManager.playSuperSaiyanSound(this.isSuperSaiyanMode);
    }
    
    // Apply visual effect to local player (handled in the Player class)
    if (this.localPlayer && typeof this.localPlayer.setSuperSaiyanMode === 'function') {
      this.localPlayer.setSuperSaiyanMode(this.isSuperSaiyanMode);
    }
    
    // Send message to server to broadcast to other players
    this.socket.send(JSON.stringify({
      type: 'supersaiyan_toggle',
      active: this.isSuperSaiyanMode
    }));
    
    // Display a status message
    document.getElementById('status').textContent = `SuperSaiyan mode ${this.isSuperSaiyanMode ? 'activated' : 'deactivated'}!`;
    setTimeout(() => {
      document.getElementById('status').textContent = '';
    }, 3000);
  }
  
  /**
   * Handle supersaiyan toggle message from another player
   * @param {String} playerId - ID of the player who toggled SuperSaiyan mode
   * @param {Boolean} active - Whether SuperSaiyan mode is active or not
   */
  handleSuperSaiyanToggle(playerId, active) {
    console.log(`SuperSaiyan toggle for player ${playerId}: ${active}`);
    
    // Find the other player instance
    const player = this.otherPlayers.get(playerId);
    if (player) {
      // Apply visual effect to the player model
      if (typeof player.setSuperSaiyanMode === 'function') {
        player.setSuperSaiyanMode(active);
      }
      
      // Play sound effect for other player's transformation
      if (window.audioManager) {
        window.audioManager.playSuperSaiyanSound(active);
      }
      
      // Display a status message
      document.getElementById('status').textContent = `${player.playerName} ${active ? 'activated' : 'deactivated'} SuperSaiyan mode!`;
      setTimeout(() => {
        document.getElementById('status').textContent = '';
      }, 3000);
    }
  }

  /**
   * Update method to be called every frame
   * @param {Number} deltaTime - Time since last frame
   */
  update(deltaTime) {
    // Only send updates if connected
    if (this.connected) {
      // Update position and rotation on the server
      this.sendPositionUpdate();
      this.sendRotationUpdate();
    }
    
    // Log other players count occasionally (every 5 seconds)
    const now = Date.now();
    if (!this._lastDebugLog || now - this._lastDebugLog > 5000) {
      console.log(`Active other players: ${this.otherPlayers.size}`);
      if (this.otherPlayers.size > 0) {
        console.log('Other players:', Array.from(this.otherPlayers.entries()).map(([id, player]) => {
          return {
            id: id,
            name: player.playerName || player.name || 'Unknown',
            position: {
              x: player.position.x.toFixed(2),
              y: player.position.y.toFixed(2),
              z: player.position.z.toFixed(2)
            }
          };
        }));
      }
      this._lastDebugLog = now;
    }
    
    // Animate other players
    this.otherPlayers.forEach(player => {
      // Make sure the player model is visible
      player.visible = true;
      player.body.visible = true;
      player.head.visible = true;
      
      // Calculate if player is moving by comparing last known positions
      const isMoving = player.lastPosition && 
                       (player.lastPosition.x !== player.position.x ||
                        player.lastPosition.y !== player.position.y ||
                        player.lastPosition.z !== player.position.z);
                        
      // Animate based on movement state
      player.animate(deltaTime, isMoving);
      
      // Store current position for next frame's comparison
      player.lastPosition = { 
        x: player.position.x, 
        y: player.position.y, 
        z: player.position.z 
      };
    });
  }

  /**
   * Disconnect from the WebSocket server
   */
  disconnect() {
    try {
      if (this.socket && this.socket.readyState !== WebSocket.CLOSED) {
        this.socket.close();
      }
      this.connected = false;
      this.socket = null;
    } catch (error) {
      console.error('Error during disconnect:', error);
    }
  }
}