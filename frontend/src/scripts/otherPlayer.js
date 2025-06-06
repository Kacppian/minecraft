import * as THREE from 'three';

/**
 * Class representing other players in the multiplayer world
 */
export class OtherPlayer extends THREE.Group {
  constructor(id, name, position, rotation) {
    super();
    this.playerId = id;  // Use playerId instead of id to avoid conflict with THREE.Object3D
    this.playerName = name;  // Also rename name to be consistent
    
    // Create player model
    this.createPlayerModel();
    
    // Create name tag
    this.createNameTag();
    
    // Create chat bubble (initially hidden)
    this.chatBubble = null;
    this.chatTimeout = null;
    
    // SuperSaiyan mode properties
    this.isSuperSaiyanMode = false;
    this.fireParticles = null;
    this.glowEffect = null;
    this.superSaiyanAnimationFrame = null;
    
    // Make player models slightly larger for better visibility
    this.scale.set(1.2, 1.2, 1.2);
    
    // Set initial position and rotation
    this.updatePosition(position);
    this.updateRotation(rotation);
    
    console.log(`Created other player: ${this.playerName} (${this.playerId}) at position:`, position);
  }
  
  /**
   * Creates a simple player model
   */
  createPlayerModel() {
    // Create player body
    const bodyGeometry = new THREE.BoxGeometry(0.6, 1.8, 0.6);
    const bodyMaterial = new THREE.MeshLambertMaterial({ color: 0x3366ff });
    this.body = new THREE.Mesh(bodyGeometry, bodyMaterial);
    this.body.position.y = 0.9; // Center the body vertically
    
    // Create player head
    const headGeometry = new THREE.BoxGeometry(0.8, 0.8, 0.8);
    const headMaterial = new THREE.MeshLambertMaterial({ color: 0xffcc99 });
    this.head = new THREE.Mesh(headGeometry, headMaterial);
    this.head.position.y = 1.8; // Place head on top of body
    
    // Create player arms
    const armGeometry = new THREE.BoxGeometry(0.25, 0.6, 0.25);
    const armMaterial = new THREE.MeshLambertMaterial({ color: 0x3366ff });
    
    // Left arm
    this.leftArm = new THREE.Mesh(armGeometry, armMaterial);
    this.leftArm.position.set(-0.425, 1.2, 0);
    
    // Right arm
    this.rightArm = new THREE.Mesh(armGeometry, armMaterial);
    this.rightArm.position.set(0.425, 1.2, 0);
    
    // Create player legs
    const legGeometry = new THREE.BoxGeometry(0.25, 0.6, 0.25);
    const legMaterial = new THREE.MeshLambertMaterial({ color: 0x333333 });
    
    // Left leg
    this.leftLeg = new THREE.Mesh(legGeometry, legMaterial);
    this.leftLeg.position.set(-0.2, 0.3, 0);
    
    // Right leg
    this.rightLeg = new THREE.Mesh(legGeometry, legMaterial);
    this.rightLeg.position.set(0.2, 0.3, 0);
    
    // Add all parts to the player model
    this.add(this.body);
    this.add(this.head);
    this.add(this.leftArm);
    this.add(this.rightArm);
    this.add(this.leftLeg);
    this.add(this.rightLeg);
  }
  
  /**
   * Creates a floating name tag above the player
   */
  createNameTag() {
    // Create canvas for name tag
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = 256;
    canvas.height = 64;
    
    // Set background
    context.fillStyle = 'rgba(0, 0, 0, 0.5)';
    context.fillRect(0, 0, canvas.width, canvas.height);
    
    // Set text properties
    context.font = 'Bold 24px Arial';
    context.fillStyle = 'white';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    
    // Draw player name
    context.fillText(this.playerName, canvas.width / 2, canvas.height / 2);
    
    // Create texture from canvas
    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    
    // Create a sprite material with the texture
    const material = new THREE.SpriteMaterial({ map: texture });
    
    // Create sprite with the material
    this.nameTag = new THREE.Sprite(material);
    this.nameTag.scale.set(2, 0.5, 1);
    this.nameTag.position.y = 2.7; // Position above the player's head
    
    // Add name tag to player model
    this.add(this.nameTag);
  }
  
  /**
   * Updates the player's position
   * @param {Object} position - Object containing x, y, z coordinates
   */
  updatePosition(position) {
    if (position) {
      console.log(`OtherPlayer ${this.playerName} (${this.playerId}) - Setting position:`, position);
      
      // In Minecraft, player position represents the position of their feet
      // Our model's origin is at its center, so we need to offset the Y position
      // to ensure the feet are at the correct Y coordinate
      
      // The player's total height is approximately 1.8 units (body height)
      // So we need to offset the model by half this height (0.9) to align the feet
      // with the ground at the given Y coordinate
      
      this.position.set(
        position.x, 
        position.y - 0.9, // Offset to align feet with the ground
        position.z
      );
      
      // Make player visible (in case it was hidden)
      this.visible = true;
      
      // Log the actual position after setting
      console.log(`OtherPlayer ${this.playerName} actual position:`, 
                 {x: this.position.x, y: this.position.y, z: this.position.z});
    }
  }
  
