import { test, expect } from '@playwright/test';
import { clickAcceptIfPresent } from './utility.mjs';

test('Bookmark share falls back to original share link when too large', async ({ page }) => {
  await page.goto('/');

  await page.route('**/documents/save/**', async route => {
    const fallbackId = '2222222222222222222222';
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        url: `http://127.0.0.1:8788/${fallbackId}`,
        hash: fallbackId,
        history: []
      })
    });
  });

  await clickAcceptIfPresent(page);

  await page.evaluate(() => {
    const heading = document.querySelector('h1');
    const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
    const chunkSize = 65536;
    const totalSize = 270000;
    const chunks = [];

    for (let remaining = totalSize; remaining > 0; remaining -= chunkSize) {
      const size = Math.min(remaining, chunkSize);
      const bytes = crypto.getRandomValues(new Uint8Array(size));
      const chars = new Array(size);

      for (let index = 0; index < size; index += 1) {
        chars[index] = alphabet[bytes[index] % alphabet.length];
      }

      chunks.push(chars.join(''));
    }

    heading.textContent = chunks.join('');
    heading.dispatchEvent(new Event('input', { bubbles: true }));
  });

  await page.click('#upload-sheet');
  await page.click('text=Get Bookmark Link');
  await page.waitForSelector('text=Bookmark Too Large');
  await page.click('text=Use Original Share Link');
  await page.waitForSelector('#shareable-link');

  const fallbackUrl = new URL(await page.$eval('#shareable-link', el => el.value));

  expect(fallbackUrl.hash).toBe('');
  expect(fallbackUrl.pathname.length).toBe(23);
});

test('Bookmark share updates the address bar when it succeeds', async ({ page }) => {
  await page.goto('/');

  await clickAcceptIfPresent(page);

  await page.click('#upload-sheet');
  await page.click('text=Get Bookmark Link');

  await page.waitForSelector('#shareable-link');
  await page.waitForFunction(() => window.location.hash.startsWith('#bm1.'), null, { timeout: 10000 });

  const bookmarkUrl = new URL(page.url());
  expect(bookmarkUrl.hash.startsWith('#bm1.')).toBeTruthy();
  expect(bookmarkUrl.pathname).toBe('/');
});
