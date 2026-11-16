(() => {
  const button = document.querySelector('.site-menu-toggle');
  const content = document.getElementById('site-nav-content');
  if (!button || !content) return;

  const setOpen = open => {
    button.setAttribute('aria-expanded', String(open));
    button.setAttribute('aria-label', open ? 'Cerrar menú principal' : 'Abrir menú principal');
    content.classList.toggle('is-open', open);
  };
  button.addEventListener('click', () => setOpen(button.getAttribute('aria-expanded') !== 'true'));
  content.querySelectorAll('a').forEach(link => link.addEventListener('click', () => setOpen(false)));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && button.getAttribute('aria-expanded') === 'true') {
      setOpen(false);
      button.focus();
    }
  });
  window.matchMedia('(max-width: 1250px)').addEventListener('change', () => setOpen(false));
})();
