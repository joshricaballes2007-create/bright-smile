/* ============ Clinic details (edit these) ============ */
const CLINIC = { name:'Bright Smile Dental Clinic', street:'Rizal Street, San Isidro', dentist:'Dr. A. Reyes', phone:'0900 000 0000' };

/* ============ Helpers ============ */
const $ = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => [...r.querySelectorAll(s)];
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pad = n => String(n).padStart(2,'0');
const iso = d => `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
const parseISO = s => { const [y,m,d] = s.split('-').map(Number); return new Date(y,m-1,d); };
const addDays = (s,n) => { const d = parseISO(s); d.setDate(d.getDate()+n); return iso(d); };
const today = () => iso(new Date());
const nowMin = () => { const d = new Date(); return d.getHours()*60 + d.getMinutes(); };
const toMin = t => { const [h,m] = t.split(':').map(Number); return h*60+m; };
const fromMin = n => `${pad(Math.floor(n/60))}:${pad(n%60)}`;
const fmtTime = t => { if(!t) return 'Walk-in'; const m = toMin(t), h = Math.floor(m/60); return `${((h+11)%12)+1}:${pad(m%60)} ${h<12?'AM':'PM'}`; };
const fmtDate = (s,o={weekday:'short',month:'short',day:'numeric'}) => parseISO(s).toLocaleDateString('en-PH',o);
const DAYS = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
const qLabel = q => q ? 'Q-'+String(q).padStart(3,'0') : '–';
const byTime = (a,b) => (a.time||'99:99').localeCompare(b.time||'99:99');
const stamp = mins => new Date(Date.now()+mins*60000).toISOString();
const LABEL = {pending:'Pending',confirmed:'Confirmed',waiting:'Waiting',serving:'In chair',completed:'Completed',cancelled:'Cancelled','no-show':'No-show'};
const pill = s => `<span class="pill p-${s}">${LABEL[s]||s}</span>`;
const BLOCK = ['pending','confirmed','waiting','serving','completed'];
const validPhone = p => /^(\+?63|0)?9\d{9}$/.test(String(p).replace(/[\s\-()]/g,''));
const pkey = a => { const d = (a.phone||'').replace(/\D/g,'').slice(-10); return d || ('n:'+a.name.trim().toLowerCase()); };

/* ============ Data store ============ */
const KEY = 'bsdc_v1';
let db;
function load(){ try{ const s = localStorage.getItem(KEY); if(s) return JSON.parse(s); }catch(e){} return null; }
function save(){ try{ localStorage.setItem(KEY, JSON.stringify(db)); }catch(e){} }
function svcById(id){ return db.services.find(s => s.id === id); }
function isOpenDay(d){ return !db.settings.closedDays.includes(parseISO(d).getDay()); }
function nextOpen(d){ for(let i=1;i<15;i++){ const x = addDays(d,i); if(isOpenDay(x)) return x; } return d; }
function clinicDay(){ const t = today(); return isOpenDay(t) ? t : nextOpen(t); }

function makeAppt(o){
  const a = { id:'a'+Date.now().toString(36)+Math.random().toString(36).slice(2,6), ref:'BS-'+(++db.counter), status:'pending', source:'online', notes:'', q:null, created:new Date().toISOString(), ...o };
  const s = svcById(a.svcId); if(s){ a.svcName = s.name; a.dur = a.dur || s.min; }
  db.appts.push(a); return a;
}

function seed(){
  let r = 7; const rnd = () => { r = (r*16807) % 2147483647; return r/2147483647; };
  db = { settings:{open:'09:00',close:'17:00',lunchStart:'12:00',lunchEnd:'13:00',closedDays:[0],avgMinutes:30},
    services:[
      {id:'s1',name:'Checkup & consultation',min:30},{id:'s2',name:'Oral prophylaxis (cleaning)',min:30},
      {id:'s3',name:'Dental filling',min:60},{id:'s4',name:'Tooth extraction',min:60},{id:'s5',name:'Follow-up visit',min:30}],
    staff:[{id:'u1',name:'Front Desk',username:'staff',password:'staff123',role:'staff'},{id:'u2',name:'Clinic Administrator',username:'admin',password:'admin123',role:'admin'}],
    patients:[{id:'p1',name:'Angela Ramos',phone:'09175550101',email:'',password:'patient123'}],
    appts:[], counter:1000, stats:{blocked:0} };
  const pool = ['Angela Ramos','Paolo Santos','Liza Bautista','Mark Villanueva','Grace Mendoza','Rico Aquino','Jenny Flores','Carlo Navarro','Trisha Garcia','Noel Castillo'].map((n,i)=>({name:n,phone:'0917555'+pad(i+1)+'01'}));
  const at = (d,min) => { const x = parseISO(d); x.setMinutes(min); return x.toISOString(); };
  for(let i=14;i>=1;i--){
    const d = addDays(today(),-i); if(!isOpenDay(d)) continue;
    const n = 3 + Math.floor(rnd()*4), made = [];
    for(let k=0;k<n;k++){
      const svc = db.services[Math.floor(rnd()*db.services.length)];
      const free = slotList(d,svc.min).filter(s=>s.state==='free'); if(!free.length) continue;
      const t = free[Math.floor(rnd()*free.length)].time, p = pool[Math.floor(rnd()*pool.length)], x = rnd();
      const src = x<.6?'online':x<.85?'phone':'walk-in', y = rnd();
      const a = makeAppt({name:p.name,phone:p.phone,svcId:svc.id,date:d,time:t,source:src,status: y<.08?'cancelled':y<.16?'no-show':'completed'});
      made.push(a);
    }
    made.filter(a=>a.status==='completed').sort(byTime).forEach((a,idx)=>{
      a.q = idx+1; const tm = toMin(a.time), ci = tm-5+Math.floor(rnd()*4), st = ci+6+Math.floor(rnd()*22);
      a.checkedInAt = at(d,ci); a.startedAt = at(d,st); a.doneAt = at(d,st+a.dur-5);
      if(rnd()<.5) a.notes = 'Routine visit. Advised regular brushing and a follow-up in six months.';
    });
  }
  const cd = clinicDay(), P = pool;
  const add = (i,t,svc,status,q,ci) => { const a = makeAppt({name:P[i].name,phone:P[i].phone,svcId:svc,date:cd,time:t,status,source:i%3===0?'phone':'online'});
    if(q){ a.q=q; a.checkedInAt = stamp(ci); if(status==='serving'||status==='completed') a.startedAt = stamp(ci+12); if(status==='completed') a.doneAt = stamp(ci+38); } return a; };
  add(0,'09:00','s1','completed',1,-75); add(1,'09:30','s2','serving',2,-40); add(2,'10:00','s1','waiting',3,-20);
  add(3,'11:00','s3','confirmed'); add(4,'14:00','s2','pending'); add(5,'15:00','s4','confirmed');
  const d1 = nextOpen(cd), d2 = nextOpen(d1);
  makeAppt({name:P[6].name,phone:P[6].phone,svcId:'s1',date:d1,time:'09:30',status:'pending'});
  makeAppt({name:P[7].name,phone:P[7].phone,svcId:'s5',date:d1,time:'10:30',status:'pending'});
  makeAppt({name:P[8].name,phone:P[8].phone,svcId:'s3',date:d2,time:'14:00',status:'confirmed'});
  save(); return db;
}

/* ============ Availability engine (prevents double booking) ============ */
function occupied(date, excludeId){
  return db.appts.filter(a => a.date===date && a.time && BLOCK.includes(a.status) && a.id!==excludeId).map(a => [toMin(a.time), toMin(a.time)+a.dur]);
}
function slotList(date, dur, excludeId){
  if(!isOpenDay(date)) return [];
  const s = db.settings, open = toMin(s.open), close = toMin(s.close), ls = toMin(s.lunchStart), le = toMin(s.lunchEnd);
  const occ = occupied(date, excludeId), isToday = date === today(), out = [];
  for(let t=open; t+30<=close; t+=30){
    if(t>=ls && t<le) continue;
    const end = t+dur; let state = 'free';
    if(end>close || (t<ls && end>ls)) state = 'nofit';
    else if(isToday && t<=nowMin()) state = 'past';
    else if(occ.some(([a,b]) => t<b && end>a)) state = 'taken';
    out.push({time:fromMin(t), state});
  }
  return out;
}
function isFree(date,time,dur,excludeId){ const s = slotList(date,dur,excludeId).find(x=>x.time===time); return !!s && s.state==='free'; }
function nextOpenSlot(){ for(let i=0;i<30;i++){ const d = addDays(today(),i), s = slotList(d,30).find(x=>x.state==='free'); if(s) return {date:d,time:s.time}; } return null; }
function slotButtons(date,dur,excludeId,sel){
  if(!isOpenDay(date)) return '<p class="muted">The clinic is closed on this day. Pick another date.</p>';
  const L = slotList(date,dur,excludeId);
  if(!L.length) return '<p class="muted">No times on this date.</p>';
  const t = {taken:'Already booked',past:'This time has passed',nofit:'Not enough time before lunch or closing'};
  return `<div class="slots">${L.map(s=>`<button type="button" class="slot ${sel===s.time?'sel':''}" data-time="${s.time}" aria-pressed="${sel===s.time}" ${s.state!=='free'?`disabled title="${t[s.state]}"`:''}>${fmtTime(s.time)}</button>`).join('')}</div>`;
}
function queueList(date){ return db.appts.filter(a=>a.date===date && (a.status==='waiting'||a.status==='serving')); }
function waitMinutes(list){ return list.reduce((m,x)=>m+(x.status==='serving'?Math.ceil(x.dur/2):x.dur),0); }
function nextQ(date){ return Math.max(0,...db.appts.filter(a=>a.date===date).map(a=>a.q||0))+1; }

/* ============ UI state ============ */
const ui = { book:null, track:{ref:'',phone:'',res:null,err:''}, tab:'queue', qDate:null, filt:{status:'all',when:'upcoming',q:''}, pat:{q:'',sel:null}, range:14, account:{mode:'login',err:''} };
function resetBook(){ ui.book = { svc:db.services[0].id, date:'', time:'', name:'', phone:'', email:'', note:'', errs:{}, done:null }; }
let session = null;
try{ session = JSON.parse(sessionStorage.getItem('bsdc_session')||'null'); }catch(e){}
function setSession(u){ session = u; try{ sessionStorage.setItem('bsdc_session', JSON.stringify(u)); }catch(e){} }

let patSession = null;
try{ patSession = JSON.parse(sessionStorage.getItem('bsdc_psession')||'null'); }catch(e){}
function setPatSession(u){ patSession = u; try{ sessionStorage.setItem('bsdc_psession', JSON.stringify(u)); }catch(e){} }
function findPatientByPhone(phone){ const d = (phone||'').replace(/\D/g,'').slice(-10); return d ? db.patients.find(p => p.phone.replace(/\D/g,'').slice(-10)===d) : null; }
function myAppts(){ if(!patSession) return []; const dkey = pkey({name:patSession.name,phone:patSession.phone}); return db.appts.filter(a => a.patientId===patSession.id || pkey(a)===dkey); }

/* ============ Feedback ============ */
let toastT;
function toast(m){ const t = $('#toast'); t.textContent = m; t.classList.add('show'); clearTimeout(toastT); toastT = setTimeout(()=>t.classList.remove('show'),2800); }
const dlg = $('#dlg');
function openModal(html,mount){ dlg.innerHTML = html; if(!dlg.open) dlg.showModal(); mount && mount(dlg); }
function closeModal(){ if(dlg.open) dlg.close(); }
function confirmBox(title,msg,ok,cb,back='Go back'){
  openModal(`<form method="dialog" class="dlg-body"><h3>${title}</h3><p>${msg}</p><div class="dlg-actions"><button class="btn ghost" value="no">${back}</button><button class="btn danger" id="dlgOk" value="ok">${ok}</button></div></form>`, d => $('#dlgOk',d).addEventListener('click',()=>cb()));
}

/* ============ Views: public ============ */
function vHome(){
  const cd = clinicDay(), L = db.appts.filter(a=>a.date===cd), serving = L.find(a=>a.status==='serving');
  const q = queueList(cd), nx = nextOpenSlot();
  const nxTxt = nx ? `${nx.date===today()?'Today':fmtDate(nx.date)}, ${fmtTime(nx.time)}` : 'None soon';
  const strip = slotList(cd,30).map(s=>`<span class="chip ${s.state==='free'?'free':'busy'}">${fmtTime(s.time).replace(' ','\u00a0')}</span>`).join('');
  const s = db.settings, closed = s.closedDays.map(d=>DAYS[d]).join(', ');
  return `
  <section class="hero"><div class="wrap">
    <div>
      <h1>Book your dental visit online. Skip the phone call and the long wait.</h1>
      <p class="lead">See when the dentist is free, pick a time that suits you, and follow your place in line from your phone. No more double-booked slots at ${esc(CLINIC.name)}.</p>
      <div class="actions"><a class="btn" href="#/book">Book an appointment</a><a class="btn ghost" href="#/track">Track my visit</a></div>
    </div>
    <aside class="ticket" aria-label="Live clinic status">
      <div class="top-row"><span>Clinic day: ${cd===today()?'Today':fmtDate(cd)}</span><span>Live</span></div>
      <div class="muted" style="margin-top:14px">Now serving</div>
      <div class="serving">${serving?qLabel(serving.q):'–'}</div>
      <div class="perf"></div>
      <dl>
        <dt>Patients in queue</dt><dd>${q.length}</dd>
        <dt>Estimated wait if you arrive now</dt><dd>${waitMinutes(q)} min</dd>
        <dt>Next open slot</dt><dd>${nxTxt}</dd>
      </dl>
      <div class="strip" aria-label="Times on this clinic day">${strip}</div>
      <p class="muted" style="font-size:.8rem;margin:10px 0 0">Shaded times are open. Crossed-out times are taken or have passed.</p>
    </aside>
  </div></section>

  <section class="block"><div class="wrap">
    <h2>How booking works</h2>
    <ol class="steps plain" style="padding:0">
      <li><h3>Pick a service and time</h3><p>Only times that are really free are shown, so two patients can never hold the same slot.</p></li>
      <li><h3>Get your reference code</h3><p>Enter your name and mobile number. The clinic staff confirms your booking.</p></li>
      <li><h3>Arrive and check in</h3><p>Staff check you in and give you a queue number for the day.</p></li>
      <li><h3>Watch your place in line</h3><p>See how many patients are ahead of you and your estimated wait.</p></li>
    </ol>
  </div></section>

  <section class="block"><div class="wrap two">
    <div><h2>Services</h2><p class="muted">Checkups, cleanings and minor procedures with one licensed dentist, ${esc(CLINIC.dentist)}.</p></div>
    <ul class="plain svc-list">${db.services.map(v=>`<li><b>${esc(v.name)}</b><span class="muted">${v.min} min</span></li>`).join('')}</ul>
  </div></section>

  <section class="block"><div class="wrap">
    <h2>Made for everyone at the clinic</h2>
    <div class="roles">
      <div><h3>Patients</h3><p>Check dentist availability, book online, and follow your queue position. No account needed.</p><a class="btn sm ghost" href="#/book">Book now</a></div>
      <div><h3>Clinic staff</h3><p>Confirm, reschedule or cancel bookings, check patients in, run the queue, add walk-ins and look up visit history.</p><a class="btn sm ghost" href="#/staff">Staff sign in</a></div>
      <div><h3>Administrator</h3><p>Everything staff can do, plus reports, clinic hours, services and staff accounts.</p><a class="btn sm ghost" href="#/staff">Admin sign in</a></div>
    </div>
  </div></section>

  <section class="block"><div class="wrap two">
    <div><h2>Visit us</h2></div>
    <div>
      <p><b>${esc(CLINIC.name)}</b><br>${esc(CLINIC.street)}</p>
      <p><b>Hours</b><br>${fmtTime(s.open)} to ${fmtTime(s.close)}, closed ${fmtTime(s.lunchStart)} to ${fmtTime(s.lunchEnd)} for lunch.<br>Closed on ${esc(closed||'no days')}.</p>
      <p><b>Phone</b><br>${esc(CLINIC.phone)}</p>
      <p class="muted">Walk-ins are welcome. Staff add you to the same digital queue so scheduled patients keep their place.</p>
    </div>
  </div></section>`;
}

function vBook(){
  const b = ui.book; if(b.done) return vDone(b.done);
  if(patSession && !b.name){ b.name = patSession.name; b.phone = patSession.phone; b.email = patSession.email||''; }
  const svc = svcById(b.svc) || db.services[0], e = b.errs;
  const dates = Array.from({length:28},(_,i)=>addDays(today(),i));
  const chips = dates.map(d=>{ const n = slotList(d,svc.min).filter(s=>s.state==='free').length;
    return `<button type="button" class="dchip ${b.date===d?'sel':''}" data-act="pickDate" data-date="${d}" ${n?'':'disabled'} aria-pressed="${b.date===d}"><b>${fmtDate(d,{weekday:'short'})}</b><span>${fmtDate(d,{month:'short',day:'numeric'})}</span><em>${isOpenDay(d)?(n?n+' open':'Full'):'Closed'}</em></button>`; }).join('');
  return `<div class="page"><div class="wrap">
    <h1 style="font-size:clamp(2rem,5vw,2.8rem)">Book an appointment</h1>
    <p class="muted" style="max-width:40em">Choose a service, date and time. Times that are already booked are disabled, so your slot is yours as soon as you book.</p>
    <div class="grid-book" style="margin-top:26px">
      <div class="panel">
        <fieldset><legend>1. Service</legend>
          <div class="svc-pick">${db.services.map(v=>`<label class="opt"><input type="radio" name="svc" value="${v.id}" data-act="pickSvc" ${b.svc===v.id?'checked':''}><span>${esc(v.name)}<small>${v.min} minutes</small></span></label>`).join('')}</div>
        </fieldset>
        <fieldset id="f-date"><legend>2. Date</legend><div class="dates" role="group" aria-label="Dates">${chips}</div>${e.date?`<p class="err">${e.date}</p>`:''}</fieldset>
        <fieldset id="f-time"><legend>3. Time ${b.date?`<span class="muted" style="font:500 .95rem var(--body)">on ${fmtDate(b.date,{weekday:'long',month:'long',day:'numeric'})}</span>`:''}</legend>
          <div id="slotBox">${b.date?slotButtons(b.date,svc.min,null,b.time):'<p class="muted">Pick a date to see open times.</p>'}</div>${e.time?`<p class="err">${e.time}</p>`:''}
        </fieldset>
        <fieldset><legend>4. Your details</legend>
          ${patSession?`<p class="muted" style="margin-top:-6px">Signed in as ${esc(patSession.name)}. This booking will be saved to <a href="#/account">My account</a>.</p>`:''}
          <div class="row2">
            <label class="${e.name?'field-err':''}">Full name<input data-bind="name" autocomplete="name" value="${esc(b.name)}" placeholder="Juan Dela Cruz">${e.name?`<p class="err">${e.name}</p>`:''}</label>
            <label class="${e.phone?'field-err':''}">Mobile number<input data-bind="phone" type="tel" inputmode="tel" autocomplete="tel" value="${esc(b.phone)}" placeholder="0917 123 4567">${e.phone?`<p class="err">${e.phone}</p>`:''}</label>
          </div>
          <label>Email <span class="hint">(optional)</span><input data-bind="email" type="email" autocomplete="email" value="${esc(b.email)}"></label>
          <label>Reason for visit <span class="hint">(optional)</span><textarea data-bind="note" placeholder="For example: toothache on the lower left side">${esc(b.note)}</textarea></label>
        </fieldset>
      </div>
      <aside class="panel sum stick" aria-label="Booking summary">
        <h3>Your booking</h3>
        <dl><dt>Service</dt><dd>${esc(svc.name)}</dd><dt>Dentist</dt><dd>${esc(CLINIC.dentist)}</dd><dt>Date</dt><dd>${b.date?fmtDate(b.date):'Not chosen'}</dd><dt>Time</dt><dd>${b.time?fmtTime(b.time):'Not chosen'}</dd><dt>Length</dt><dd>${svc.min} min</dd></dl>
        <button class="btn" style="width:100%" data-act="submitBook">Book appointment</button>
        <p class="muted" style="font-size:.85rem;margin:12px 0 0">The clinic confirms your booking. Keep your reference code to track it or cancel.</p>
      </aside>
    </div></div></div>`;
}
function vDone(a){
  return `<div class="page"><div class="wrap" style="max-width:640px">
    <div class="ticket" style="text-align:center">
      <p class="muted" style="margin:0">Booking received</p>
      <div class="refbig">${a.ref}</div>
      <p class="muted">Save this code and the mobile number you used.</p>
      <div class="perf"></div>
      <dl style="text-align:left"><dt>Patient</dt><dd>${esc(a.name)}</dd><dt>Service</dt><dd>${esc(a.svcName)}</dd><dt>Date</dt><dd>${fmtDate(a.date,{weekday:'long',month:'long',day:'numeric'})}</dd><dt>Time</dt><dd>${fmtTime(a.time)}</dd><dt>Status</dt><dd>${pill(a.status)}</dd></dl>
    </div>
    <p class="muted" style="margin-top:18px">Clinic staff will confirm your booking. Please arrive 10 minutes early and check in at the front desk to get your queue number.</p>
    <div style="display:flex;gap:10px;flex-wrap:wrap">${patSession?'<a class="btn" href="#/account">View my bookings</a>':`<a class="btn" href="#/track" data-act="goTrack" data-ref="${a.ref}" data-phone="${esc(a.phone)}">Track this booking</a>`}<button class="btn ghost" data-act="bookAgain">Book another</button></div>
  </div></div>`;
}

function vTrack(){
  const t = ui.track, a = t.res;
  let res = '';
  if(a){
    const st = a.status, steps = [['Booked',true],['Confirmed',['confirmed','waiting','serving','completed'].includes(st)],['In queue',['waiting','serving','completed'].includes(st)],['Seen',st==='completed']];
    const dead = st==='cancelled'||st==='no-show';
    let live = '';
    if(st==='waiting'){ const ah = queueList(a.date).filter(x=>x.q<a.q); live = `<div class="two" style="grid-template-columns:1fr 1fr;gap:16px;margin:8px 0 18px"><div><div class="muted">Your queue number</div><div class="bignum">${qLabel(a.q)}</div></div><div><div class="muted">Patients ahead of you</div><div class="bignum">${ah.length}</div><div class="muted">About ${waitMinutes(ah)} min wait</div></div></div>`; }
    else if(st==='serving') live = `<p><b>You are being seen now.</b> Queue number ${qLabel(a.q)}.</p>`;
    else if(st==='pending') live = `<p>Waiting for the clinic to confirm your booking.</p>`;
    else if(st==='confirmed') live = `<p>Confirmed. Arrive 10 minutes early and tell the front desk your reference code to get your queue number.</p>`;
    else if(st==='completed') live = `<p>Visit completed. Thank you for visiting ${esc(CLINIC.name)}.</p>`;
    else if(st==='cancelled') live = `<p>This booking was cancelled. You can <a href="#/book">book a new time</a>.</p>`;
    else live = `<p>This visit was marked as a no-show. You can <a href="#/book">book a new time</a>.</p>`;
    res = `<div class="panel" style="margin-top:24px"><div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap;align-items:center"><h3 style="margin:0">${a.ref} · ${esc(a.name)}</h3>${pill(st)}</div>
      <p class="muted">${esc(a.svcName)} with ${esc(CLINIC.dentist)} on ${fmtDate(a.date,{weekday:'long',month:'long',day:'numeric'})}, ${fmtTime(a.time)}</p>
      ${dead?'':`<div class="timeline" aria-label="Progress">${steps.map(([n,on])=>`<div class="${on?'on':''}">${n}</div>`).join('')}</div>`}
      ${live}
      ${['pending','confirmed'].includes(st)?`<button class="btn ghost danger" style="color:var(--rose)" data-act="cancelMine" data-id="${a.id}">Cancel this booking</button>`:''}</div>`;
  }
  return `<div class="page"><div class="wrap" style="max-width:640px">
    <h1 style="font-size:clamp(2rem,5vw,2.8rem)">Track my visit</h1>
    <p class="muted">Enter the reference code from your booking and the mobile number you used.</p>
    <form data-form="lookup" class="panel" novalidate>
      <div class="row2"><label>Reference code<input name="ref" value="${esc(t.ref)}" placeholder="BS-1042" autocapitalize="characters" required></label>
      <label>Mobile number<input name="phone" type="tel" value="${esc(t.phone)}" placeholder="0917 123 4567" required></label></div>
      ${t.err?`<p class="err" role="alert">${t.err}</p>`:''}
      <button class="btn">Find my booking</button>
    </form>${res}</div></div>`;
}

function acctCard(a){
  const cancellable = a.status==='pending'||a.status==='confirmed';
  return `<div class="visit"><div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;align-items:center"><b>${esc(a.svcName)}</b>${pill(a.status)}</div>
    <div class="muted">${a.ref} · ${fmtDate(a.date,{weekday:'long',month:'long',day:'numeric'})} · ${fmtTime(a.time)}${a.q?` · ${qLabel(a.q)}`:''}</div>
    ${cancellable?`<button class="btn sm ghost" style="margin-top:8px;color:var(--rose)" data-act="cancelMine" data-id="${a.id}">Cancel</button>`:''}</div>`;
}
function vAccount(){
  if(!patSession){
    const m = ui.account.mode, err = ui.account.err;
    return `<div class="page"><div class="wrap" style="max-width:460px">
      <h1 style="font-size:clamp(2rem,5vw,2.6rem)">My account</h1>
      <p class="muted">Sign in to see your bookings, or create an account so your details are ready next time you book.</p>
      <div class="tabs" role="tablist" style="margin-top:18px">
        <button role="tab" aria-selected="${m==='login'}" data-act="acctMode" data-mode="login">Sign in</button>
        <button role="tab" aria-selected="${m==='signup'}" data-act="acctMode" data-mode="signup">Create account</button>
      </div>
      ${m==='login'?`
      <form data-form="acctLogin" class="panel" novalidate>
        <label>Mobile number<input name="phone" type="tel" placeholder="0917 123 4567" required></label>
        <label>Password<input name="p" type="password" autocomplete="current-password" required></label>
        ${err?`<p class="err" role="alert">${err}</p>`:''}
        <button class="btn" style="width:100%">Sign in</button>
      </form>
      <p class="muted" style="font-size:.9rem;margin-top:12px">Prototype account: <b>0917 555 0101</b> / <b>patient123</b>.</p>`:`
      <form data-form="acctSignup" class="panel" novalidate>
        <label>Full name<input name="name" autocomplete="name" required></label>
        <label>Mobile number<input name="phone" type="tel" placeholder="0917 123 4567" required></label>
        <label>Email <span class="hint">(optional)</span><input name="email" type="email" autocomplete="email"></label>
        <label>Password <span class="hint">(at least 6 characters)</span><input name="p" type="password" minlength="6" autocomplete="new-password" required></label>
        ${err?`<p class="err" role="alert">${err}</p>`:''}
        <button class="btn" style="width:100%">Create account</button>
      </form>`}
    </div></div>`;
  }
  const L = myAppts();
  const upcoming = L.filter(a=>['pending','confirmed','waiting','serving'].includes(a.status)).sort((a,b)=>a.date.localeCompare(b.date)||byTime(a,b));
  const pastIds = new Set(upcoming.map(a=>a.id));
  const past = L.filter(a=>!pastIds.has(a.id)).sort((a,b)=>b.date.localeCompare(a.date)||byTime(b,a));
  return `<div class="page"><div class="wrap" style="max-width:640px">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">
      <div><h1 style="font-size:clamp(1.8rem,4vw,2.4rem);margin:0">My account</h1><p class="muted" style="margin:4px 0 0">Signed in as ${esc(patSession.name)} · ${esc(patSession.phone)}</p></div>
      <button class="btn ghost sm" data-act="acctLogout">Sign out</button>
    </div>
    <div class="panel" style="margin-top:20px"><div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap"><h3 style="margin:0">Upcoming</h3><a class="btn sm" href="#/book">Book new</a></div>
      ${upcoming.length?upcoming.map(acctCard).join(''):'<p class="empty">No upcoming appointments.</p>'}</div>
    <div class="panel" style="margin-top:20px"><h3>Past visits</h3>${past.length?past.map(acctCard).join(''):'<p class="empty">No past visits yet.</p>'}</div>
  </div></div>`;
}

/* ============ Views: staff & admin ============ */
function vStaff(){
  if(!session) return `<div class="page"><div class="wrap" style="max-width:460px">
    <h1 style="font-size:clamp(2rem,5vw,2.6rem)">Staff &amp; admin sign in</h1>
    <form data-form="login" class="panel"><label>Username<input name="u" autocomplete="username" required></label><label>Password<input name="p" type="password" autocomplete="current-password" required></label>
    <p class="err" id="loginErr" role="alert"></p><button class="btn" style="width:100%">Sign in</button></form>
    <p class="muted" style="margin-top:14px;font-size:.9rem">Prototype sign-in for the case study. Try <b>staff</b> / <b>staff123</b> or <b>admin</b> / <b>admin123</b>.</p></div></div>`;
  const admin = session.role==='admin';
  const tabs = [['queue','Queue'],['appts','Appointments'],['patients','Patient records']].concat(admin?[['reports','Reports'],['settings','Settings']]:[]);
  if(!tabs.find(t=>t[0]===ui.tab)) ui.tab = 'queue';
  const body = {queue:vQueue,appts:vAppts,patients:vPatients,reports:vReports,settings:vSettings}[ui.tab]();
  return `<div class="page"><div class="wrap">
    <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap">
      <div><h1 style="font-size:clamp(1.8rem,4vw,2.4rem);margin:0">${admin?'Admin dashboard':'Staff dashboard'}</h1><p class="muted" style="margin:4px 0 0">Signed in as ${esc(session.name)}</p></div>
      <button class="btn ghost sm" data-act="logout">Sign out</button></div>
    <div class="tabs" role="tablist">${tabs.map(([k,l])=>`<button role="tab" aria-selected="${ui.tab===k}" data-act="tab" data-tab="${k}">${l}</button>`).join('')}</div>
    ${body}</div></div>`;
}

function qRow(a,acts,now){
  return `<div class="qrow ${now?'now':''}"><div class="qn ${a.q?'':'t'}">${a.q?qLabel(a.q):fmtTime(a.time)}</div>
    <div><b>${esc(a.name)}</b> ${pill(a.status)}<small>${esc(a.svcName)} · ${a.time?fmtTime(a.time):'Walk-in'}${a.source==='walk-in'?' · walk-in':''} · ${a.ref}</small></div><div class="acts">${acts}</div></div>`;
}
function vQueue(){
  const d = ui.qDate || clinicDay(), L = db.appts.filter(a=>a.date===d);
  const serving = L.filter(a=>a.status==='serving'), waiting = L.filter(a=>a.status==='waiting').sort((a,b)=>a.q-b.q);
  const expected = L.filter(a=>a.status==='pending'||a.status==='confirmed').sort(byTime);
  const done = L.filter(a=>a.status==='completed'||a.status==='no-show').sort((a,b)=>(a.q||99)-(b.q||99)||byTime(a,b));
  const open = isOpenDay(d);
  return `
  <div class="note">Prototype with sample data. Changes are saved in this browser only.</div>
  <div class="dnav"><h2>${d===today()?'Today, ':''}${fmtDate(d,{weekday:'long',month:'long',day:'numeric'})}</h2>
    <button class="btn ghost sm" data-act="qShift" data-n="-1" aria-label="Previous day">‹ Prev</button><button class="btn ghost sm" data-act="qShift" data-n="1" aria-label="Next day">Next ›</button>${d!==clinicDay()?'<button class="btn ghost sm" data-act="qToday">Back to today</button>':''}</div>
  ${open?'':'<p class="muted">The clinic is closed on this day.</p>'}
  <div class="statbar"><div><b>${serving.length}</b><span>In the chair</span></div><div><b>${waiting.length}</b><span>Waiting (about ${waitMinutes([...serving,...waiting])} min)</span></div><div><b>${expected.length}</b><span>Expected, not checked in</span></div><div><b>${done.filter(a=>a.status==='completed').length}</b><span>Completed</span></div></div>
  <div class="cols">
    <div class="panel"><div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:6px"><h3 style="margin:0">Queue</h3>
      <button class="btn sm" data-act="callNext" ${waiting.length&&!serving.length?'':'disabled'}>Call next patient</button></div>
      ${serving.map(a=>qRow(a,`<button class="btn sm" data-act="finish" data-id="${a.id}">Finish visit</button>`,true)).join('')}
      ${waiting.map(a=>qRow(a,`<button class="btn sm ghost" data-act="callin" data-id="${a.id}" ${serving.length?'disabled title="Finish the current visit first"':''}>Call in</button><button class="btn sm ghost" data-act="noshow" data-id="${a.id}">No-show</button>`)).join('')}
      ${serving.length+waiting.length?'':'<p class="empty">Nobody in the queue. Check in an expected patient or add a walk-in.</p>'}
    </div>
    <div>
      <div class="panel" style="margin-bottom:24px"><h3>Expected today</h3>
        ${expected.map(a=>qRow(a,`<button class="btn sm" data-act="checkin" data-id="${a.id}">Check in</button><button class="btn sm ghost" data-act="noshow" data-id="${a.id}">No-show</button>`)).join('')||'<p class="empty">No more bookings for this day.</p>'}</div>
      <form class="panel" data-form="walkin"><h3>Add walk-in patient</h3>
        <label>Full name<input name="name" required></label>
        <div class="row2"><label>Mobile <span class="hint">(optional)</span><input name="phone" type="tel"></label>
        <label>Service<select name="svc">${db.services.map(v=>`<option value="${v.id}">${esc(v.name)}</option>`).join('')}</select></label></div>
        <button class="btn" style="width:100%" ${open?'':'disabled'}>Add to queue</button>
        <p class="muted" style="font-size:.85rem;margin:10px 0 0">Walk-ins take the next free time slot when one exists, so they never overlap a booked patient.</p></form>
    </div>
  </div>
  ${done.length?`<div class="panel" style="margin-top:24px"><h3>Finished</h3>${done.map(a=>qRow(a,'')).join('')}</div>`:''}`;
}

function apptRows(){
  const f = ui.filt, t = today(), q = f.q.trim().toLowerCase();
  let L = db.appts.filter(a=>{
    if(f.status!=='all' && a.status!==f.status) return false;
    if(f.when==='today' && a.date!==t) return false;
    if(f.when==='upcoming' && a.date<t) return false;
    if(f.when==='past' && a.date>=t) return false;
    if(q && !(a.name.toLowerCase().includes(q)||a.ref.toLowerCase().includes(q)||(a.phone||'').replace(/\D/g,'').includes(q.replace(/\D/g,'')||'§'))) return false;
    return true; });
  L.sort((a,b)=> f.when==='past' ? b.date.localeCompare(a.date)||byTime(b,a) : a.date.localeCompare(b.date)||byTime(a,b));
  if(!L.length) return '<tr><td colspan="7" class="empty">No appointments match these filters.</td></tr>';
  return L.slice(0,150).map(a=>{
    const canEdit = a.status==='pending'||a.status==='confirmed';
    return `<tr><td><b>${a.ref}</b></td><td>${esc(a.name)}<br><small class="muted">${esc(a.phone||'No number')}</small></td><td>${esc(a.svcName)}</td><td>${fmtDate(a.date)}<br><small class="muted">${fmtTime(a.time)}</small></td><td>${a.source}</td><td>${pill(a.status)}</td>
      <td style="white-space:nowrap">${a.status==='pending'?`<button class="btn sm" data-act="confirmAppt" data-id="${a.id}">Confirm</button> `:''}${canEdit?`<button class="btn sm ghost" data-act="resched" data-id="${a.id}">Reschedule</button> <button class="btn sm ghost" style="color:var(--rose)" data-act="cancelAppt" data-id="${a.id}">Cancel</button>`:''}</td></tr>`; }).join('');
}
function vAppts(){
  const f = ui.filt;
  return `<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px"><h2 style="margin:0">Appointments</h2><button class="btn" data-act="newBooking">New phone booking</button></div>
  <div class="filters">
    <label>Search<input data-live="filtQ" value="${esc(f.q)}" placeholder="Name, phone or BS-1001"></label>
    <label>When<select data-live="filtWhen">${[['upcoming','Today and upcoming'],['today','Today only'],['past','Past'],['all','All']].map(([v,l])=>`<option value="${v}" ${f.when===v?'selected':''}>${l}</option>`).join('')}</select></label>
    <label>Status<select data-live="filtStatus"><option value="all">All statuses</option>${Object.keys(LABEL).map(s=>`<option value="${s}" ${f.status===s?'selected':''}>${LABEL[s]}</option>`).join('')}</select></label></div>
  <div class="tscroll"><table><thead><tr><th>Ref</th><th>Patient</th><th>Service</th><th>Date &amp; time</th><th>Source</th><th>Status</th><th>Actions</th></tr></thead><tbody id="apptRows">${apptRows()}</tbody></table></div>`;
}

function patientMap(){
  const m = {};
  db.appts.forEach(a=>{ const k = pkey(a); (m[k] = m[k] || {key:k,name:a.name,phone:a.phone,visits:[]}).visits.push(a); m[k].name = a.name; });
  return Object.values(m);
}
function patList(){
  const q = ui.pat.q.trim().toLowerCase(), dq = q.replace(/\D/g,'');
  const P = patientMap().filter(p=>!q||p.name.toLowerCase().includes(q)||(dq&&(p.phone||'').replace(/\D/g,'').includes(dq))).sort((a,b)=>a.name.localeCompare(b.name));
  if(!P.length) return '<p class="empty">No patients found.</p>';
  return P.map(p=>{ const done = p.visits.filter(v=>v.status==='completed').length; return `<button data-act="selPat" data-key="${esc(p.key)}" aria-current="${ui.pat.sel===p.key}"><b>${esc(p.name)}</b><br><small class="muted">${esc(p.phone||'No number')} · ${done} completed visit${done===1?'':'s'}</small></button>`; }).join('');
}
function patDetail(){
  const p = patientMap().find(x=>x.key===ui.pat.sel);
  if(!p) return '<p class="empty">Select a patient to see their visit history.</p>';
  const V = p.visits.slice().sort((a,b)=>b.date.localeCompare(a.date)||byTime(b,a));
  return `<h3>${esc(p.name)}</h3><p class="muted">${esc(p.phone||'No number')} · ${V.length} record${V.length===1?'':'s'}</p>`+V.map(v=>`<div class="visit"><div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap"><b>${fmtDate(v.date,{month:'short',day:'numeric',year:'numeric'})}, ${fmtTime(v.time)}</b>${pill(v.status)}</div><div class="muted">${esc(v.svcName)} · ${v.ref}</div>
    <label style="margin:8px 0 0">Visit notes<textarea id="note-${v.id}" placeholder="Add treatment notes">${esc(v.notes||'')}</textarea></label><button class="btn sm ghost" style="margin-top:6px" data-act="saveNote" data-id="${v.id}">Save note</button></div>`).join('');
}
function vPatients(){
  return `<h2>Patient records</h2><div class="cols" style="grid-template-columns:.7fr 1.3fr">
    <div class="panel"><label>Search<input data-live="patQ" value="${esc(ui.pat.q)}" placeholder="Name or phone"></label><div class="plist" id="patList">${patList()}</div></div>
    <div class="panel" id="patDetail">${patDetail()}</div></div>`;
}

function vReports(){
  const end = today(), start = addDays(end,-(ui.range-1));
  const L = db.appts.filter(a=>a.date>=start&&a.date<=end), live = L.filter(a=>a.status!=='cancelled');
  const cnt = k => L.filter(a=>a.status===k).length;
  const waits = L.filter(a=>a.checkedInAt&&a.startedAt).map(a=>(new Date(a.startedAt)-new Date(a.checkedInAt))/60000);
  const avg = waits.length ? Math.round(waits.reduce((x,y)=>x+y,0)/waits.length) : 0;
  const days = Array.from({length:ui.range},(_,i)=>addDays(start,i)), per = days.map(d=>live.filter(a=>a.date===d).length), mx = Math.max(1,...per);
  const grp = fn => { const m = {}; live.forEach(a=>{ const k = fn(a); m[k] = (m[k]||0)+1; }); return Object.entries(m).sort((a,b)=>b[1]-a[1]); };
  const hb = arr => { const m = Math.max(1,...arr.map(x=>x[1])); return arr.map(([k,v])=>`<div class="hbar"><span>${esc(k)}</span><i style="width:${v/m*100}%"></i><b>${v}</b></div>`).join('') || '<p class="empty">No data in this range.</p>'; };
  const noShowRate = L.length ? Math.round(cnt('no-show')/L.length*100) : 0;
  return `<div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px"><h2 style="margin:0">Reports</h2>
    <div><button class="btn sm ${ui.range===7?'':'ghost'}" data-act="range" data-n="7">7 days</button> <button class="btn sm ${ui.range===14?'':'ghost'}" data-act="range" data-n="14">14 days</button> <button class="btn sm ${ui.range===30?'':'ghost'}" data-act="range" data-n="30">30 days</button> <button class="btn sm ghost" data-act="print">Print</button></div></div>
  <p class="muted">${fmtDate(start,{month:'short',day:'numeric'})} to ${fmtDate(end,{month:'short',day:'numeric',year:'numeric'})}</p>
  <div class="kpis"><div><b>${L.length}</b><span>Appointments</span></div><div><b>${cnt('completed')}</b><span>Completed</span></div><div><b>${cnt('cancelled')}</b><span>Cancelled</span></div><div><b>${noShowRate}%</b><span>No-show rate</span></div><div><b>${avg} min</b><span>Average wait</span></div><div><b>${db.stats.blocked}</b><span>Double-bookings blocked</span></div></div>
  <div class="panel" style="margin-bottom:24px"><h3>Appointments per day</h3><div class="bars" role="img" aria-label="Bar chart of appointments per day">${per.map((v,i)=>`<div style="height:${v/mx*100}%" title="${fmtDate(days[i])}: ${v}"></div>`).join('')}</div>
    <div class="barlab">${days.map((d,i)=>`<span>${ui.range<=14||i%3===0?parseISO(d).getDate():''}</span>`).join('')}</div></div>
  <div class="cols" style="grid-template-columns:1fr 1fr"><div class="panel"><h3>By service</h3>${hb(grp(a=>a.svcName))}</div>
    <div class="panel"><h3>Busiest start times</h3>${hb(grp(a=>a.time?fmtTime(a.time.slice(0,2)+':00'):'Walk-in').sort((a,b)=>{ const h = s=>{ if(s==='Walk-in') return 99; const [n,ap]=s.split(' '); return parseInt(n)%12+(ap==='PM'?12:0); }; return h(a[0])-h(b[0]); }))}<h3 style="margin-top:20px">By source</h3>${hb(grp(a=>a.source))}</div></div>`;
}

function vSettings(){
  const s = db.settings;
  return `<h2>Clinic settings</h2><div class="cols" style="grid-template-columns:1fr 1fr">
  <form class="panel" data-form="settings"><h3>Hours and queue</h3>
    <div class="row2"><label>Opens<input type="time" name="open" value="${s.open}" required></label><label>Closes<input type="time" name="close" value="${s.close}" required></label>
    <label>Lunch starts<input type="time" name="ls" value="${s.lunchStart}" required></label><label>Lunch ends<input type="time" name="le" value="${s.lunchEnd}" required></label></div>
    <label>Closed on</label><div class="days">${DAYS.map((n,i)=>`<label><input type="checkbox" name="cd" value="${i}" ${s.closedDays.includes(i)?'checked':''}>${n.slice(0,3)}</label>`).join('')}</div>
    <label>Average minutes per visit <span class="hint">(used for wait estimates)</span><input type="number" name="avg" min="5" max="120" value="${s.avgMinutes}"></label>
    <button class="btn">Save settings</button></form>
  <div>
    <div class="panel" style="margin-bottom:24px"><h3>Services</h3>${db.services.map(v=>`<div class="qrow" style="grid-template-columns:1fr auto"><div><b>${esc(v.name)}</b><small>${v.min} minutes</small></div><button class="btn sm ghost" data-act="delSvc" data-id="${v.id}" ${db.services.length<2?'disabled':''}>Remove</button></div>`).join('')}
      <form data-form="addSvc" class="row2" style="margin-top:12px;align-items:end"><label>New service<input name="name" required></label><label>Length<select name="min"><option value="30">30 min</option><option value="60">60 min</option><option value="90">90 min</option></select></label><button class="btn sm" style="grid-column:1/-1;justify-self:start">Add service</button></form></div>
    <div class="panel"><h3>Staff accounts</h3>${db.staff.map(u=>`<div class="qrow" style="grid-template-columns:1fr auto"><div><b>${esc(u.name)}</b><small>${esc(u.username)} · ${u.role}</small></div><button class="btn sm ghost" data-act="delStaff" data-id="${u.id}" ${u.id===session.id||u.username===session.username?'disabled':''}>Remove</button></div>`).join('')}
      <form data-form="addStaff" style="margin-top:12px"><div class="row2"><label>Name<input name="name" required></label><label>Role<select name="role"><option value="staff">Staff</option><option value="admin">Administrator</option></select></label><label>Username<input name="u" required></label><label>Password<input name="p" type="password" minlength="6" required></label></div><button class="btn sm">Add account</button></form></div>
    <p style="margin-top:20px"><button class="btn ghost sm" data-act="resetDemo">Reset all sample data</button></p>
  </div></div>`;
}

/* ============ Modals ============ */
function bookingModal(existing){
  const res = !!existing; let date = existing ? existing.date : clinicDay(), time = '', svcId = existing ? existing.svcId : db.services[0].id;
  openModal(`<form class="dlg-body" id="bm" novalidate><h3>${res?`Reschedule ${existing.ref}`:'New phone booking'}</h3>
    ${res?`<p class="muted">${esc(existing.name)} · ${esc(existing.svcName)}</p>`:`<label>Full name<input id="bmName" required></label><div class="row2"><label>Mobile number<input id="bmPhone" type="tel" placeholder="0917 123 4567"></label><label>Service<select id="bmSvc">${db.services.map(v=>`<option value="${v.id}">${esc(v.name)} (${v.min} min)</option>`).join('')}</select></label></div>`}
    <label>Date<input type="date" id="bmDate" min="${today()}" value="${date}"></label><div id="bmSlots"></div><p class="err" id="bmErr" role="alert"></p>
    <div class="dlg-actions"><button type="button" class="btn ghost" id="bmCancel">Cancel</button><button class="btn">${res?'Save new time':'Book appointment'}</button></div></form>`, d=>{
    const dur = () => res ? existing.dur : svcById($('#bmSvc',d).value).min;
    const paint = () => { $('#bmSlots',d).innerHTML = slotButtons(date,dur(),res?existing.id:null,time); };
    paint();
    $('#bmDate',d).addEventListener('change',e=>{ date = e.target.value; time = ''; paint(); });
    if(!res) $('#bmSvc',d).addEventListener('change',()=>{ time = ''; paint(); });
    $('#bmSlots',d).addEventListener('click',e=>{ const b = e.target.closest('[data-time]'); if(b){ time = b.dataset.time; paint(); } });
    $('#bmCancel',d).addEventListener('click',closeModal);
    $('#bm',d).addEventListener('submit',e=>{
      e.preventDefault(); const err = $('#bmErr',d);
      if(!date){ err.textContent = 'Choose a date.'; return; } if(!time){ err.textContent = 'Choose an open time.'; return; }
      if(res){
        if(!isFree(date,time,existing.dur,existing.id)){ db.stats.blocked++; save(); err.textContent = 'That time was just taken. Choose another.'; time=''; paint(); return; }
        existing.date = date; existing.time = time; save(); closeModal(); toast(`${existing.ref} moved to ${fmtDate(date)}, ${fmtTime(time)}`); render(); return;
      }
      const name = $('#bmName',d).value.trim(), phone = $('#bmPhone',d).value.trim(), sv = svcById($('#bmSvc',d).value);
      if(!name){ err.textContent = 'Enter the patient name.'; return; }
      if(phone && !validPhone(phone)){ err.textContent = 'Enter a mobile number like 0917 123 4567, or leave it blank.'; return; }
      if(!isFree(date,time,sv.min)){ db.stats.blocked++; save(); err.textContent = 'That time was just taken. Choose another.'; time=''; paint(); return; }
      const a = makeAppt({name,phone,svcId:sv.id,date,time,source:'phone',status:'confirmed'}); save(); closeModal(); toast(`Booked ${a.ref} for ${name}`); render();
    });
  });
}

/* ============ Actions ============ */
const A = {
  navToggle(b){ const n = $('#mainnav'); const o = n.classList.toggle('open'); b.setAttribute('aria-expanded',o); },
  pickSvc(b){ ui.book.svc = b.value; const s = svcById(b.value); if(ui.book.date && ui.book.time && !isFree(ui.book.date,ui.book.time,s.min)) ui.book.time=''; if(ui.book.date && !slotList(ui.book.date,s.min).some(x=>x.state==='free')) ui.book.date=''; render(); },
  pickDate(b){ ui.book.date = b.dataset.date; ui.book.time=''; ui.book.errs.date=''; render(); },
  pickTime(b){ ui.book.time = b.dataset.time; ui.book.errs.time=''; render(); },
  submitBook(){
    const b = ui.book, sv = svcById(b.svc), e = {};
    if(!b.date) e.date = 'Choose a date.'; if(!b.time) e.time = 'Choose an open time.';
    if(!b.name.trim()) e.name = 'Enter your full name.';
    if(!validPhone(b.phone)) e.phone = 'Enter a mobile number like 0917 123 4567.';
    if(Object.keys(e).length){ b.errs = e; render(); const first = $('.err'); first && first.scrollIntoView({block:'center',behavior:'smooth'}); return; }
    if(!isFree(b.date,b.time,sv.min)){ db.stats.blocked++; save(); b.time=''; b.errs = {time:'That time was just taken by another booking. Choose a different open time.'}; render(); return; }
    const a = makeAppt({name:b.name.trim(),phone:b.phone.trim(),email:b.email.trim(),svcId:b.svc,date:b.date,time:b.time,notes:b.note.trim(),source:'online',status:'pending',patientId:patSession?patSession.id:null});
    save(); b.done = a; try{ sessionStorage.setItem('bsdc_last',JSON.stringify({ref:a.ref,phone:a.phone})); }catch(x){} render(); window.scrollTo(0,0);
  },
  bookAgain(){ resetBook(); render(); },
  goTrack(b){ ui.track = {ref:b.dataset.ref,phone:b.dataset.phone,res:null,err:''}; const a = db.appts.find(x=>x.ref===b.dataset.ref); ui.track.res = a||null; },
  cancelMine(b){ const a = db.appts.find(x=>x.id===b.dataset.id); confirmBox('Cancel this booking?',`${fmtDate(a.date)} at ${fmtTime(a.time)} will be released for other patients.`,'Cancel booking',()=>{ a.status='cancelled'; save(); toast('Booking cancelled'); render(); },'Keep booking'); },
  logout(){ setSession(null); render(); },
  acctMode(b){ ui.account.mode = b.dataset.mode; ui.account.err=''; render(); },
  acctLogout(){ setPatSession(null); ui.account.mode='login'; toast('Signed out'); render(); },
  tab(b){ ui.tab = b.dataset.tab; render(); },
  qShift(b){ ui.qDate = addDays(ui.qDate||clinicDay(), +b.dataset.n); render(); },
  qToday(){ ui.qDate = null; render(); },
  checkin(b){ const a = db.appts.find(x=>x.id===b.dataset.id); a.status='waiting'; a.q = nextQ(a.date); a.checkedInAt = new Date().toISOString(); save(); toast(`${a.name} checked in as ${qLabel(a.q)}`); render(); },
  callin(b){ const a = db.appts.find(x=>x.id===b.dataset.id); if(db.appts.some(x=>x.date===a.date&&x.status==='serving')) return toast('Finish the current visit first'); a.status='serving'; a.startedAt = new Date().toISOString(); save(); render(); },
  callNext(){ const d = ui.qDate||clinicDay(); const n = db.appts.filter(x=>x.date===d&&x.status==='waiting').sort((a,b)=>a.q-b.q)[0]; if(n){ n.status='serving'; n.startedAt = new Date().toISOString(); save(); toast(`Now serving ${qLabel(n.q)} · ${n.name}`); render(); } },
  finish(b){ const a = db.appts.find(x=>x.id===b.dataset.id); a.status='completed'; a.doneAt = new Date().toISOString(); save(); toast('Visit completed'); render(); },
  noshow(b){ const a = db.appts.find(x=>x.id===b.dataset.id); confirmBox('Mark as no-show?',`${esc(a.name)} will be removed from the queue and the time slot is released.`,'Mark no-show',()=>{ a.status='no-show'; save(); render(); },'Go back'); },
  confirmAppt(b){ const a = db.appts.find(x=>x.id===b.dataset.id); a.status='confirmed'; save(); toast(`${a.ref} confirmed`); render(); },
  cancelAppt(b){ const a = db.appts.find(x=>x.id===b.dataset.id); confirmBox('Cancel this appointment?',`${esc(a.name)}, ${fmtDate(a.date)} at ${fmtTime(a.time)}. The slot becomes available again.`,'Cancel appointment',()=>{ a.status='cancelled'; save(); toast(`${a.ref} cancelled`); render(); },'Keep it'); },
  resched(b){ bookingModal(db.appts.find(x=>x.id===b.dataset.id)); },
  newBooking(){ bookingModal(null); },
  selPat(b){ ui.pat.sel = b.dataset.key; $('#patDetail').innerHTML = patDetail(); $('#patList').innerHTML = patList(); },
  saveNote(b){ const a = db.appts.find(x=>x.id===b.dataset.id); a.notes = $('#note-'+a.id).value.trim(); save(); toast('Note saved'); },
  range(b){ ui.range = +b.dataset.n; render(); },
  print(){ try{ window.print(); }catch(e){ toast('Printing is not available here'); } },
  delSvc(b){ confirmBox('Remove this service?','Existing appointments keep their service name.','Remove',()=>{ db.services = db.services.filter(v=>v.id!==b.dataset.id); save(); render(); }); },
  delStaff(b){ confirmBox('Remove this account?','This person will no longer be able to sign in.','Remove',()=>{ db.staff = db.staff.filter(u=>u.id!==b.dataset.id); save(); render(); }); },
  resetDemo(){ confirmBox('Reset all data?','This deletes every appointment, account and setting you changed and restores the sample data.','Reset data',()=>{ localStorage.removeItem(KEY); seed(); resetBook(); ui.qDate=null; toast('Sample data restored'); render(); }); }
};
const F = {
  lookup(f){ const ref = f.ref.value.trim().toUpperCase(), ph = f.phone.value.replace(/\D/g,'').slice(-10);
    ui.track.ref = ref; ui.track.phone = f.phone.value;
    const a = db.appts.find(x=>x.ref===ref && (x.phone||'').replace(/\D/g,'').slice(-10)===ph && ph);
    ui.track.res = a||null; ui.track.err = a ? '' : 'No booking matches that code and number. Check both and try again.'; render(); },
  login(f){ const u = db.staff.find(x=>x.username===f.u.value.trim() && x.password===f.p.value);
    if(!u){ $('#loginErr').textContent = 'Wrong username or password.'; return; } setSession({id:u.id,name:u.name,role:u.role,username:u.username}); render(); },
  acctLogin(f){ const p = findPatientByPhone(f.phone.value);
    if(!p || p.password!==f.p.value){ ui.account.err = 'Wrong mobile number or password.'; render(); return; }
    setPatSession({id:p.id,name:p.name,phone:p.phone,email:p.email||''}); ui.account.err=''; toast(`Welcome back, ${p.name}`); render(); },
  acctSignup(f){ const name = f.name.value.trim(), phone = f.phone.value.trim(), email = f.email.value.trim(), pass = f.p.value;
    if(!name){ ui.account.err = 'Enter your full name.'; render(); return; }
    if(!validPhone(phone)){ ui.account.err = 'Enter a mobile number like 0917 123 4567.'; render(); return; }
    if(pass.length<6){ ui.account.err = 'Password must be at least 6 characters.'; render(); return; }
    if(findPatientByPhone(phone)){ ui.account.err = 'An account with this mobile number already exists. Try signing in instead.'; ui.account.mode='login'; render(); return; }
    const p = {id:'p'+Date.now().toString(36),name,phone,email,password:pass}; db.patients.push(p); save();
    setPatSession({id:p.id,name:p.name,phone:p.phone,email:p.email}); ui.account.err=''; toast('Account created'); render(); },
  walkin(f){ const d = ui.qDate||clinicDay(), sv = svcById(f.svc.value), name = f.name.value.trim(), phone = f.phone.value.trim();
    if(!name) return; if(phone && !validPhone(phone)) return toast('Mobile number looks wrong. Use 0917 123 4567 or leave blank.');
    const from = d===today() ? nowMin() : -1, slot = slotList(d,sv.min).find(s=>s.state==='free' && toMin(s.time)>from);
    const a = makeAppt({name,phone,svcId:sv.id,date:d,time:slot?slot.time:'',source:'walk-in',status:'waiting'});
    a.q = nextQ(d); a.checkedInAt = new Date().toISOString(); save(); toast(`${name} added as ${qLabel(a.q)}`); render(); },
  settings(f){ const o = f.open.value, c = f.close.value, ls = f.ls.value, le = f.le.value;
    if(toMin(o)>=toMin(c)||toMin(ls)>=toMin(le)||toMin(ls)<toMin(o)||toMin(le)>toMin(c)) return toast('Check the times: opening must be before lunch and closing.');
    db.settings = {open:o,close:c,lunchStart:ls,lunchEnd:le,closedDays:$$('[name=cd]:checked',f).map(x=>+x.value),avgMinutes:+f.avg.value||30}; save(); toast('Settings saved'); render(); },
  addSvc(f){ db.services.push({id:'s'+Date.now().toString(36),name:f.name.value.trim(),min:+f.min.value}); save(); toast('Service added'); render(); },
  addStaff(f){ const u = f.u.value.trim(); if(db.staff.some(x=>x.username===u)) return toast('That username is taken'); db.staff.push({id:'u'+Date.now().toString(36),name:f.name.value.trim(),username:u,password:f.p.value,role:f.role.value}); save(); toast('Account added'); render(); }
};

document.addEventListener('click',e=>{
  const s = e.target.closest('[data-time]'); if(s && !dlg.contains(s) && s.classList.contains('slot')) return A.pickTime(s);
  const b = e.target.closest('[data-act]'); if(b && b.tagName!=='INPUT' && A[b.dataset.act]) A[b.dataset.act](b,e);
});
document.addEventListener('change',e=>{ const b = e.target.closest('input[data-act]'); if(b) A[b.dataset.act](b,e);
  const l = e.target.dataset && e.target.dataset.live; if(l==='filtWhen'){ ui.filt.when = e.target.value; $('#apptRows').innerHTML = apptRows(); } if(l==='filtStatus'){ ui.filt.status = e.target.value; $('#apptRows').innerHTML = apptRows(); } });
document.addEventListener('input',e=>{
  const t = e.target, bind = t.dataset && t.dataset.bind; if(bind && ui.book){ ui.book[bind] = t.value; if(ui.book.errs[bind]) ui.book.errs[bind]=''; }
  const l = t.dataset && t.dataset.live;
  if(l==='filtQ'){ ui.filt.q = t.value; $('#apptRows').innerHTML = apptRows(); }
  if(l==='patQ'){ ui.pat.q = t.value; $('#patList').innerHTML = patList(); }
});
document.addEventListener('submit',e=>{ const f = e.target.closest('[data-form]'); if(!f) return; e.preventDefault(); F[f.dataset.form](f); });
window.addEventListener('storage',e=>{ if(e.key===KEY && e.newValue){ try{ db = JSON.parse(e.newValue); render(); }catch(x){} } });
window.addEventListener('hashchange',()=>{ $('#mainnav').classList.remove('open'); $('.burger').setAttribute('aria-expanded','false'); render(true); });

/* ============ Router ============ */
let lastPath = null;
function render(newPage){
  const path = (location.hash.replace(/^#/,'')||'/').split('?')[0];
  const views = {'/':vHome,'/book':vBook,'/track':vTrack,'/account':vAccount,'/staff':vStaff};
  const y = window.scrollY, fresh = newPage===true || path!==lastPath;
  $('#app').innerHTML = (views[path]||vHome)();
  $$('nav.main a').forEach(a=>{ if(a.dataset.r===path) a.setAttribute('aria-current','page'); else a.removeAttribute('aria-current'); });
  lastPath = path; document.title = 'Bright Smile Dental Clinic – ' + ({'/book':'Book an appointment','/track':'Track my visit','/account':'My account','/staff':'Staff & admin'}[path]||'Online appointments and queue');
  window.scrollTo(0, fresh ? 0 : y);
}
setInterval(()=>{ const t = document.activeElement && document.activeElement.tagName; if(document.hidden || dlg.open || /INPUT|TEXTAREA|SELECT/.test(t||'')) return; render(); },30000);

/* ============ Start ============ */
db = load() || seed();
if(!db.stats) db.stats = {blocked:0};
if(!db.patients) db.patients = [];
resetBook();
render(true);
