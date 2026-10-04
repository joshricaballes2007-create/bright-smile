// This only handles the small menu and contact form. HTML ang gumagawa ng ibang pages.
const menuButton = document.getElementById('menu-button');
const navigation = document.getElementById('main-navigation');
menuButton?.addEventListener('click', () => {
  const open = navigation.classList.toggle('is-open');
  menuButton.setAttribute('aria-expanded', String(open));
  menuButton.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
  menuButton.querySelector('img').src = `/static/icons/${open ? 'x' : 'list'}.svg`;
});

// Escape closes the menu. Madaling bumalik kapag keyboard ang gamit.
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && navigation.classList.contains('is-open')) {
    navigation.classList.remove('is-open');
    menuButton.setAttribute('aria-expanded', 'false');
    menuButton.setAttribute('aria-label', 'Open menu');
    menuButton.querySelector('img').src = '/static/icons/list.svg';
    menuButton.focus();
  }
});

// Send contact details through Python, not straight to Supabase. Nasa server ang private key.
const contactForm = document.getElementById('contact-form');
contactForm?.addEventListener('submit', async event => {
  event.preventDefault();
  const button = contactForm.querySelector('button[type="submit"]');
  const feedback = document.getElementById('contact-feedback');
  button.disabled = true;
  feedback.textContent = 'Sending your message…';
  try {
    const details = Object.fromEntries(new FormData(contactForm));
    const response = await fetch('/api/contact', {method:'POST', headers:{'Content-Type':'application/json','X-CSRF-Token':details.csrf}, body:JSON.stringify(details)});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'Your message could not be sent. Please try again.');
    feedback.textContent = result.message;
    contactForm.reset();
  } catch (error) {
    // Show the truth if the inbox is not connected. Hindi fake success ang ipapakita.
    feedback.textContent = error.message || 'Please check your connection and try again.';
  } finally {
    button.disabled = false;
  }
});
