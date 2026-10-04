// This only handles the small menu and contact form. HTML ang gumagawa ng ibang pages.
// The HTML already contains the menu and form; this script adds their small interactions.
// Opening the menu changes its visible state and the label read by a screen reader.
// Hindi nito hawak ang database keys: Python handles the private Supabase connection.
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
  // Stop the normal page reload so we can show feedback beside the contact form.
  // Disable the button while waiting to reduce accidental double submissions.
  // Pag tapos or may error, the finally block enables the button again.
  event.preventDefault();
  const button = contactForm.querySelector('button[type="submit"]');
  const feedback = document.getElementById('contact-feedback');
  button.disabled = true;
  feedback.textContent = 'Sending your message…';
  try {
    // FormData collects fields by their HTML names, including the hidden CSRF value.
    // JSON turns those details into a text format that Python can read in this POST request.
    // Success appears only after the database save works, hindi pag click pa lang.
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