  /**
   * Updates the player's rotation
   * @param {Object} rotation - Object containing x, y, z rotation values
   */
  updateRotation(rotation) {
    if (rotation) {
      console.log(`OtherPlayer ${this.playerName} (${this.playerId}) - Setting rotation:`, rotation);
      
      // Rotate the entire player model based on y-axis rotation (looking left/right)
      // This ensures the whole player (body, arms, legs) faces the direction they're looking
      this.rotation.y = rotation.y;
      
      // We can also add some head tilt for looking up/down
      this.head.rotation.x = rotation.x;
      
      // Log the actual rotation after setting
      console.log(`OtherPlayer ${this.playerName} actual rotation:`, 
                 {
                   model: {x: this.rotation.x, y: this.rotation.y, z: this.rotation.z},
                   head: {x: this.head.rotation.x, y: this.head.rotation.y, z: this.head.rotation.z}
                 });
    }
  }
  
  /**
   * Creates a chat bubble above the player
   * @param {String} text - The text message to display
   */
  showChatBubble(text) {
    // Clear any existing chat timeout
    if (this.chatTimeout) {
      clearTimeout(this.chatTimeout);
      this.chatTimeout = null;
    }
    
    // Remove existing chat bubble if there is one
    if (this.chatBubble) {
      this.remove(this.chatBubble);
      this.chatBubble.material.dispose();
      this.chatBubble = null;
    }
    
    // Create canvas for chat bubble
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = 512;  // Wider for chat messages
    canvas.height = 128;
    
    // Set background with rounded corners (as much as possible in canvas)
    context.fillStyle = 'rgba(255, 255, 255, 0.85)';
    roundRect(context, 0, 0, canvas.width, canvas.height, 20, true, false);
    
    // Set text properties
    context.font = 'Bold 24px Arial';
    context.fillStyle = 'black';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    
    // Draw chat message with word wrap
    wrapText(context, text, canvas.width/2, canvas.height/2, canvas.width - 40, 28);
    
    // Create texture from canvas
    const texture = new THREE.CanvasTexture(canvas);
    texture.needsUpdate = true;
    
    // Create a sprite material with the texture
    const material = new THREE.SpriteMaterial({ map: texture });
    
    // Create sprite with the material
    this.chatBubble = new THREE.Sprite(material);
    this.chatBubble.scale.set(4, 1, 1);  // Wide chat bubble
    this.chatBubble.position.y = 3.5;    // Position well above the player's head
    
    // Add chat bubble to player model
    this.add(this.chatBubble);
    
    // Set timeout to remove chat bubble after a few seconds
    this.chatTimeout = setTimeout(() => {
      this.remove(this.chatBubble);
      this.chatBubble.material.dispose();
      this.chatBubble = null;
      this.chatTimeout = null;
    }, 8000);  // Display for 8 seconds
    
    // Helper function to draw rounded rectangles
    function roundRect(ctx, x, y, width, height, radius, fill, stroke) {
      ctx.beginPath();
      ctx.moveTo(x + radius, y);
      ctx.lineTo(x + width - radius, y);
      ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
      ctx.lineTo(x + width, y + height - radius);
      ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
      ctx.lineTo(x + radius, y + height);
      ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
      ctx.lineTo(x, y + radius);
      ctx.quadraticCurveTo(x, y, x + radius, y);
      ctx.closePath();
      if (fill) ctx.fill();
      if (stroke) ctx.stroke();
    }
    
    // Helper function to wrap text
    function wrapText(ctx, text, x, y, maxWidth, lineHeight) {
      const words = text.split(' ');
      let line = '';
      let lineCount = 0;
      
      for (let n = 0; n < words.length; n++) {
        const testLine = line + words[n] + ' ';
        const metrics = ctx.measureText(testLine);
        const testWidth = metrics.width;
        
        if (testWidth > maxWidth && n > 0) {
          ctx.fillText(line, x, y - lineHeight * 0.5 + lineCount * lineHeight);
          line = words[n] + ' ';
          lineCount++;
        } else {
          line = testLine;
        }
      }
      
      ctx.fillText(line, x, y - lineHeight * 0.5 + lineCount * lineHeight);
    }
  }
  
