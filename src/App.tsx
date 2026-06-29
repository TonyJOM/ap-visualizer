import { useMemo, useState } from 'react';
import { Hud } from './components/Hud';
import { isFrameStale } from './lib/sceneMath';
import { useSceneStream } from './lib/useSceneStream';
import { SceneCanvas } from './rendering/SceneCanvas';

export function App(): JSX.Element {
  const { frame, connectionState, mode, setMode, lastError } = useSceneStream();
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(false);
  const stale = useMemo(() => (frame ? isFrameStale(frame) : false), [frame]);

  return (
    <main className={`app-shell ${stale ? 'is-stale' : ''}`}>
      <SceneCanvas frame={frame} stale={stale} />
      <Hud
        frame={frame}
        connectionState={stale ? 'stale' : connectionState}
        diagnosticsOpen={diagnosticsOpen}
        onToggleDiagnostics={() => setDiagnosticsOpen((open) => !open)}
        onUseSimulator={() => setMode('sim')}
        onUseLive={() => setMode('live')}
        mode={mode}
        lastError={lastError}
      />
      <div className="surface-vignette" />
    </main>
  );
}

