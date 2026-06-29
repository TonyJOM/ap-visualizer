import { useEffect, useMemo, useRef, useState } from 'react';
import { makeSimFrame } from './simulator';
import { ConnectionState, SceneFrame } from './types';
import { isFrameStale } from './sceneMath';

type StreamMode = 'live' | 'sim';

type StreamState = {
  frame: SceneFrame | null;
  connectionState: ConnectionState;
  mode: StreamMode;
  setMode: (mode: StreamMode) => void;
  lastError: string | null;
};

type BusyMessage = { type: 'busy'; reason?: string };

export function parseSceneMessage(raw: string): SceneFrame | BusyMessage {
  const parsed = JSON.parse(raw) as SceneFrame | BusyMessage;
  if ('type' in parsed) {
    if (parsed.type === 'busy') {
      return parsed;
    }
    throw new Error(`Unknown stream message type: ${parsed.type}`);
  }
  if (parsed.schemaVersion !== 1) {
    throw new Error('Unsupported AP Visualizer scene schema.');
  }
  return parsed;
}

function websocketUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws/scene`;
}

export function useSceneStream(): StreamState {
  const [mode, setMode] = useState<StreamMode>('live');
  const [frame, setFrame] = useState<SceneFrame | null>(null);
  const [connectionState, setConnectionState] = useState<ConnectionState>('connecting');
  const [lastError, setLastError] = useState<string | null>(null);
  const simSequence = useRef(0);

  useEffect(() => {
    if (mode !== 'sim') {
      return undefined;
    }

    setConnectionState('sim');
    setLastError(null);
    const id = window.setInterval(() => {
      simSequence.current += 1;
      setFrame(makeSimFrame(simSequence.current));
    }, 50);
    simSequence.current += 1;
    setFrame(makeSimFrame(simSequence.current));

    return () => window.clearInterval(id);
  }, [mode]);

  useEffect(() => {
    if (mode !== 'live') {
      return undefined;
    }

    let closed = false;
    let reconnectTimer = 0;
    let staleTimer = 0;
    let socket: WebSocket | null = null;

    const connect = () => {
      if (closed) {
        return;
      }

      setConnectionState('connecting');
      socket = new WebSocket(websocketUrl());

      socket.addEventListener('open', () => {
        setConnectionState('waiting');
        setLastError(null);
      });

      socket.addEventListener('message', (event) => {
        try {
          const next = parseSceneMessage(event.data as string);
          if ('type' in next && next.type === 'busy') {
            setConnectionState('busy');
            setLastError(next.reason ?? 'Another AP Visualizer client is connected.');
            socket?.close();
            return;
          }
          setFrame(next as SceneFrame);
          setConnectionState(isFrameStale(next as SceneFrame) ? 'stale' : 'live');
        } catch (error) {
          setConnectionState('error');
          setLastError(error instanceof Error ? error.message : 'Unable to parse scene frame.');
        }
      });

      socket.addEventListener('close', () => {
        if (closed) {
          return;
        }
        setConnectionState((current) => (current === 'busy' ? current : 'waiting'));
        reconnectTimer = window.setTimeout(connect, 1500);
      });

      socket.addEventListener('error', () => {
        setConnectionState('error');
        setLastError('Unable to connect to AP Visualizer.');
      });
    };

    staleTimer = window.setInterval(() => {
      setFrame((current) => {
        if (current && isFrameStale(current)) {
          setConnectionState('stale');
        }
        return current;
      });
    }, 500);

    connect();

    return () => {
      closed = true;
      window.clearTimeout(reconnectTimer);
      window.clearInterval(staleTimer);
      socket?.close();
    };
  }, [mode]);

  return useMemo(() => ({ frame, connectionState, mode, setMode, lastError }), [frame, connectionState, mode, lastError]);
}
