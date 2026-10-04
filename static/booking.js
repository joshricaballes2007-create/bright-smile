// Booking is the only page that needs a bigger script. Python pa rin ang nagche-check ng actual schedule.
// Keep references to the calendar, service selector, and form so we can update them.
// selectedDay and selectedSlot remember the choice while moving between booking steps.
// Temporary browser state lang ito; a saved reservation still needs Python and Cal.com.
const shell = document.getElementById('booking-shell');
const service = document.getElementById('booking-service');
const calendar = document.getElementById('calendar-grid');
const slotsBox = document.getElementById('time-slots');
const nextButton = document.getElementById('continue-booking');
const form = document.getElementById('booking-form');
const today = shell.dataset.today;
let month = Number(today.slice(5, 7)) - 1;
let year = Number(today.slice(0, 4));
let selectedDay = '';
let selectedSlot = null;
let slotRequest = null;

// We use Manila time even if the patient is abroad. Para hindi lumipat ang appointment day.
function formatDay(day, options = {month:'long', day:'numeric', year:'numeric'}) {
  return new Intl.DateTimeFormat('en-PH', {...options, timeZone:'Asia/Manila'}).format(new Date(`${day}T12:00:00+08:00`));
}
// Build a date as YYYY-MM-DD with leading zeroes, like 2026-10-05.
// This format matches the text Python expects and keeps date comparisons predictable.
// Consistent format ang gamit para hindi malito sa month/day order.
function isoDay(y, m, d) { return `${y}-${String(m + 1).padStart(2,'0')}-${String(d).padStart(2,'0')}`; }
// Changing the date clears the old time selection and disables Continue.
// A time from yesterday must not remain selected after choosing another day.
// Kailangan ulit pumili ng slot na kabilang sa bagong date.
function resetTime() {
  selectedSlot = null;
  nextButton.disabled = true;
  document.getElementById('selected-summary').textContent = 'Choose a time that suits your day.';
}

// Rebuild the month as button elements, with blank spaces before day one.
// Disable dates outside the booking window and label each button for screen readers.
// Display lang ito; Python checks the date again when the visitor submits a booking.
function renderCalendar() {
  calendar.replaceChildren();
  document.getElementById('calendar-month').textContent = formatDay(isoDay(year, month, 1), {month:'long', year:'numeric'});
  const offset = (new Date(year, month, 1).getDay() + 6) % 7;
  const days = new Date(year, month + 1, 0).getDate();
  const limit = new Date(`${today}T12:00:00+08:00`);
  limit.setUTCDate(limit.getUTCDate() + 90);
  for (let i = 0; i < offset; i++) calendar.append(document.createElement('span'));
  for (let day = 1; day <= days; day++) {
    const value = isoDay(year, month, day);
    const date = new Date(`${value}T12:00:00+08:00`);
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'calendar-day' + (value === today ? ' today' : '');
    button.textContent = String(day);
    button.setAttribute('aria-label', formatDay(value, {weekday:'long', month:'long', day:'numeric'}));
    button.setAttribute('aria-pressed', String(value === selectedDay));
    button.disabled = value < today || date > limit || date.getUTCDay() === 0;
    button.addEventListener('click', () => selectDay(value));
    calendar.append(button);
  }
  // Only show months inside the 90-day window. Hindi puwedeng pumili ng sobrang layo.
  document.getElementById('previous-month').disabled = year === Number(today.slice(0,4)) && month === Number(today.slice(5,7)) - 1;
  const nextMonth = new Date(Date.UTC(year, month + 1, 1));
  document.getElementById('next-month').disabled = nextMonth > limit;
}

// Selecting a day asks Python for the available start times for that service.
// async lets the browser wait for the reply while the page remains usable.
// Habang naghihintay, show a loading message instead of stale buttons from the old date.
async function selectDay(day) {
  selectedDay = day;
  resetTime();
  renderCalendar();
  document.getElementById('selected-date-label').textContent = formatDay(day, {weekday:'short', month:'short', day:'numeric'});
  document.getElementById('slots-feedback').textContent = '';
  slotsBox.replaceChildren();
  slotsBox.textContent = 'Finding times…';
  // Cancel the old request when the date changes. Para hindi ma-show ang times ng lumang date.
  slotRequest?.abort();
  slotRequest = new AbortController();
  try {
    const response = await fetch(`/api/slots?service=${encodeURIComponent(service.value)}&day=${day}`, {signal:slotRequest.signal});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'We could not load times. Please try another date.');
    slotsBox.replaceChildren();
    if (!result.slots.length) {
      const message = document.createElement('p');
      message.className = 'muted';
      message.textContent = 'No times left on this day. Let’s try another date.';
      slotsBox.append(message);
    }
    for (const slot of result.slots) {
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'time-slot';
      button.textContent = slot.label; button.disabled = !slot.available;
      button.setAttribute('aria-pressed', 'false');
      if (!slot.available) button.setAttribute('aria-label', `${slot.label}, unavailable`);
      button.addEventListener('click', () => {
        selectedSlot = slot;
        slotsBox.querySelectorAll('button').forEach(item => item.setAttribute('aria-pressed', String(item === button)));
        nextButton.disabled = false;
        document.getElementById('selected-summary').textContent = `${formatDay(day, {month:'short',day:'numeric'})} · ${slot.label} · Philippine time`;
      });
      slotsBox.append(button);
    }
  } catch (error) {
    if (error.name !== 'AbortError') {
      slotsBox.textContent = '';
      document.getElementById('slots-feedback').textContent = error.message || 'Please check your connection and try again.';
    }
  }
}

