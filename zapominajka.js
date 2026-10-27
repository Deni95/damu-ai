// Запоминайка: голосовые заметки → текст → напоминание-будильник.
// Всё хранится локально в браузере (IndexedDB), без сервера.

const $ = (id) => document.getElementById(id);

const recordBtn = $('recordBtn');
const recStatus = $('recStatus');
const recTimer = $('recTimer');
const langSelect = $('langSelect');
const previewAudio = $('previewAudio');
const noteText = $('noteText');
const remindAt = $('remindAt');
const formMsg = $('formMsg');
const noteList = $('noteList');
const emptyMsg = $('emptyMsg');
const alarmEl = $('alarm');
const alarmText = $('alarmText');
const alarmAudio = $('alarmAudio');

const SNOOZE_MIN = 10;
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

let notes = [];
let draftAudio = null;

/* ---------- Хранилище (IndexedDB) ---------- */

const dbReady = new Promise((resolve, reject) => {
  const req = indexedDB.open('zapominajka', 1);
  req.onupgradeneeded = () => req.result.createObjectStore('notes', { keyPath: 'id' });
  req.onsuccess = () => resolve(req.result);
  req.onerror = () => reject(req.error);
});

async function dbRun(mode, fn) {
  const db = await dbReady;
  return new Promise((resolve, reject) => {
    const tx = db.transaction('notes', mode);
    const req = fn(tx.objectStore('notes'));
    tx.oncomplete = () => resolve(req && req.result);
    tx.onerror = () => reject(tx.error);
  });
}

const dbAll = () => dbRun('readonly', (s) => s.getAll());
const dbPut = (note) => dbRun('readwrite', (s) => s.put(note));
const dbDelete = (id) => dbRun('readwrite', (s) => s.delete(id));

/* ---------- Время ---------- */

const pad = (n) => String(n).padStart(2, '0');

function toLocalInput(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function formatWhen(ts) {
  return new Date(ts).toLocaleString('ru-RU', {
    weekday: 'short', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit'
  });
}

function setQuickTime(btn) {
  const now = new Date();
  let d;
  if (btn.dataset.add) {
    const base = remindAt.value ? new Date(remindAt.value) : now;
    d = new Date(Math.max(base, now) + Number(btn.dataset.add) * 60000);
  } else if (btn.dataset.preset === 'evening') {
    d = new Date(now);
    d.setHours(20, 0, 0, 0);
    if (d <= now) d.setDate(d.getDate() + 1);
  } else {
    d = new Date(now);
    d.setDate(d.getDate() + 1);
    d.setHours(9, 0, 0, 0);
  }
  remindAt.value = toLocalInput(d);
}

/* ---------- Запись и распознавание ---------- */

let mediaRecorder = null;
let chunks = [];
let recognition = null;
let recording = false;
let timerId = null;
let startedAt = 0;
let baseText = '';
let finalText = '';

if (!SpeechRecognition) $('sttWarning').hidden = false;

function showMsg(text, isError = false) {
  formMsg.textContent = text;
  formMsg.classList.toggle('error', isError);
}

function updateTimer() {
  const s = Math.floor((Date.now() - startedAt) / 1000);
  recTimer.textContent = `${pad(Math.floor(s / 60))}:${pad(s % 60)}`;
}

function startRecognition() {
  if (!SpeechRecognition) return;
  recognition = new SpeechRecognition();
  recognition.lang = langSelect.value;
  recognition.continuous = true;
  recognition.interimResults = true;

  recognition.onresult = (e) => {
    let interim = '';
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const t = e.results[i][0].transcript;
      if (e.results[i].isFinal) finalText += t.trim() + ' ';
      else interim += t;
    }
    noteText.value = (baseText + finalText + interim).trim();
  };
  recognition.onerror = (e) => {
    if (e.error === 'not-allowed' || e.error === 'service-not-allowed') {
      showMsg('Распознавание речи недоступно — введите текст вручную.', true);
      recognition = null;
    }
  };
  // Chrome сам останавливает распознавание после паузы — перезапускаем, пока идёт запись.
  recognition.onend = () => {
    if (recording && recognition) {
      try { recognition.start(); } catch (_) { /* уже запущено */ }
    }
  };
  try { recognition.start(); } catch (_) { recognition = null; }
}

async function startRecording() {
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    showMsg('Нет доступа к микрофону. Разрешите его в настройках браузера.', true);
    return;
  }

  chunks = [];
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
  mediaRecorder.onstop = () => {
    stream.getTracks().forEach((t) => t.stop());
    draftAudio = new Blob(chunks, { type: mediaRecorder.mimeType || 'audio/webm' });
    previewAudio.src = URL.createObjectURL(draftAudio);
    previewAudio.hidden = false;
  };
  mediaRecorder.start();

  recording = true;
  baseText = noteText.value.trim() ? noteText.value.trim() + ' ' : '';
  finalText = '';
  startRecognition();

  startedAt = Date.now();
  updateTimer();
  timerId = setInterval(updateTimer, 500);
  recordBtn.classList.add('recording');
  recordBtn.setAttribute('aria-label', 'Остановить запись');
  recStatus.textContent = SpeechRecognition ? 'Идёт запись… говорите' : 'Идёт запись…';
  showMsg('');
}