  /**
   * Sets the SuperSaiyan mode for the player
   * @param {Boolean} active - Whether to activate or deactivate SuperSaiyan mode
   */
  setSuperSaiyanMode(active) {
    console.log(`Setting SuperSaiyan mode for ${this.playerName} to ${active}`);
    this.isSuperSaiyanMode = active;
    
    if (active) {
      // Change player appearance for SuperSaiyan mode
      
      // Change body color to bright golden yellow
      this.body.material.color.set(0xFFD700);
      this.leftArm.material.color.set(0xFFD700);
      this.rightArm.material.color.set(0xFFD700);
      
      // Make head glow
      this.head.material.emissive = new THREE.Color(0xFF9900);
      this.head.material.emissiveIntensity = 0.5;
      
      // Create fire particle effect if it doesn't exist
      if (!this.fireParticles) {
        // Create a simple particle system for fire effect
        const particleCount = 50;
        const particleGeometry = new THREE.BufferGeometry();
        const positions = new Float32Array(particleCount * 3);
        
        // Create random starting positions for particles
        for (let i = 0; i < particleCount * 3; i += 3) {
          // Random position around the head
          positions[i] = (Math.random() - 0.5) * 0.8;
          positions[i + 1] = 2.0 + (Math.random() * 0.4);  // Above the head
          positions[i + 2] = (Math.random() - 0.5) * 0.8;
        }
        
        particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        
        // Create materials for particles with different colors for fire effect
        const particleMaterial = new THREE.PointsMaterial({
          color: 0xFF5500,
          size: 0.2,
          transparent: true,
          opacity: 0.8,
          blending: THREE.AdditiveBlending
        });
        
        this.fireParticles = new THREE.Points(particleGeometry, particleMaterial);
        this.add(this.fireParticles);
        
        // Store original positions for animation
        this.originalParticlePositions = [...positions];
        
        // Start SuperSaiyan animation
        this.animateSuperSaiyan();
      }
      
      // Create glow effect around player
      if (!this.glowEffect) {
        const glowGeometry = new THREE.SphereGeometry(1.2, 16, 16);
        const glowMaterial = new THREE.MeshBasicMaterial({
          color: 0xFFAA00,
          transparent: true,
          opacity: 0.3,
          side: THREE.BackSide,
          blending: THREE.AdditiveBlending
        });
        
        this.glowEffect = new THREE.Mesh(glowGeometry, glowMaterial);
        this.glowEffect.position.y = 0.9;  // Center on body
        this.add(this.glowEffect);
      }
    } else {
      // Restore original appearance
      this.body.material.color.set(0x3366FF);
      this.leftArm.material.color.set(0x3366FF);
      this.rightArm.material.color.set(0x3366FF);
      
      // Remove head glow
      this.head.material.emissive = new THREE.Color(0x000000);
      this.head.material.emissiveIntensity = 0;
      
      // Remove fire particles
      if (this.fireParticles) {
        this.remove(this.fireParticles);
        this.fireParticles.geometry.dispose();
        this.fireParticles.material.dispose();
        this.fireParticles = null;
      }
      
      // Remove glow effect
      if (this.glowEffect) {
        this.remove(this.glowEffect);
        this.glowEffect.geometry.dispose();
        this.glowEffect.material.dispose();
        this.glowEffect = null;
      }
      
      // Stop animation
      if (this.superSaiyanAnimationFrame) {
        cancelAnimationFrame(this.superSaiyanAnimationFrame);
        this.superSaiyanAnimationFrame = null;
      }
    }
  }
  
  /**
   * Animates the SuperSaiyan fire effect
   */
  animateSuperSaiyan() {
    if (!this.isSuperSaiyanMode || !this.fireParticles) return;
    
    const positions = this.fireParticles.geometry.attributes.position.array;
    const originalPositions = this.originalParticlePositions;
    const time = Date.now() * 0.005;
    
    // Animate each particle to create fire effect
    for (let i = 0; i < positions.length; i += 3) {
      // Get original position
      const x = originalPositions[i];
      const y = originalPositions[i + 1];
      const z = originalPositions[i + 2];
      
      // Add time-based variation
      positions[i] = x + Math.sin(time + i) * 0.1;
      positions[i + 1] = y + Math.cos(time + i * 0.5) * 0.1 + Math.sin(time * 2) * 0.05;
      positions[i + 2] = z + Math.cos(time + i * 0.7) * 0.1;
    }
    
    this.fireParticles.geometry.attributes.position.needsUpdate = true;
    
    // Pulse the glow effect
    if (this.glowEffect) {
      const scale = 1.0 + Math.sin(time * 2) * 0.1;
      this.glowEffect.scale.set(scale, scale, scale);
    }
    
    // Continue animation loop
    this.superSaiyanAnimationFrame = requestAnimationFrame(() => this.animateSuperSaiyan());
  }

  /**
   * Animates the player model based on movement
   * @param {Number} deltaTime - Time since last frame in seconds
   * @param {Boolean} isMoving - Whether the player is currently moving
   */
  animate(deltaTime, isMoving) {
    if (isMoving) {
      // Simple walking animation
      const time = Date.now() * 0.005;
      
      // Swing legs and arms opposite to each other
      this.leftLeg.rotation.x = Math.sin(time) * 0.5;
      this.rightLeg.rotation.x = Math.sin(time + Math.PI) * 0.5;
      this.leftArm.rotation.x = Math.sin(time + Math.PI) * 0.5;
      this.rightArm.rotation.x = Math.sin(time) * 0.5;
    } else {
      // Reset animations when not moving
      this.leftLeg.rotation.x = 0;
      this.rightLeg.rotation.x = 0;
      this.leftArm.rotation.x = 0;
      this.rightArm.rotation.x = 0;
    }
    
    // Always make the name tag and chat bubble face the camera
    if (this.nameTag) {
      this.nameTag.quaternion.copy(this.parent.quaternion);
    }
    
    if (this.chatBubble) {
      this.chatBubble.quaternion.copy(this.parent.quaternion);
    }
  }
}