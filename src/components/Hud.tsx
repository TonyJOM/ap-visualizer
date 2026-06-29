import { Activity, Gauge, RadioTower, Settings2 } from 'lucide-react';
import { ConnectionState, SceneFrame, displayMps } from '../lib/types';

type HudProps = {
  frame: SceneFrame | null;
  connectionState: ConnectionState;
  diagnosticsOpen: boolean;
  onToggleDiagnostics: () => void;
  onUseSimulator: () => void;
  onUseLive: () => void;
  mode: 'live' | 'sim';
  lastError: string | null;
};

function formatOptionalSpeed(speedMps: number | null | undefined, frame: SceneFrame | null): string {
  if (speedMps === null || speedMps === undefined || !frame) {
    return '--';
  }
  return String(displayMps(speedMps, frame.units));
}

export function Hud({ frame, connectionState, diagnosticsOpen, onToggleDiagnostics, onUseSimulator, onUseLive, mode, lastError }: HudProps): JSX.Element {
  const speed = frame?.ego.displaySpeed ?? 0;
  const unit = frame?.ego.speedUnit ?? 'mph';
  const stateLabel = connectionState === 'live' ? (frame?.ego.engaged ? 'Engaged' : 'Ready') : connectionState;
  const assistSource = frame?.assist.longitudinalPlanSource ?? '--';

  return (
    <>
      <section className="speed-cluster" aria-label="Driving essentials">
        <div className="speed-limit">{formatOptionalSpeed(frame?.cruise.speedLimitMps, frame)}<span>{unit}</span></div>
        <div className="speed-ring">
          <div className="speed-value">{speed}</div>
          <div className="speed-unit">{unit}</div>
          <div className="speed-arc" />
        </div>
        <div className="cluster-row">
          <span>Set</span>
          <strong>{formatOptionalSpeed(frame?.cruise.setSpeedMps, frame)}</strong>
        </div>
        <div className="cluster-row">
          <span>Gear</span>
          <strong>{frame?.ego.gear ?? '--'}</strong>
        </div>
        <div className="cluster-row">
          <span>Assist</span>
          <strong>{stateLabel}</strong>
        </div>
      </section>

      <section className="bottom-status" aria-label="Driver assist status">
        <div className="status-pill">
          <Activity size={18} />
          <span>{frame?.assist.shouldStop ? 'Model stop' : assistSource}</span>
        </div>
        <div className="status-pill">
          <Gauge size={18} />
          <span>{frame?.mode ?? mode}</span>
        </div>
        <div className="status-pill">
          <RadioTower size={18} />
          <span>{connectionState}</span>
        </div>
      </section>

      <div className="top-controls">
        <button type="button" className="icon-button" aria-label="Toggle diagnostics" title="Diagnostics" onClick={onToggleDiagnostics}>
          <Settings2 size={22} />
        </button>
      </div>

      {!frame && (
        <section className="waiting-state" aria-label="Connection status">
          <h1>AP Visualizer</h1>
          <p>{lastError ?? 'Waiting for live scene data.'}</p>
          <div className="waiting-actions">
            <button type="button" onClick={onUseSimulator}>Simulator</button>
            <button type="button" onClick={onUseLive}>Live</button>
          </div>
        </section>
      )}

      {diagnosticsOpen && (
        <aside className="diagnostics" aria-label="Diagnostics">
          <h2>Diagnostics</h2>
          <dl>
            <dt>Connection</dt>
            <dd>{connectionState}</dd>
            <dt>Mode</dt>
            <dd>{frame?.mode ?? mode}</dd>
            <dt>Sequence</dt>
            <dd>{frame?.sequence ?? '--'}</dd>
            <dt>Frame age</dt>
            <dd>{Math.round(frame?.diagnostics.frameAgeMs ?? 0)} ms</dd>
            <dt>Source</dt>
            <dd>{frame?.diagnostics.source ?? '--'}</dd>
            <dt>Stop intent</dt>
            <dd>{frame?.assist.shouldStop ? `${Math.round(frame.assist.stopDistanceM ?? 0)} m` : 'inactive'}</dd>
            <dt>Stale services</dt>
            <dd>{frame?.diagnostics.staleServices.join(', ') || 'none'}</dd>
          </dl>
        </aside>
      )}
    </>
  );
}

