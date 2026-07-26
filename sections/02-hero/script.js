export function init(root) {
  const video = root.querySelector('.hero__video');

  if (!video) return;

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    || root.classList.contains('config-motion-disabled');
  let hasPlayed = false;

  function showHero() {
    root.classList.add('is-video-ready', 'is-playing');
  }

  function playOnce() {
    if (hasPlayed || reduceMotion) return;
    hasPlayed = true;
    showHero();

    const playPromise = video.play();
    if (playPromise) {
      playPromise.catch(() => root.classList.add('is-video-ended'));
    }
  }

  video.addEventListener('canplay', playOnce, { once: true });
  video.addEventListener('ended', () => root.classList.add('is-video-ended'), { once: true });

  if (reduceMotion) {
    showHero();
  } else if (video.readyState >= 3) {
    playOnce();
  } else {
    video.load();
  }
}
