/**
 * AudioManager class for handling all game audio
 */
export class AudioManager {
  constructor() {
    this.sounds = {};
    this.music = null;
    this.isMusicPlaying = false;
    this.isMuted = false;
    this.volume = 0.5;
    
    // List of sound URLs
    this.soundUrls = {
      // Background music
      bgMusic: 'https://assets.mixkit.co/music/preview/mixkit-games-worldbeat-466.mp3',
      
      // Game sound effects
      blockPlace: 'https://assets.mixkit.co/sfx/preview/mixkit-arcade-game-jump-coin-216.mp3',
      blockBreak: 'https://assets.mixkit.co/sfx/preview/mixkit-player-jumping-in-a-video-game-2043.mp3',
      playerJump: 'https://assets.mixkit.co/sfx/preview/mixkit-quick-jump-arcade-game-239.mp3',
      playerLand: 'https://assets.mixkit.co/sfx/preview/mixkit-arcade-mechanical-bling-210.mp3',
      
      // SuperSaiyan transformation
      superSaiyan: 'https://assets.mixkit.co/sfx/preview/mixkit-martial-arts-fast-punch-2047.mp3',
      superSaiyanOff: 'https://assets.mixkit.co/sfx/preview/mixkit-martial-arts-punch-2052.mp3'
    };
    
    // Preload sounds
    this.preloadSounds();
  }
  
  /**
   * Preload all game sounds
   */
  preloadSounds() {
    // Create audio context
    try {
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
      console.log('Audio context created successfully');
    } catch (e) {
      console.error('Failed to create audio context:', e);
      return;
    }
    
    // Preload all sound effects
    Object.keys(this.soundUrls).forEach(soundName => {
      if (soundName !== 'bgMusic') { // Skip background music, we'll load it separately
        const audio = new Audio();
        audio.src = this.soundUrls[soundName];
        audio.preload = 'auto';
        this.sounds[soundName] = audio;
        
        // Add event listeners for debugging
        audio.addEventListener('canplaythrough', () => {
          console.log(`Sound "${soundName}" loaded successfully`);
        });
        
        audio.addEventListener('error', (e) => {
          console.error(`Error loading sound "${soundName}":`, e);
        });
      }
    });
    
    // Prepare background music
    this.prepareBackgroundMusic();
  }
  
  /**
   * Set up background music with looping
   */
  prepareBackgroundMusic() {
    this.music = new Audio();
    this.music.src = this.soundUrls.bgMusic;
    this.music.loop = true;
    this.music.volume = this.volume * 0.3; // Background music slightly quieter
    
    // Add event listeners for debugging
    this.music.addEventListener('canplaythrough', () => {
      console.log('Background music loaded successfully');
    });
    
    this.music.addEventListener('error', (e) => {
      console.error('Error loading background music:', e);
    });
  }
  
  /**
   * Play a sound effect
   * @param {String} soundName - Name of the sound to play
   */
  playSound(soundName) {
    if (this.isMuted || !this.sounds[soundName]) return;
    
    try {
      // Clone the audio to allow overlapping sounds
      const sound = this.sounds[soundName].cloneNode();
      sound.volume = this.volume;
      
      // Play the sound
      sound.play().catch(e => {
        console.error(`Error playing sound "${soundName}":`, e);
      });
      
      console.log(`Playing sound: ${soundName}`);
    } catch (e) {
      console.error(`Error playing sound "${soundName}":`, e);
    }
  }
  
  /**
   * Start playing background music
   */
  playMusic() {
    if (this.isMuted || !this.music || this.isMusicPlaying) return;
    
    try {
      this.music.play().then(() => {
        this.isMusicPlaying = true;
        console.log('Background music started');
      }).catch(e => {
        console.error('Error playing background music:', e);
      });
    } catch (e) {
      console.error('Error playing background music:', e);
    }
  }
  
  /**
   * Pause background music
   */
  pauseMusic() {
    if (!this.music || !this.isMusicPlaying) return;
    
    try {
      this.music.pause();
      this.isMusicPlaying = false;
      console.log('Background music paused');
    } catch (e) {
      console.error('Error pausing background music:', e);
    }
  }
  
  /**
   * Toggle music on/off
   */
  toggleMusic() {
    if (this.isMusicPlaying) {
      this.pauseMusic();
    } else {
      this.playMusic();
    }
  }
  
  /**
   * Toggle mute all sounds
   */
  toggleMute() {
    this.isMuted = !this.isMuted;
    
    if (this.isMuted) {
      this.pauseMusic();
    } else if (!this.isMusicPlaying) {
      this.playMusic();
    }
    
    console.log(`Sound ${this.isMuted ? 'muted' : 'unmuted'}`);
    return this.isMuted;
  }
  
  /**
   * Set the volume for all sounds
   * @param {Number} volume - Volume level (0.0 to 1.0)
   */
  setVolume(volume) {
    this.volume = Math.max(0, Math.min(1, volume));
    
    // Update music volume
    if (this.music) {
      this.music.volume = this.volume * 0.3;
    }
    
    console.log(`Volume set to ${this.volume}`);
    return this.volume;
  }
  
  /**
   * Play SuperSaiyan activation sound
   * @param {Boolean} active - Whether SuperSaiyan mode is being activated or deactivated
   */
  playSuperSaiyanSound(active) {
    const soundName = active ? 'superSaiyan' : 'superSaiyanOff';
    this.playSound(soundName);
    
    // If SuperSaiyan is activated, add a voice effect
    if (active && !this.isMuted) {
      // Use the Web Speech API for the voice
      try {
        const utterance = new SpeechSynthesisUtterance('Power up!');
        utterance.rate = 1.0; // Speed of speech
        utterance.pitch = 0.2; // Low pitch for a deep voice
        utterance.volume = this.volume * 1.5; // Louder
        
        // Speak the utterance
        window.speechSynthesis.speak(utterance);
      } catch (e) {
        console.error('Speech synthesis not supported:', e);
      }
    }
  }
}

// Create and export a singleton instance
const audioManager = new AudioManager();
export default audioManager;