// Apply preferences before paint; storage failure must never block the interface.
try {
  const theme = localStorage.getItem('scamshield-theme');
  document.documentElement.dataset.theme = theme === 'dark' || theme === 'light'
    ? theme
    : (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  if (sessionStorage.getItem('scamshield-welcome') === 'done') document.documentElement.dataset.welcome = 'done';
} catch (_) {
}
