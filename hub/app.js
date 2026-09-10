const lessonGrid = document.querySelector('#lessons');
const workspace = document.querySelector('#workspace');
const progressKey = 'sdd-course-progress-v1';
let selectedLesson = null;

function getProgress() {
  try { return JSON.parse(localStorage.getItem(progressKey)) || {}; }
  catch { return {}; }
}

function setComplete(id, complete) {
  const progress = getProgress();
  progress[id] = complete;
  localStorage.setItem(progressKey, JSON.stringify(progress));
}

function updateProgressSummary() {
  const available = LESSONS.filter(item => item.status === 'available');
  const progress = getProgress();
  const completed = available.filter(item => progress[item.id]).length;
  document.querySelector('#progress-summary').textContent = `${completed} of ${available.length} available lessons complete`;
}

function renderCards(level = 'all') {
  const progress = getProgress();
  const visible = LESSONS.filter(item => level === 'all' || item.level === level);
  lessonGrid.innerHTML = visible.map(lesson => {
    const isAvailable = lesson.status === 'available';
    const action = isAvailable
      ? `<button class="button secondary" data-open="${lesson.id}">${progress[lesson.id] ? 'Review lesson' : 'Open lesson'}</button>`
      : '<span class="status">Roadmap</span>';
    return `<article class="lesson-card ${lesson.status}">
      <div class="card-top"><span class="level">${lesson.course === 'Capstone' ? 'Capstone' : `Course ${String(lesson.course).padStart(2, '0')}`}</span>${isAvailable ? `<span class="status">${progress[lesson.id] ? 'Complete' : 'Available'}</span>` : ''}</div>
      <p class="eyebrow">${lesson.part}</p>
      <h3>${lesson.title}</h3>
      <p>${lesson.summary}</p>
      ${action}
    </article>`;
  }).join('');
  updateProgressSummary();
}

function link(label, href) {
  return `<a class="button secondary" href="${href}">${label} ↗</a>`;
}

function openLesson(id) {
  selectedLesson = LESSONS.find(item => item.id === id && item.status === 'available');
  if (!selectedLesson) return;
  document.querySelector('#curriculum').hidden = true;
  workspace.hidden = false;
  document.querySelector('#lesson-meta').textContent = `Course ${String(selectedLesson.course).padStart(2, '0')} · ${selectedLesson.part}`;
  document.querySelector('#lesson-title').textContent = selectedLesson.title;
  document.querySelector('#lesson-summary').textContent = selectedLesson.summary;
  document.querySelector('#learn').innerHTML = `
    <h3>Learning outcomes</h3>
    <ul>${selectedLesson.outcomes.map(item => `<li>${item}</li>`).join('')}</ul>
    <h3>Primary material</h3>
    <div class="link-list">${link('Read the chapter', selectedLesson.readme)}${link('Open the notebook', selectedLesson.notebook)}</div>
    <h3>References</h3>
    <ul>${selectedLesson.references.map(([name, url]) => `<li><a href="${url}">${name}</a></li>`).join('')}</ul>`;
  document.querySelector('#lab').innerHTML = `
    <h3>Run the reusable implementation</h3>
    <p>The default lab is deterministic, credential-free, and uses only the Python standard library.</p>
    <pre><code>${selectedLesson.run}</code></pre>
    <div class="link-list">${link('View lab.py', selectedLesson.lab)}${link('Use the guided notebook', selectedLesson.notebook)}</div>`;
  renderCheckpoint();
  updateCompleteButton();
  selectTab('learn');
  workspace.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderCheckpoint() {
  const checkpoint = selectedLesson.checkpoint;
  document.querySelector('#checkpoint').innerHTML = `
    <h3>Focused checkpoint</h3>
    <p>${checkpoint.question}</p>
    <form id="checkpoint-form">
      <div class="checkpoint-options">${checkpoint.options.map((option, index) => `<label><input type="radio" name="answer" value="${index}"> ${option}</label>`).join('')}</div>
      <button class="button primary" type="submit">Check answer</button>
    </form>
    <p id="checkpoint-feedback" class="feedback" hidden></p>
    <p><a href="../quiz/">Continue to the course knowledge check →</a></p>`;
}

function selectTab(tabName) {
  document.querySelectorAll('.tabs button').forEach(button => {
    const active = button.dataset.tab === tabName;
    button.classList.toggle('active', active);
    button.setAttribute('aria-selected', String(active));
  });
  ['learn', 'lab', 'checkpoint'].forEach(name => {
    document.querySelector(`#${name}`).hidden = name !== tabName;
  });
}

function updateCompleteButton() {
  const complete = getProgress()[selectedLesson.id];
  const button = document.querySelector('#complete-lesson');
  button.textContent = complete ? '✓ Lesson complete' : 'Mark complete';
  button.setAttribute('aria-pressed', String(Boolean(complete)));
}

document.querySelectorAll('.filters button').forEach(button => {
  button.addEventListener('click', () => {
    document.querySelectorAll('.filters button').forEach(item => item.classList.remove('active'));
    button.classList.add('active');
    renderCards(button.dataset.level);
  });
});

document.querySelector('.tabs').addEventListener('click', event => {
  if (event.target.dataset.tab) selectTab(event.target.dataset.tab);
});

lessonGrid.addEventListener('click', event => {
  if (event.target.dataset.open) openLesson(event.target.dataset.open);
});

document.querySelector('#close-workspace').addEventListener('click', () => {
  workspace.hidden = true;
  document.querySelector('#curriculum').hidden = false;
  document.querySelector('#curriculum').scrollIntoView({ behavior: 'smooth' });
});

document.querySelector('#complete-lesson').addEventListener('click', () => {
  const current = Boolean(getProgress()[selectedLesson.id]);
  setComplete(selectedLesson.id, !current);
  updateCompleteButton();
  updateProgressSummary();
});

document.querySelector('#checkpoint').addEventListener('submit', event => {
  event.preventDefault();
  const chosen = new FormData(event.target).get('answer');
  const feedback = document.querySelector('#checkpoint-feedback');
  feedback.hidden = false;
  if (chosen === null) {
    feedback.textContent = 'Choose an answer first.';
    return;
  }
  const correct = Number(chosen) === selectedLesson.checkpoint.answer;
  feedback.textContent = `${correct ? 'Correct. ' : 'Not yet. '}${selectedLesson.checkpoint.explanation}`;
});

renderCards();
