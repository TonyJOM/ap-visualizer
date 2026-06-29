import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

describe('styles', () => {
  it('contains responsive portrait, landscape, and system-theme states', () => {
    const css = readFileSync(join(process.cwd(), 'src/styles.css'), 'utf8');

    expect(css).toContain('@media (orientation: portrait)');
    expect(css).toContain('@media (max-width: 700px) and (orientation: landscape)');
    expect(css).toContain('@media (prefers-color-scheme: dark)');
  });
});