// Add or subtract a month, then redraw the calendar buttons.
// JavaScript's Date handles year changes when moving past December or January.
// Para hindi kailangan gumawa ng separate code para sa bawat month.
function changeMonth(amount) {
  const changed = new Date(year, month + amount, 1);
  year = changed.getFullYear(); month = changed.getMonth();
  renderCalendar();
}
document.getElementById('previous-month').addEventListener('click', () => changeMonth(-1));
document.getElementById('next-month').addEventListener('click', () => changeMonth(1));

// Another service may take a different amount of time and use another Cal.com event.
// Return to the calendar and reload slots instead of reusing the previous service's time.
// Halimbawa, a 60-minute filling needs a longer opening than a 30-minute checkup.
service.addEventListener('change', () => {
  document.getElementById('visit-duration').textContent = `${service.selectedOptions[0].dataset.minutes} minutes`;
  document.getElementById('booking-details').hidden = true;
  document.getElementById('booking-result').hidden = true;
  document.getElementById('booking-picker').hidden = false;
  if (selectedDay) selectDay(selectedDay);
});

// Continue moves from choosing a time to entering the patient details.
// Require a selected slot and repeat the chosen service, date, and time in the summary.
// Focus moves to the name field para madaling magpatuloy gamit ang keyboard.
nextButton.addEventListener('click', () => {
  if (!selectedSlot) return;
  document.getElementById('booking-picker').hidden = true;
  document.getElementById('booking-details').hidden = false;
  document.getElementById('details-summary').textContent = `${service.selectedOptions[0].textContent} · ${formatDay(selectedDay)} · ${selectedSlot.label} (Philippine time)`;
  form.elements.name.focus();
});
document.getElementById('back-to-calendar').addEventListener('click', () => {
  document.getElementById('booking-details').hidden = true;
  document.getElementById('booking-picker').hidden = false;
  nextButton.focus();
});

// Send patient details, consent, service, day, and selected start time to Python.
// Disable the button while waiting, then use the server reply to show the result.
// Hindi proof ng booking ang button click; kailangan ng successful provider response.
form.addEventListener('submit', async event => {
  event.preventDefault();
  const button = document.getElementById('confirm-booking');
  const feedback = document.getElementById('booking-feedback');
  button.disabled = true;
  service.disabled = true;
  feedback.textContent = 'Checking your visit…';
  const values = Object.fromEntries(new FormData(form));
  try {
    const response = await fetch('/api/bookings', {method:'POST', headers:{'Content-Type':'application/json', 'X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content}, body:JSON.stringify({...values, consent:form.elements.consent.checked, service:service.value, day:selectedDay, start:selectedSlot.start})});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || 'We could not complete your visit. Please try again.');
    // Separate a practice preview, a confirmed reservation, and a pending booking request.
    // The server also tells us if the reservation is a labeled demo event for presentation.
    // Para tama ang message at hindi mangako ng confirmed visit na wala pa.
    const preview = result.mode === 'preview';
    document.getElementById('result-label').textContent = result.demo ? 'Demo appointment' : preview ? 'A little look ahead' : 'Your next step';
    document.getElementById('result-title').textContent = preview ? 'Your visit preview is ready.' : result.status === 'accepted' ? 'Your appointment is booked.' : 'Your booking request is received.';
    document.getElementById('result-message').textContent = result.demo ? 'Your labeled demo event is saved in Cal.com. This is presentation data and does not reserve dental treatment.' : preview ? 'This is a preview only. No appointment has been reserved, no email has been sent, and your details have not been saved.' : 'Check your email for appointment details and next steps from the clinic.';
    const list = document.getElementById('result-details'); list.replaceChildren();
    // Use textContent, not raw HTML, for form values. Para hindi maging code ang input ng tao.
    const rows = [['Care', result.service], ['Date', formatDay(selectedDay)], ['Time', `${selectedSlot.label} · UTC+8`]];
    if (!preview) rows.push(['Reference', result.uid]);
    for (const [label,value] of rows) { const term = document.createElement('dt'); const detail = document.createElement('dd'); term.textContent = label; detail.textContent = value; list.append(term,detail); }
    document.getElementById('booking-details').hidden = true;
    document.getElementById('booking-result').hidden = false;
    document.getElementById('result-title').setAttribute('tabindex','-1');
    document.getElementById('result-title').focus();
    form.reset();
  } catch (error) {
    // Do not automatically resend bookings. Baka dalawang appointment ang magawa.
    feedback.textContent = error.message || 'Please check your connection and try again.';
  } finally { button.disabled = false; service.disabled = false; }
});

// Return to the calendar and fetch fresh times when starting another visit.
// The time just booked may no longer be available after the reservation succeeds.
// Hindi inuulit ang previous POST; a new visit needs a new date and time selection.
document.getElementById('start-again').addEventListener('click', () => {
  document.getElementById('booking-result').hidden = true;
  document.getElementById('booking-picker').hidden = false;
  document.getElementById('booking-feedback').textContent = '';
  selectDay(selectedDay);
});

// Show the correct duration and first open day. Hindi kailangang manghula ang patient.
document.getElementById('visit-duration').textContent = `${service.selectedOptions[0].dataset.minutes} minutes`;
renderCalendar();
const firstDay = calendar.querySelector('.calendar-day:not(:disabled)');
firstDay?.click();