function stopRecording() {
  recording = false;
  clearInterval(timerId);
  if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
  if (recognition) recognition.stop();
  recordBtn.classList.remove('recording');
  recordBtn.setAttribute('aria-label', 'Начать запись');
  recStatus.textContent = 'Запись готова. Проверьте текст и выберите время';
  if (!remindAt.value) remindAt.focus();
}

recordBtn.addEventListener('click', () => {
  unlockAudio();
  recording ? stopRecording() : startRecording();
});

/* ---------- Сохранение ---------- */

function resetForm() {
  noteText.value = '';
  remindAt.value = '';
  draftAudio = null;
  previewAudio.removeAttribute('src');
  previewAudio.hidden = true;
  recTimer.textContent = '00:00';
  recStatus.textContent = 'Нажмите, чтобы записать';
}

$('saveBtn').addEventListener('click', async () => {
  unlockAudio();
  if (recording) stopRecording();
  const text = noteText.value.trim();
  if (!text && !draftAudio) return showMsg('Запишите голос или введите текст.', true);
  if (!remindAt.value) return showMsg('Выберите, когда напомнить.', true);
  const when = new Date(remindAt.value).getTime();
  if (when <= Date.now()) return showMsg('Это время уже прошло — выберите будущее.', true);

  const note = {
    id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
    text,
    audio: draftAudio,
    remindAt: when,
    createdAt: Date.now(),
    done: false
  };
  await dbPut(note);
  notes.push(note);
  resetForm();
  render();
  showMsg(`Готово! Напомню ${formatWhen(when)}.`);
  askNotifyPermission();
});

$('clearBtn').addEventListener('click', () => {
  if (recording) stopRecording();
  resetForm();
  showMsg('');
});

document.querySelectorAll('.zap-quick button').forEach((btn) =>
  btn.addEventListener('click', () => setQuickTime(btn))
);

/* ---------- Список ---------- */

function render() {
  const now = Date.now();
  const sorted = [...notes].sort((a, b) => (a.done - b.done) || (a.remindAt - b.remindAt));
  noteList.innerHTML = '';
  emptyMsg.hidden = sorted.length > 0;

  for (const note of sorted) {
    const li = document.createElement('li');
    if (note.done) li.classList.add('done');
    else if (note.remindAt <= now) li.classList.add('overdue');

    const time = document.createElement('div');
    time.className = 'note-time';
    time.textContent = (note.done ? '✓ ' : '⏰ ') + formatWhen(note.remindAt);

    const text = document.createElement('div');
    text.className = 'note-text' + (note.text ? '' : ' empty');
    text.textContent = note.text || 'Только аудио';

    li.append(time, text);

    if (note.audio) {
      const audio = document.createElement('audio');
      audio.controls = true;
      audio.preload = 'none';
      audio.src = URL.createObjectURL(note.audio);
      li.append(audio);
    }

    const actions = document.createElement('div');
    actions.className = 'note-actions';
    const addAction = (label, title, fn) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.textContent = label;
      b.title = title;
      b.addEventListener('click', fn);
      actions.append(b);
    };

    if (note.done) {
      addAction('↺ Повторить завтра', 'Напомнить снова завтра в это же время', () => {
        const d = new Date(Math.max(note.remindAt, now));
        d.setDate(d.getDate() + 1);
        updateNote(note, { done: false, remindAt: d.getTime() });
      });
    } else {
      addAction('✓ Выполнено', 'Отметить как выполненное', () => updateNote(note, { done: true }));
      addAction('📅', 'Добавить в календарь телефона', () => exportIcs(note));
    }
    addAction('🗑', 'Удалить', async () => {
      if (!confirm('Удалить это напоминание?')) return;
      await dbDelete(note.id);
      notes = notes.filter((n) => n.id !== note.id);
      render();
    });

    li.append(actions);
    noteList.append(li);
  }
}

async function updateNote(note, changes) {
  Object.assign(note, changes);
  await dbPut(note);
  render();
}

function exportIcs(note) {
  const stamp = (ts) => new Date(ts).toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
  const esc = (s) => s.replace(/\\/g, '\\\\').replace(/\n/g, '\\n').replace(/[,;]/g, (m) => '\\' + m);
  const summary = esc(note.text || 'Запоминайка: голосовая заметка');
  const ics = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//Damu AI//Zapominajka//RU',
    'BEGIN:VEVENT',
    `UID:${note.id}@zapominajka`,
    `DTSTAMP:${stamp(Date.now())}`,
    `DTSTART:${stamp(note.remindAt)}`,
    `DTEND:${stamp(note.remindAt + 15 * 60000)}`,
    `SUMMARY:${summary}`,
    'BEGIN:VALARM',
    'ACTION:DISPLAY',
    `DESCRIPTION:${summary}`,
    'TRIGGER:PT0M',
    'END:VALARM',
    'END:VEVENT',
    'END:VCALENDAR'
  ].join('\r\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([ics], { type: 'text/calendar' }));
  a.download = 'zapominajka.ics';
  a.click();
}

