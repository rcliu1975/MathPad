import { test, expect } from '@playwright/test';

import { precision, loadPyodide, newSheet, parseLatexFloat } from './utility.mjs';

let page;

// loading pyodide takes a long time (especially in resource constrained CI environments)
// load page once and use for all tests in this file
test.beforeAll(async ({ browser }) => {page = await loadPyodide(browser, page);} );

// give each test a blank sheet to start with (this doesn't reload pyodide)
test.beforeEach(async () => {await newSheet(page)});


test('Test autosave checkpoints', async ({ browserName }) => {
  await page.setViewportSize({ width: 1400, height: 1400 });

  // Change title
  await page.getByRole('heading', { name: 'New Sheet' }).click({ clickCount: 3 });
  await page.type('text=New Sheet', 'Checkpoint Recovery');

  await page.setLatex(0, '1=');

  await expect.poll(async () => page.url(), {
    timeout: 20000
  }).toContain('#b2.');
  await expect.poll(async () => page.evaluate(() => window.history.state?.checkpointHash), {
    timeout: 20000
  }).toBeFalsy();
  expect(page.url()).not.toContain('temp-checkpoint');

  // change the sheet after checkpoint creation so we can verify recovery
  await page.setLatex(0, '2=');

  const recentSheetInfo = await page.evaluate(() => new Promise((resolve, reject) => {
    const req = indexedDB.open('keyval-store');
    req.onerror = () => reject(req.error);
    req.onsuccess = () => {
      const db = req.result;
      const tx = db.transaction('keyval', 'readonly');
      const store = tx.objectStore('keyval');
      const recentReq = store.get('recentSheets');
      recentReq.onerror = () => reject(recentReq.error);
      recentReq.onsuccess = () => {
        const recentSheets = recentReq.result;
        const entry = [...recentSheets.entries()].find(([, value]) => typeof value.url === 'string' && value.url.includes('#b2.'));
        resolve(entry ? {title: entry[1].title, url: entry[1].url, checkpointHash: entry[1].checkpointHash ?? null} : null);
      };
    };
  }));
  expect(recentSheetInfo).not.toBeNull();
  expect(recentSheetInfo.url).toContain('#b2.');
  expect(recentSheetInfo.checkpointHash).toBeNull();

  // recover from the latest autosave via Recent Sheets
  await page.locator('button.bx--header__menu-toggle').click();
  await page.getByRole('button', { name: 'Recent Sheets' }).click();
  const recentSheet = page.locator('div.side-nav-title').filter({ hasText: recentSheetInfo.title }).first();
  await expect(recentSheet).toBeVisible();
  await recentSheet.click();
  await page.locator('h3 >> text=Retrieving Sheet').waitFor({state: 'detached', timeout: 5000});
  await page.waitForSelector('.status-footer', { state: 'detached', timeout: 5000 });

  expect(page.url()).not.toContain('temp-checkpoint');
  expect(page.url()).toContain('#b2.');

  const content = await page.locator('#result-value-0').textContent();
  expect(parseLatexFloat(content)).toBeCloseTo(2, precision);

  await expect(page.getByRole('heading', { name: 'Checkpoint Recovery' })).toBeVisible();
});
