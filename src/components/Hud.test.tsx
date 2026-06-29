import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Hud } from './Hud';
import { makeSimFrame } from '../lib/simulator';

describe('Hud', () => {
  it('renders driving essentials and diagnostics', () => {
    const frame = makeSimFrame(1, 1_000_000);
    render(
      <Hud
        frame={frame}
        connectionState="live"
        diagnosticsOpen
        onToggleDiagnostics={vi.fn()}
        onUseSimulator={vi.fn()}
        onUseLive={vi.fn()}
        mode="sim"
        lastError={null}
      />
    );

    expect(screen.getByLabelText('Driving essentials')).toHaveTextContent('Gear');
    expect(screen.getByLabelText('Driver assist status')).toHaveTextContent('live');
    expect(screen.getByLabelText('Diagnostics')).toHaveTextContent('Frame age');
  });

  it('renders no-data controls clearly', () => {
    render(
      <Hud
        frame={null}
        connectionState="waiting"
        diagnosticsOpen={false}
        onToggleDiagnostics={vi.fn()}
        onUseSimulator={vi.fn()}
        onUseLive={vi.fn()}
        mode="live"
        lastError="Waiting for live scene data."
      />
    );

    expect(screen.getByRole('heading', { name: 'AP Visualizer' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Simulator' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Live' })).toBeInTheDocument();
  });
});

