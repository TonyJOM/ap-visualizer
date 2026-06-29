import { expect, test } from '@playwright/test';

test('renders simulator view without blank canvas or overlapping essentials', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Simulator' }).click();
  await expect(page.getByLabel('Driving essentials')).toBeVisible();
  await expect(page.getByLabel('Driver assist status')).toBeVisible();
  await page.waitForTimeout(300);

  const canvas = page.locator('canvas');
  await expect(canvas).toBeVisible();
  const sample = await canvas.evaluate((node: HTMLCanvasElement) => {
    const context = node.getContext('webgl2') ?? node.getContext('webgl');
    if (!context) {
      return { nonblank: false };
    }
    const width = node.width;
    const height = node.height;
    const pixels = new Uint8Array(width * height * 4);
    context.readPixels(0, 0, width, height, context.RGBA, context.UNSIGNED_BYTE, pixels);
    let nonblank = 0;
    for (let index = 0; index < pixels.length; index += 4) {
      if (pixels[index] || pixels[index + 1] || pixels[index + 2] || pixels[index + 3]) {
        nonblank += 1;
      }
    }
    return { nonblank: nonblank > width * height * 0.2 };
  });
  expect(sample.nonblank).toBe(true);

  const essentials = await page.getByLabel('Driving essentials').boundingBox();
  const status = await page.getByLabel('Driver assist status').boundingBox();
  expect(essentials).not.toBeNull();
  expect(status).not.toBeNull();
  if (essentials && status) {
    const overlaps = essentials.x < status.x + status.width &&
      essentials.x + essentials.width > status.x &&
      essentials.y < status.y + status.height &&
      essentials.y + essentials.height > status.y;
    expect(overlaps).toBe(false);
  }
});
