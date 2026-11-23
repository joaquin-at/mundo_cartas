const carousel = document.querySelector('[data-news-carousel]');
if (carousel) {
  const slides = [...carousel.querySelectorAll('.news-slide')];
  const dots = [...document.querySelectorAll('[data-carousel-dot]')];
  let activeSlide = 0;
  let pointerStart = null;
  let scrollStart = 0;
  let dragged = false;
  const slideLeft = slide => carousel.scrollLeft + slide.getBoundingClientRect().left - carousel.getBoundingClientRect().left;

  const showSlide = index => {
    activeSlide = (index + slides.length) % slides.length;
    carousel.scrollTo({ left: slideLeft(slides[activeSlide]), behavior: 'smooth' });
    dots.forEach((dot, dotIndex) => {
      const active = dotIndex === activeSlide;
      dot.classList.toggle('active', active);
      dot.setAttribute('aria-pressed', String(active));
    });
  };

  document.querySelector('[data-carousel-prev]')?.addEventListener('click', () => showSlide(activeSlide - 1));
  document.querySelector('[data-carousel-next]')?.addEventListener('click', () => showSlide(activeSlide + 1));
  dots.forEach(dot => dot.addEventListener('click', () => showSlide(Number(dot.dataset.carouselDot))));

  carousel.addEventListener('scroll', () => {
    const center = carousel.clientWidth / 2;
    let nearest = 0;
    slides.forEach((slide, index) => {
      const slideCenter = slide.getBoundingClientRect().left - carousel.getBoundingClientRect().left + slide.clientWidth / 2;
      const nearestCenter = slides[nearest].getBoundingClientRect().left - carousel.getBoundingClientRect().left + slides[nearest].clientWidth / 2;
      if (Math.abs(slideCenter - center) < Math.abs(nearestCenter - center)) nearest = index;
    });
    activeSlide = nearest;
    dots.forEach((dot, index) => {
      const active = index === nearest;
      dot.classList.toggle('active', active);
      dot.setAttribute('aria-pressed', String(active));
    });
  }, { passive: true });

  carousel.addEventListener('keydown', event => {
    if (event.key === 'ArrowRight') { event.preventDefault(); showSlide(activeSlide + 1); }
    if (event.key === 'ArrowLeft') { event.preventDefault(); showSlide(activeSlide - 1); }
  });

  carousel.addEventListener('pointerdown', event => {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    pointerStart = event.clientX;
    scrollStart = carousel.scrollLeft;
    dragged = false;
    carousel.classList.add('is-dragging');
    carousel.setPointerCapture(event.pointerId);
  });
  carousel.addEventListener('pointermove', event => {
    if (pointerStart === null) return;
    const distance = event.clientX - pointerStart;
    if (Math.abs(distance) > 5) dragged = true;
    if (dragged) carousel.scrollLeft = scrollStart - distance;
  });
  const finishDrag = () => {
    if (pointerStart === null) return;
    pointerStart = null;
    carousel.classList.remove('is-dragging');
    if (dragged) showSlide(activeSlide);
    setTimeout(() => { dragged = false; }, 0);
  };
  carousel.addEventListener('pointerup', finishDrag);
  carousel.addEventListener('pointercancel', finishDrag);
  carousel.addEventListener('click', event => {
    if (dragged) { event.preventDefault(); event.stopPropagation(); }
  }, true);
}