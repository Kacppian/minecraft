import * as THREE from 'three';
import Stats from 'three/examples/jsm/libs/stats.module.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { World } from './world';
import { Player } from './player';
import { Physics } from './physics';
import { setupUI } from './ui';
import { ModelLoader } from './modelLoader';
import { MultiplayerManager } from './multiplayerManager';
import audioManager from './audioManager';

// UI Setup
const stats = new Stats();
document.body.appendChild(stats.dom);

// Renderer setup
const renderer = new THREE.WebGLRenderer();
renderer.setPixelRatio(window.devicePixelRatio);
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setClearColor(0x80a0e0);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.appendChild(renderer.domElement);

// Scene setup
const scene = new THREE.Scene();
scene.fog = new THREE.Fog(0x80a0e0, 50, 75);

const world = new World();
world.generate();
scene.add(world);

const player = new Player(scene, world);
const physics = new Physics(scene);

// Initialize multiplayer manager
const multiplayer = new MultiplayerManager(scene, player);
// Make multiplayer manager and audio manager available globally for the overlay screen
window.multiplayer = multiplayer;
window.audioManager = audioManager;

// Connect to WebSocket server and start audio when the game starts
document.addEventListener('keydown', function setupGame() {
  // Only set up once
  document.removeEventListener('keydown', setupGame);
  
  // Connect to the WebSocket server
  multiplayer.connect();
  
  // Show connection message
  document.getElementById('status').textContent = 'Connecting to server...';
  setTimeout(() => {
    document.getElementById('status').textContent = '';
  }, 3000);
  
  // Start background music (disabled by default)
  // try {
  //   audioManager.playMusic();
  //   console.log('Background music started');
  // } catch (e) {
  //   console.error('Failed to start background music:', e);
  // }
  
  // Add keyboard shortcuts for audio control
  document.addEventListener('keydown', (e) => {
    // M key to toggle music
    if (e.key === 'm') {
      audioManager.toggleMusic();
      document.getElementById('status').textContent = 
        `Music ${audioManager.isMusicPlaying ? 'On' : 'Off'}`;
      setTimeout(() => {
        document.getElementById('status').textContent = '';
      }, 1500);
    }
    
    // N key to toggle all sound (mute)
    if (e.key === 'n') {
      const isMuted = audioManager.toggleMute();
      document.getElementById('status').textContent = 
        `Sound ${isMuted ? 'Muted' : 'Unmuted'}`;
      setTimeout(() => {
        document.getElementById('status').textContent = '';
      }, 1500);
    }
  });
}, { once: true });

// Camera setup
const orbitCamera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
orbitCamera.position.set(24, 24, 24);
orbitCamera.layers.enable(1);

const controls = new OrbitControls(orbitCamera, renderer.domElement);
controls.update();

const modelLoader = new ModelLoader((models) => {
  player.setTool(models.pickaxe);
})

let sun;
function setupLights() {
  sun = new THREE.DirectionalLight();
  sun.intensity = 1.5;
  sun.position.set(50, 50, 50);
  sun.castShadow = true;

  // Set the size of the sun's shadow box
  sun.shadow.camera.left = -40;
  sun.shadow.camera.right = 40;
  sun.shadow.camera.top = 40;
  sun.shadow.camera.bottom = -40;
  sun.shadow.camera.near = 0.1;
  sun.shadow.camera.far = 200;
  sun.shadow.bias = -0.0001;
  sun.shadow.mapSize = new THREE.Vector2(2048, 2048);
  scene.add(sun);
  scene.add(sun.target);

  const ambient = new THREE.AmbientLight();
  ambient.intensity = 0.2;
  scene.add(ambient);
}

// Render loop
let previousTime = performance.now();
function animate() {
  requestAnimationFrame(animate);

  const currentTime = performance.now();
  const dt = (currentTime - previousTime) / 1000;

  // Always update multiplayer to render other players even when not locked
  multiplayer.update(dt);
  
  // Only update physics when player controls are locked
  if (player.controls.isLocked) {
    physics.update(dt, player, world);
    player.update(world);
    world.update(player);

    // Position the sun relative to the player. Need to adjust both the
    // position and target of the sun to keep the same sun angle
    sun.position.copy(player.camera.position);
    sun.position.sub(new THREE.Vector3(-50, -50, -50));
    sun.target.position.copy(player.camera.position);

    // Update positon of the orbit camera to track player 
    orbitCamera.position.copy(player.position).add(new THREE.Vector3(16, 16, 16));
    controls.target.copy(player.position);
    
    // Display debug info - show number of other players
    const infoElement = document.getElementById('info-player-position');
    if (infoElement) {
      const otherPlayersCount = multiplayer.otherPlayers.size;
      const posInfo = `X: ${player.position.x.toFixed(2)}, Y: ${player.position.y.toFixed(2)}, Z: ${player.position.z.toFixed(2)}`;
      infoElement.innerHTML = `${posInfo}<br>Other players: ${otherPlayersCount}`;
    }
  }

  renderer.render(scene, player.controls.isLocked ? player.camera : orbitCamera);
  stats.update();

  previousTime = currentTime;
}

window.addEventListener('resize', () => {
  // Resize camera aspect ratio and renderer size to the new window size
  orbitCamera.aspect = window.innerWidth / window.innerHeight;
  orbitCamera.updateProjectionMatrix();
  player.camera.aspect = window.innerWidth / window.innerHeight;
  player.camera.updateProjectionMatrix();

  renderer.setSize(window.innerWidth, window.innerHeight);
});

setupUI(world, player, physics, scene);
setupLights();
animate();

// Add cleanup on page unload
window.addEventListener('beforeunload', () => {
  if (window.multiplayer) {
    window.multiplayer.disconnect();
  }
});

// Add cleanup on visibility change (when user switches tabs)
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'hidden' && window.multiplayer) {
    // Don't disconnect on tab switch, just note it
    console.log('Tab became hidden');
  }
});

console.log('Game initialized');