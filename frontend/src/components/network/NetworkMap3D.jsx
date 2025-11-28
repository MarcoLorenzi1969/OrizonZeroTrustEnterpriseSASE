import React, { useRef, useEffect, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls';
import { CSS2DRenderer, CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer';
import { useNodesStore } from '../../store/nodesStore';

const NetworkMap3D = () => {
  const mountRef = useRef(null);
  const sceneRef = useRef(null);
  const rendererRef = useRef(null);
  const labelRendererRef = useRef(null);
  const cameraRef = useRef(null);
  const controlsRef = useRef(null);
  const nodesRef = useRef({});
  const connectionsRef = useRef([]);
  const frameId = useRef(null);

  const { nodes, connections, selectedNode, setSelectedNode } = useNodesStore();
  const [hoveredNode, setHoveredNode] = useState(null);

  useEffect(() => {
    if (!mountRef.current) return;

    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0a0a0a);
    scene.fog = new THREE.Fog(0x0a0a0a, 50, 200);
    sceneRef.current = scene;

    // Camera setup
    const camera = new THREE.PerspectiveCamera(
      75,
      mountRef.current.clientWidth / mountRef.current.clientHeight,
      0.1,
      1000
    );
    camera.position.set(30, 30, 30);
    cameraRef.current = camera;

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    mountRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // CSS2D Renderer for labels
    const labelRenderer = new CSS2DRenderer();
    labelRenderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
    labelRenderer.domElement.style.position = 'absolute';
    labelRenderer.domElement.style.top = '0px';
    labelRenderer.domElement.style.pointerEvents = 'none';
    mountRef.current.appendChild(labelRenderer.domElement);
    labelRendererRef.current = labelRenderer;

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.minDistance = 10;
    controls.maxDistance = 100;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.5;
    controlsRef.current = controls;

    // Lighting
    const ambientLight = new THREE.AmbientLight(0x404040, 1);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 1);
    directionalLight.position.set(50, 50, 50);
    directionalLight.castShadow = true;
    directionalLight.shadow.camera.left = -50;
    directionalLight.shadow.camera.right = 50;
    directionalLight.shadow.camera.top = 50;
    directionalLight.shadow.camera.bottom = -50;
    scene.add(directionalLight);

    // Add grid
    const gridHelper = new THREE.GridHelper(100, 20, 0x444444, 0x222222);
    scene.add(gridHelper);

    // Add central hub (DigitalOcean server)
    const hubGeometry = new THREE.OctahedronGeometry(3, 0);
    const hubMaterial = new THREE.MeshPhongMaterial({
      color: 0x00ff88,
      emissive: 0x00ff88,
      emissiveIntensity: 0.3,
      shininess: 100,
    });
    const hub = new THREE.Mesh(hubGeometry, hubMaterial);
    hub.position.set(0, 5, 0);
    hub.castShadow = true;
    hub.receiveShadow = true;
    scene.add(hub);

    // Hub label
    const hubLabelDiv = document.createElement('div');
    hubLabelDiv.className = 'node-label hub-label';
    hubLabelDiv.textContent = 'ORIZON HUB';
    hubLabelDiv.style.color = '#00ff88';
    hubLabelDiv.style.fontSize = '14px';
    hubLabelDiv.style.fontWeight = 'bold';
    hubLabelDiv.style.textShadow = '0 0 10px #00ff88';
    const hubLabel = new CSS2DObject(hubLabelDiv);
    hubLabel.position.set(0, 2, 0);
    hub.add(hubLabel);

    // Particle system for background
    const particlesGeometry = new THREE.BufferGeometry();
    const particlesCount = 1000;
    const positions = new Float32Array(particlesCount * 3);

    for (let i = 0; i < particlesCount * 3; i += 3) {
      positions[i] = (Math.random() - 0.5) * 200;
      positions[i + 1] = (Math.random() - 0.5) * 200;
      positions[i + 2] = (Math.random() - 0.5) * 200;
    }

    particlesGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const particlesMaterial = new THREE.PointsMaterial({
      color: 0x888888,
      size: 0.5,
      transparent: true,
      opacity: 0.6,
    });

    const particles = new THREE.Points(particlesGeometry, particlesMaterial);
    scene.add(particles);

    // Raycaster for mouse interaction
    const raycaster = new THREE.Raycaster();
    const mouse = new THREE.Vector2();

    const onMouseMove = (event) => {
      const rect = mountRef.current.getBoundingClientRect();
      mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
      mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
    };

    const onMouseClick = (event) => {
      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(Object.values(nodesRef.current));
      
      if (intersects.length > 0) {
        const clickedNode = intersects[0].object;
        setSelectedNode(clickedNode.userData.id);
      }
    };

    window.addEventListener('mousemove', onMouseMove);
    mountRef.current.addEventListener('click', onMouseClick);

    // Animation loop
    const animate = () => {
      frameId.current = requestAnimationFrame(animate);

      // Rotate hub
      hub.rotation.y += 0.01;

      // Update particles
      particles.rotation.y += 0.0002;
      particles.rotation.x += 0.0001;

      // Pulse selected node
      if (selectedNode && nodesRef.current[selectedNode]) {
        const node = nodesRef.current[selectedNode];
        const scale = 1 + Math.sin(Date.now() * 0.003) * 0.1;
        node.scale.set(scale, scale, scale);
      }

      // Update connections animation
      connectionsRef.current.forEach((connection) => {
        if (connection.material.uniforms) {
          connection.material.uniforms.dashOffset.value -= 0.01;
        }
      });

      // Check hover
      raycaster.setFromCamera(mouse, camera);
      const intersects = raycaster.intersectObjects(Object.values(nodesRef.current));
      
      if (intersects.length > 0) {
        const hoveredObject = intersects[0].object;
        if (hoveredNode !== hoveredObject.userData.id) {
          setHoveredNode(hoveredObject.userData.id);
          document.body.style.cursor = 'pointer';
        }
      } else {
        if (hoveredNode) {
          setHoveredNode(null);
          document.body.style.cursor = 'default';
        }
      }

      controls.update();
      renderer.render(scene, camera);
      labelRenderer.render(scene, camera);
    };

    animate();

    // Handle resize
    const handleResize = () => {
      if (!mountRef.current) return;
      
      camera.aspect = mountRef.current.clientWidth / mountRef.current.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
      labelRenderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight);
    };

    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', onMouseMove);
      if (mountRef.current) {
        mountRef.current.removeEventListener('click', onMouseClick);
      }
      if (frameId.current) {
        cancelAnimationFrame(frameId.current);
      }
      if (mountRef.current && renderer.domElement) {
        mountRef.current.removeChild(renderer.domElement);
      }
      if (mountRef.current && labelRenderer.domElement) {
        mountRef.current.removeChild(labelRenderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  // Update nodes and connections
  useEffect(() => {
    if (!sceneRef.current) return;

    // Clear existing nodes
    Object.values(nodesRef.current).forEach((node) => {
      sceneRef.current.remove(node);
    });
    nodesRef.current = {};

    // Clear existing connections
    connectionsRef.current.forEach((connection) => {
      sceneRef.current.remove(connection);
    });
    connectionsRef.current = [];

    // Add nodes
    nodes.forEach((nodeData, index) => {
      const angle = (index / nodes.length) * Math.PI * 2;
      const radius = 20;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;
      const y = Math.random() * 10;

      // Node geometry based on type
      let geometry;
      let color;
      
      switch (nodeData.type) {
        case 'server':
          geometry = new THREE.BoxGeometry(2, 2, 2);
          color = 0x4488ff;
          break;
        case 'workstation':
          geometry = new THREE.SphereGeometry(1.5, 16, 16);
          color = 0xff8844;
          break;
        case 'mobile':
          geometry = new THREE.ConeGeometry(1, 2, 8);
          color = 0x88ff44;
          break;
        default:
          geometry = new THREE.TetrahedronGeometry(1.5);
          color = 0xff4488;
      }

      const material = new THREE.MeshPhongMaterial({
        color,
        emissive: color,
        emissiveIntensity: 0.1,
      });

      const node = new THREE.Mesh(geometry, material);
      node.position.set(x, y, z);
      node.castShadow = true;
      node.receiveShadow = true;
      node.userData = nodeData;

      // Add label
      const labelDiv = document.createElement('div');
      labelDiv.className = 'node-label';
      labelDiv.textContent = nodeData.name || nodeData.id;
      labelDiv.style.color = '#ffffff';
      labelDiv.style.fontSize = '12px';
      const label = new CSS2DObject(labelDiv);
      label.position.set(0, 2, 0);
      node.add(label);

      // Status indicator
      const statusGeometry = new THREE.SphereGeometry(0.3, 8, 8);
      const statusColor = nodeData.status === 'online' ? 0x00ff00 : 
                         nodeData.status === 'warning' ? 0xffaa00 : 0xff0000;
      const statusMaterial = new THREE.MeshBasicMaterial({ color: statusColor });
      const statusIndicator = new THREE.Mesh(statusGeometry, statusMaterial);
      statusIndicator.position.set(0, 2.5, 0);
      node.add(statusIndicator);

      sceneRef.current.add(node);
      nodesRef.current[nodeData.id] = node;

      // Add connection to hub
      const points = [];
      points.push(new THREE.Vector3(0, 5, 0)); // Hub position
      points.push(new THREE.Vector3(x, y, z)); // Node position

      const connectionGeometry = new THREE.BufferGeometry().setFromPoints(points);
      
      // Animated dashed line shader
      const connectionMaterial = new THREE.ShaderMaterial({
        uniforms: {
          color: { value: new THREE.Color(0x00ffaa) },
          dashOffset: { value: 0 },
        },
        vertexShader: `
          varying vec2 vUv;
          void main() {
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          uniform vec3 color;
          uniform float dashOffset;
          varying vec2 vUv;
          void main() {
            float dash = step(0.5, fract(vUv.x * 10.0 - dashOffset));
            if (dash < 0.5) discard;
            gl_FragColor = vec4(color, 1.0);
          }
        `,
        transparent: true,
      });

      const connection = new THREE.Line(connectionGeometry, connectionMaterial);
      sceneRef.current.add(connection);
      connectionsRef.current.push(connection);
    });
  }, [nodes]);

  // Update hover effect
  useEffect(() => {
    Object.entries(nodesRef.current).forEach(([id, node]) => {
      if (id === hoveredNode) {
        node.material.emissiveIntensity = 0.5;
        node.scale.set(1.2, 1.2, 1.2);
      } else {
        node.material.emissiveIntensity = 0.1;
        if (id !== selectedNode) {
          node.scale.set(1, 1, 1);
        }
      }
    });
  }, [hoveredNode, selectedNode]);

  return (
    <div className="relative w-full h-full bg-gray-900">
      <div ref={mountRef} className="w-full h-full" />
      
      {/* Overlay UI */}
      <div className="absolute top-4 left-4 bg-black/50 backdrop-blur-sm rounded-lg p-4">
        <h3 className="text-green-400 font-bold mb-2">NETWORK STATUS</h3>
        <div className="text-white text-sm space-y-1">
          <div>Nodes: {nodes.length}</div>
          <div>Active Connections: {connections.length}</div>
          <div>Hub: {import.meta.env.VITE_HUB_HOST || window.location.hostname}</div>
        </div>
      </div>

      {selectedNode && (
        <div className="absolute top-4 right-4 bg-black/50 backdrop-blur-sm rounded-lg p-4 max-w-xs">
          <h3 className="text-green-400 font-bold mb-2">NODE DETAILS</h3>
          <div className="text-white text-sm space-y-1">
            <div>ID: {selectedNode}</div>
            <div>Status: {nodesRef.current[selectedNode]?.userData?.status || 'unknown'}</div>
            <div>Type: {nodesRef.current[selectedNode]?.userData?.type || 'unknown'}</div>
            <div>IP: {nodesRef.current[selectedNode]?.userData?.ip || 'N/A'}</div>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-black/50 backdrop-blur-sm rounded-lg p-3">
        <div className="flex space-x-4 text-xs">
          <div className="flex items-center">
            <div className="w-3 h-3 bg-blue-500 rounded-sm mr-1"></div>
            <span className="text-white">Server</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 bg-orange-500 rounded-full mr-1"></div>
            <span className="text-white">Workstation</span>
          </div>
          <div className="flex items-center">
            <div className="w-3 h-3 bg-green-500 rounded-sm rotate-45 mr-1"></div>
            <span className="text-white">Mobile</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NetworkMap3D;
