(() => {
  'use strict';
  const { getElement: $, isReducedMotion: reducedMotion, showScanner: scanner } = window.ScamShieldUI;
  const icons = {
    arrow: '<path d="M5 12h14m-6-6 6 6-6 6"/>',
    check: '<path d="m5 12 4 4L19 6"/>',
    warning: '<path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v5m0 3h.01"/>',
    lock: '<rect x="5" y="10" width="14" height="11" rx="4"/><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2"/>',
    moon: '<path d="M20 15a8 8 0 0 1-11-11 9 9 0 1 0 11 11Z"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1 1m12 12 1 1M5 19l1-1M18 6l1-1"/>'
  };
  function icon(name) {
    return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name]}</svg>`;
  }
  const PUNCH_CONTACT_FRAME = 30;
  const INTRO_FINAL_HOLD_MS = 700;
  let welcomePlayer, resultPlayer, welcomeTimer;
  let themeTransitionBusy = false;
  function playAsset(container, name, onComplete) {
    if (reducedMotion() || !window.lottie) return null;
    try {
      const player = window.lottie.loadAnimation({
        container,
        renderer: 'svg',
        loop: false,
        autoplay: false,
        path: `/static/animations/${name}.json`,
        rendererSettings: { progressiveLoad: true }
      });
      player.addEventListener('DOMLoaded', () => {
        player.setSpeed(name === 'lock' ? 1.5 : .8);
        if (!reducedMotion()) player.goToAndPlay(0, true);
      });
      if (onComplete) player.addEventListener('complete', onComplete);
      player.addEventListener('data_failed', () => {
        if (onComplete) onComplete();
      });
      return player;
    } catch (_) {
      return null;
    }
  }
  function replayIntro() {
    scanner(false);
    clearTimeout(welcomeTimer);
    if (welcomePlayer) {
      welcomePlayer.destroy();
      welcomePlayer = null;
    }
    document.documentElement.dataset.welcome = '';
    $('welcome').hidden = false;
    $('app-shell').inert = true;
    $('welcome-stage').hidden = true;
    $('welcome-go').disabled = false;
    $('welcome-boxer').replaceChildren();
    $('scam-word').removeAttribute('style');
    $('scam-word').setAttribute('data-hit', 'false');
    $('welcome-status').textContent = 'Your messages stay out of our storage.';
    $('welcome-title').focus({ preventScroll: true });
  }
  function finishWelcome() {
    clearTimeout(welcomeTimer);
    if (welcomePlayer) {
      welcomePlayer.destroy();
      welcomePlayer = null;
    }
    try {
      sessionStorage.setItem('scamshield-welcome', 'done');
    } catch (_) {
    }
    document.documentElement.dataset.welcome = 'done';
    $('welcome').hidden = true;
    $('app-shell').inert = false;
    $('start').focus({ preventScroll: true });
  }
  function initializeThemeControls() {
    const toggle = $('theme-toggle');
    const toggles = [toggle, $('welcome-theme')];
    const syncTheme = () => {
      const dark = document.documentElement.dataset.theme === 'dark';
      toggles.forEach(button => {
        button.innerHTML = icon(dark ? 'sun' : 'moon');
        button.setAttribute('aria-pressed', String(dark));
        button.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
      });
    };
    syncTheme();
    const changeTheme = async button => {
      if (themeTransitionBusy) return;
      const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      let applied = false, transition;
      const apply = () => {
        if (applied) return;
        applied = true;
        document.documentElement.dataset.theme = next;
        try {
          localStorage.setItem('scamshield-theme', next);
        } catch (_) {
        }
        syncTheme();
      };
      if (reducedMotion() || !document.startViewTransition || !document.documentElement.animate) {
        apply();
        return;
      }
      const rect = button.getBoundingClientRect(), x = rect.left + rect.width / 2, y = rect.top + rect.height / 2;
      const radius = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
      themeTransitionBusy = true;
      try {
        transition = document.startViewTransition(apply);
        transition.finished.catch(() => {
        });
        await transition.ready;
        await document.documentElement.animate([{ clipPath: `circle(0px at ${x}px ${y}px)` }, { clipPath: `circle(${radius}px at ${x}px ${y}px)` }], { duration: 420, easing: 'cubic-bezier(.16,1,.3,1)', pseudoElement: '::view-transition-new(root)' }).finished;
      } catch (_) {
        if (transition) transition.skipTransition();
        apply();
      }
      finally {
        themeTransitionBusy = false;
      }
    };
    toggles.forEach(button => button.onclick = () => changeTheme(button));
  }
  function initializeExperience() {
    initializeThemeControls();
    $('replay-intro').onclick = replayIntro;
    $('home-link').onclick = e => {
      e.preventDefault();
      scanner(false);
      replayIntro();
    };
    let done = false;
    try {
      done = sessionStorage.getItem('scamshield-welcome') === 'done';
    } catch (_) {
    }
    $('welcome').hidden = done;
    $('app-shell').inert = !done;
    if (!done) $('welcome-title').focus({ preventScroll: true });
    $('welcome-skip').onclick = finishWelcome;
    $('welcome-go').onclick = () => {
      if (reducedMotion()) {
        finishWelcome();
        return;
      }
      $('welcome-go').disabled = true;
      $('welcome-status').textContent = 'A little room for better decisions.';
      $('welcome-stage').hidden = false;
      $('welcome-stage').classList.add('punching');
      welcomePlayer = playAsset($('welcome-boxer'), 'boxer', () => {
        clearTimeout(welcomeTimer);
        welcomeTimer = setTimeout(finishWelcome, INTRO_FINAL_HOLD_MS);
      });
      if (welcomePlayer) welcomePlayer.addEventListener('enterFrame', event => {
        const contact = event.currentTime >= PUNCH_CONTACT_FRAME;
        $('scam-word').setAttribute('data-hit', String(contact));
      });
      // SVG/CSS fallback and a hard stop keep Skip and landing available if playback fails.
      if (!welcomePlayer) $('welcome-boxer').innerHTML = icon('warning');
      welcomeTimer = setTimeout(finishWelcome, welcomePlayer ? 6500 : 1800);
    };
  }
  function clearResultMotion() {
    if (resultPlayer) {
      resultPlayer.destroy();
      resultPlayer = null;
    }
  }
  function showResultMotion(state) {
    clearResultMotion();
    $('result-motion').replaceChildren();
    $('result-motion').removeAttribute('data-complete');
    $('result-motion').hidden = true;
    // The adjacent verdict supplies the accessible label; colour is an extra cue.
    $('result-icon').innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="1.5" opacity=".3"/><circle cx="12" cy="12" r="6" fill="currentColor"/></svg>';
    $('result-icon').setAttribute('data-status', state);
    if (reducedMotion() || state === 'caution') return;
    $('result-motion').hidden = false;
    resultPlayer = playAsset($('result-motion'), state === 'danger' ? 'boxer' : 'lock', () => {
      // Some supplied lock frames end blank. Keep a permanent final vector state.
      if (state === 'clear') {
        $('result-motion').innerHTML = icon('lock');
        $('result-motion').setAttribute('data-complete', 'true');
      }
    });
    if (!resultPlayer) {
      $('result-motion').innerHTML = icon(state === 'clear' ? 'check' : 'warning');
    }
  }
  window.ScamShieldExperience = Object.freeze({ initialize: initializeExperience, showResultMotion, clearResultMotion });
  initializeExperience();
})();
