import { test, expect } from '@playwright/test';

import { loadPyodide, newSheet, precision, parseLatexFloat } from './utility.mjs';

let page;

test.beforeAll(async ({ browser }) => { page = await loadPyodide(browser, page); });
test.beforeEach(async () => { await newSheet(page); });

test('Drag select multiple cells, copy, and paste them as a block', async () => {
  await page.locator('#cell-0 >> math-field.editable').type('1+1=');
  await page.locator('#add-math-cell').click();
  await page.locator('#cell-1 >> math-field.editable').type('2+2=');
  await page.locator('#add-math-cell').click();
  await page.locator('#cell-2 >> math-field.editable').type('3+3=');

  await page.waitForSelector('text=Updating...', {state: 'detached'});

  const copiedBlock = await page.evaluate(() => window.forceSerializeCellRange(0, 1));
  expect(copiedBlock).toHaveLength(2);

  await page.evaluate(() => window.forceInsertCellBlockAt(2, window.forceSerializeCellRange(0, 1)));

  await page.waitForSelector('text=Updating...', {state: 'detached'});

  await expect(page.locator('math-field.editable')).toHaveCount(5);

  const values = [];
  for (let i = 0; i < 5; i++) {
    values.push(parseLatexFloat(await page.textContent(`#result-value-${i}`)));
  }

  expect(values[0]).toBeCloseTo(2, precision);
  expect(values[1]).toBeCloseTo(4, precision);
  expect(values[2]).toBeCloseTo(2, precision);
  expect(values[3]).toBeCloseTo(4, precision);
  expect(values[4]).toBeCloseTo(6, precision);
});
