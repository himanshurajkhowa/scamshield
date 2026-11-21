const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { execFileSync } = require('node:child_process');
const { createHarness } = require('./ui_harness.cjs');
const fixture = JSON.parse(fs.readFileSync('tests/fixtures/baseline_v1.json', 'utf8'));
const BASELINE = fixture.baseline;

function submit(harness) {
  harness.ids.examples.children[0].onclick();
  harness.ids['analyze-form'].onsubmit({ preventDefault() {} });
  return harness.XHR.latest;
}
function assertUnlocked({ ids }) {
  assert.equal(ids.check.disabled, false);
  assert.equal(ids.message.readOnly, false);
  assert.equal(ids.check.classList.contains('is-loading'), false);
  assert.equal(ids.workbench.attrs['aria-busy'], undefined);
  assert.ok(ids.examples.children.every(button => !button.disabled));
}
function uiState({ ids, document }) {
  return JSON.parse(JSON.stringify({
    elements: Object.fromEntries(Object.entries(ids).map(([id, element]) => [id, {
      value: element.value, text: element.textContent, hidden: element.hidden,
      disabled: element.disabled, readOnly: element.readOnly, attrs: element.attrs,
      className: element.className, innerHTML: element.innerHTML,
    }])),
    focused: Object.keys(ids).find(id => ids[id] === document.activeElement),
    chips: ids.examples.children.map(button => ({ value: button.textContent, attrs: button.attrs, disabled: button.disabled })),
  }));
}

for (const failure of ['network', 'timeout', 'json503', 'html500', 'invalidJSON']) {
  test(`XHR ${failure} releases loading state and permits retry`, () => {
    const h = createHarness();
    const request = submit(h);
    assert.ok(h.ids.check.classList.contains('is-loading'));
    if (failure === 'network') request.onerror();
    else if (failure === 'timeout') request.ontimeout();
    else {
      request.status = failure === 'json503' ? 503 : failure === 'html500' ? 500 : 200;
      request.responseText = failure === 'json503' ? '{"error":"Model unavailable"}' : '<html>Unavailable</html>';
      request.onload();
    }
    assertUnlocked(h);
    assert.ok(h.ids.error.textContent.length > 0);
    assert.equal(h.ids.result.hidden, true);
    submit(h);
    assert.equal(h.ids.error.textContent, '');
    assert.equal(h.ids.check.disabled, true);
  });
}

test('rejected scanner animation still reveals scanner and clears busy state', async () => {
  const h = createHarness();
  h.state.motionReduced = false; h.state.animationFailure = true;
  await h.ids.start.onclick();
  assert.equal(h.ids.scanner.hidden, false);
  assert.equal(h.ids['scanner-reveal'].hidden, true);
  assert.equal(h.ids.start.attrs['aria-busy'], undefined);
  assert.equal(h.document.activeElement, h.ids.message);
  h.ids.back.onclick();
  assert.equal(h.ids.landing.hidden, false);
});

test('rejected native theme snapshot releases guard and preserves saved preference', async () => {
  const h = createHarness({ experience: true });
  h.state.motionReduced = false;
  let skipped = 0;
  h.document.startViewTransition = update => {
    update();
    return { ready: Promise.reject(Error('Snapshot cancelled')), finished: Promise.resolve(), skipTransition() { skipped++; } };
  };
  await h.ids['welcome-theme'].onclick();
  assert.equal(h.local.get('scamshield-theme'), 'dark');
  assert.equal(skipped, 1);
  await h.ids['welcome-theme'].onclick();
  assert.equal(h.local.get('scamshield-theme'), 'light');
  assert.equal(skipped, 2);
});

test('blocked preference storage cannot prevent application initialization', () => {
  const h = createHarness();
  h.context.localStorage = { getItem() { throw Error('Blocked'); }, setItem() { throw Error('Blocked'); } };
  h.context.sessionStorage = h.context.localStorage;
  assert.doesNotThrow(() => vm.runInContext(fs.readFileSync('public/static/preferences.js', 'utf8'), h.context));
  assert.doesNotThrow(() => vm.runInContext(fs.readFileSync('public/static/experience.js', 'utf8'), h.context));
  h.ids['welcome-skip'].onclick();
  assert.equal(h.ids.welcome.hidden, true);
});

test('baseline and refactor produce identical DOM state for every captured result', t => {
  try { execFileSync('git', ['cat-file', '-e', `${BASELINE}^{commit}`], { stdio: 'pipe' }); }
  catch { t.skip('Historical baseline unavailable; state/failure regressions still run.'); return; }
  const before = createHarness({ revision: BASELINE, experience: true });
  const after = createHarness({ experience: true });
  for (const h of [before, after]) h.ids['welcome-skip'].onclick();
  assert.deepEqual(uiState(after), uiState(before));
  for (const entry of fixture.cases) {
    for (const h of [before, after]) {
      h.ids.message.value = entry.text;
      h.ids['analyze-form'].onsubmit({ preventDefault() {} });
      const request = h.XHR.latest;
      request.status = 200; request.responseText = JSON.stringify(entry.analysis);
      request.onload();
    }
    assert.deepEqual(uiState(after), uiState(before));
    for (const h of [before, after]) { h.yes.onclick(); h.ids.again.onclick(); }
    assert.deepEqual(uiState(after), uiState(before));
  }
});
