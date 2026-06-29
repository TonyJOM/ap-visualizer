import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { findPathYAtDistance, normalizeLaneOpacity } from '../lib/sceneMath';
import { SceneFrame } from '../lib/types';

type SceneCanvasProps = {
  frame: SceneFrame | null;
  stale: boolean;
};

const toWorld = (point: { x: number; y: number; z: number }): THREE.Vector3 => new THREE.Vector3(point.y, point.z + 0.03, -point.x);

function makeLine(points: THREE.Vector3[], color: number, opacity: number, width = 0.04): THREE.Line {
  const geometry = new THREE.BufferGeometry().setFromPoints(points);
  const material = new THREE.LineBasicMaterial({
    color,
    transparent: true,
    opacity,
    linewidth: width
  });
  return new THREE.Line(geometry, material);
}

function makeTruck(): THREE.Group {
  const truck = new THREE.Group();

  const body = new THREE.Mesh(
    new THREE.BoxGeometry(2.05, 0.64, 4.55),
    new THREE.MeshStandardMaterial({ color: 0x17a7a5, roughness: 0.62, metalness: 0.18 })
  );
  body.position.y = 0.48;
  body.position.z = -0.2;
  truck.add(body);

  const cab = new THREE.Mesh(
    new THREE.BoxGeometry(1.82, 0.55, 1.78),
    new THREE.MeshStandardMaterial({ color: 0x0f2327, roughness: 0.45, metalness: 0.12 })
  );
  cab.position.set(0, 0.95, -0.68);
  truck.add(cab);

  const bedCover = new THREE.Mesh(
    new THREE.BoxGeometry(1.84, 0.12, 1.35),
    new THREE.MeshStandardMaterial({ color: 0x182625, roughness: 0.6 })
  );
  bedCover.position.set(0, 0.85, 1.12);
  truck.add(bedCover);

  const light = new THREE.Mesh(
    new THREE.BoxGeometry(1.55, 0.06, 0.06),
    new THREE.MeshStandardMaterial({ color: 0xff4e44, emissive: 0x4c0705, emissiveIntensity: 0.7 })
  );
  light.position.set(0, 0.62, 2.12);
  truck.add(light);

  const wheelMaterial = new THREE.MeshStandardMaterial({ color: 0x1b1d1c, roughness: 0.75 });
  for (const x of [-1.08, 1.08]) {
    for (const z of [-1.55, 1.55]) {
      const wheel = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.32, 0.22, 22), wheelMaterial);
      wheel.rotation.z = Math.PI / 2;
      wheel.position.set(x, 0.28, z);
      truck.add(wheel);
    }
  }

  truck.rotation.y = Math.PI;
  return truck;
}

function disposeObject(object: THREE.Object3D): void {
  object.traverse((child) => {
    const mesh = child as THREE.Mesh;
    if (mesh.geometry) {
      mesh.geometry.dispose();
    }
    const material = mesh.material as THREE.Material | THREE.Material[] | undefined;
    if (Array.isArray(material)) {
      material.forEach((item) => item.dispose());
    } else if (material) {
      material.dispose();
    }
  });
}

export function SceneCanvas({ frame, stale }: SceneCanvasProps): JSX.Element {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const dynamicRef = useRef<THREE.Group | null>(null);
  const animationRef = useRef<number>(0);
  const frameRef = useRef<SceneFrame | null>(frame);
  const staleRef = useRef(stale);

  useEffect(() => {
    frameRef.current = frame;
    staleRef.current = stale;
  }, [frame, stale]);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) {
      return undefined;
    }

    const scene = new THREE.Scene();
    scene.background = null;
    scene.fog = new THREE.Fog(0xdfe8e1, 46, 176);
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(42, host.clientWidth / Math.max(host.clientHeight, 1), 0.1, 260);
    camera.position.set(0, 13, 19);
    camera.lookAt(0, 0.4, -58);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance', preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(host.clientWidth, host.clientHeight);
    renderer.shadowMap.enabled = false;
    host.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    scene.add(new THREE.HemisphereLight(0xffffff, 0x7a817f, 2.0));
    const sun = new THREE.DirectionalLight(0xffffff, 1.1);
    sun.position.set(-4, 10, 3);
    scene.add(sun);

    const road = new THREE.Mesh(
      new THREE.PlaneGeometry(28, 205, 1, 1),
      new THREE.MeshStandardMaterial({ color: 0xe3ebe5, roughness: 0.95, metalness: 0 })
    );
    road.rotation.x = -Math.PI / 2;
    road.position.z = -83;
    scene.add(road);

    const dynamic = new THREE.Group();
    dynamicRef.current = dynamic;
    scene.add(dynamic);
    scene.add(makeTruck());

    const resize = () => {
      const width = host.clientWidth;
      const height = Math.max(host.clientHeight, 1);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(host);

    const renderDynamic = () => {
      const group = dynamicRef.current;
      const currentFrame = frameRef.current;
      if (!group || !currentFrame) {
        return;
      }

      while (group.children.length) {
        const child = group.children.pop();
        if (child) {
          disposeObject(child);
        }
      }

      const staleOpacity = staleRef.current ? 0.35 : 1;
      group.add(makeLine(currentFrame.model.path.map(toWorld), 0x17a7a5, 0.5 * staleOpacity));

      currentFrame.model.laneLines.forEach((lane, index) => {
        const opacity = normalizeLaneOpacity(currentFrame.model.laneLineProbs[index] ?? 0, staleRef.current);
        group.add(makeLine(lane.map(toWorld), index === 1 || index === 2 ? 0xb6cbc2 : 0x93aaa1, opacity));
      });

      currentFrame.model.roadEdges.forEach((edge) => {
        group.add(makeLine(edge.map(toWorld), 0x9ca7a1, 0.35 * staleOpacity));
      });

      currentFrame.model.leads.filter((lead) => lead.status).forEach((lead) => {
        const leadMesh = new THREE.Mesh(
          new THREE.BoxGeometry(1.9, 0.7, 4.0),
          new THREE.MeshStandardMaterial({ color: 0x2f3b3a, roughness: 0.7, transparent: true, opacity: 0.82 * staleOpacity })
        );
        leadMesh.position.set(lead.y, 0.55, -lead.x);
        group.add(leadMesh);
      });

      const stopDistance = currentFrame.assist.stopDistanceM;
      if (currentFrame.assist.shouldStop && stopDistance !== null) {
        const centerY = findPathYAtDistance(currentFrame.model.path, stopDistance);
        const stop = new THREE.Mesh(
          new THREE.BoxGeometry(6.2, 0.045, 0.34),
          new THREE.MeshStandardMaterial({ color: 0xf0b23d, emissive: 0x4d3000, emissiveIntensity: 0.16, transparent: true, opacity: 0.9 * staleOpacity })
        );
        stop.position.set(centerY, 0.08, -stopDistance);
        group.add(stop);
      }
    };

    const animate = () => {
      renderDynamic();
      renderer.render(scene, camera);
      animationRef.current = window.requestAnimationFrame(animate);
    };
    animate();

    return () => {
      window.cancelAnimationFrame(animationRef.current);
      observer.disconnect();
      renderer.dispose();
      host.removeChild(renderer.domElement);
      disposeObject(scene);
    };
  }, []);

  return <div className="scene-canvas" ref={hostRef} aria-label="AP Visualizer road scene" />;
}