/* ---------- Будильник ---------- */

let audioCtx = null;
let beepTimer = null;
let activeAlarm = null;
let titleTimer = null;
const pageTitle = document.title;

// Браузеры разрешают звук только после действия пользователя — готовим его заранее.
function unlockAudio() {
  if (!audioCtx) {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (Ctx) audioCtx = new Ctx();
  }
  if (audioCtx && audioCtx.state === 'suspended') audioCtx.resume();
}
document.addEventListener('click', unlockAudio, { once: true });

function beep() {
  if (!audioCtx) return;
  const t = audioCtx.currentTime;
  [0, 0.25, 0.5].forEach((offset) => {
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = 'square';
    osc.frequency.value = 880;
    gain.gain.setValueAtTime(0.15, t + offset);
    gain.gain.exponentialRampToValueAtTime(0.001, t + offset + 0.2);
    osc.connect(gain).connect(audioCtx.destination);
    osc.start(t + offset);
    osc.stop(t + offset + 0.2);
  });
}

function speak(text) {
  if (!text || !('speechSynthesis' in window)) return;
  const u = new SpeechSynthesisUtterance(text);
  u.lang = langSelect.value;
  speechSynthesis.speak(u);
}

async function systemNotify(note) {
  if (!('Notification' in window) || Notification.permission !== 'granted') return;
  const title = '⏰ Запоминайка';
  const options = { body: note.text || 'Голосовая заметка', tag: note.id, requireInteraction: true };
  try {
    const reg = navigator.serviceWorker && await navigator.serviceWorker.getRegistration();
    if (reg) return reg.showNotification(title, options);
    new Notification(title, options);
  } catch (_) { /* уведомления недоступны */ }
}

function fireAlarm(note) {
  activeAlarm = note;
  alarmText.textContent = note.text || 'Голосовая заметка — послушайте запись.';
  if (note.audio) {
    alarmAudio.src = URL.createObjectURL(note.audio);
    alarmAudio.hidden = false;
  } else {
    alarmAudio.removeAttribute('src');
    alarmAudio.hidden = true;
  }
  alarmEl.hidden = false;

  beep();
  beepTimer = setInterval(beep, 2000);
  speak(note.text);
  if (navigator.vibrate) navigator.vibrate([400, 200, 400, 200, 400]);
  systemNotify(note);

  let flip = false;
  titleTimer = setInterval(() => {
    document.title = (flip = !flip) ? '⏰ НАПОМИНАНИЕ!' : pageTitle;
  }, 1000);
}

async function closeAlarm(changes) {
  clearInterval(beepTimer);
  clearInterval(titleTimer);
  document.title = pageTitle;
  if ('speechSynthesis' in window) speechSynthesis.cancel();
  alarmAudio.pause();
  alarmEl.hidden = true;
  const note = activeAlarm;
  activeAlarm = null;
  await updateNote(note, changes);
  checkAlarms();
}

$('doneBtn').addEventListener('click', () => closeAlarm({ done: true }));
$('snoozeBtn').addEventListener('click', () =>
  closeAlarm({ remindAt: Date.now() + SNOOZE_MIN * 60000 })
);

function checkAlarms() {
  if (activeAlarm) return;
  const due = notes
    .filter((n) => !n.done && n.remindAt <= Date.now())
    .sort((a, b) => a.remindAt - b.remindAt)[0];
  if (due) fireAlarm(due);
}

/* ---------- Уведомления ---------- */

const notifyHint = $('notifyHint');

function askNotifyPermission() {
  if (!('Notification' in window) || Notification.permission !== 'default') return;
  Notification.requestPermission().then(updateNotifyHint);
}

function updateNotifyHint() {
  const btn = $('notifyBtn');
  if (!('Notification' in window)) btn.replaceWith('уведомления в этом браузере недоступны');
  else if (Notification.permission === 'granted') btn.replaceWith('уведомления включены ✓');
  else if (Notification.permission === 'denied') btn.replaceWith('включите уведомления в настройках сайта');
}

$('notifyBtn').addEventListener('click', askNotifyPermission);

if ('serviceWorker' in navigator && location.protocol !== 'file:') {
  navigator.serviceWorker.register('zapominajka-sw.js').catch(() => {});
}

/* ---------- Старт ---------- */

(async () => {
  updateNotifyHint();
  try {
    notes = await dbAll();
  } catch (_) {
    showMsg('Не удалось открыть хранилище браузера — заметки не сохранятся.', true);
  }
  render();
  checkAlarms();
  setInterval(() => {
    checkAlarms();
    // Обновляем подсветку просроченных раз в минуту.
    if (new Date().getSeconds() === 0) render();
  }, 1000);
})();
