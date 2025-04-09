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
    this.nameTag.position.y = 2.5; // Position above the player's head
    
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
      console.log(`OtherPlayer ${this.name} (${this.id}) - Setting rotation:`, rotation);
      
      // Rotate the head and body based on y-axis rotation (looking left/right)
      this.body.rotation.y = rotation.y;
      this.head.rotation.y = rotation.y;
      
      // Log the actual rotation after setting
      console.log(`OtherPlayer ${this.name} actual head rotation:`, 
                 {x: this.head.rotation.x, y: this.head.rotation.y, z: this.head.rotation.z});
    }
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
    
    // Always make the name tag face the camera
    if (this.nameTag) {
      this.nameTag.quaternion.copy(this.parent.quaternion);
    }
  }
}