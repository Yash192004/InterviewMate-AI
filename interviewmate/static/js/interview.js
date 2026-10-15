/* ── Interview JS ─────────────────────────────────────────────── */

let currentSessionId = null;
let currentQuestionId = null;
let currentQuestionNum = 1;
let totalQuestions = 8;
let selectedDifficulty = 'medium';

// Setup screen controls
document.querySelectorAll('.diff-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.diff-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    selectedDifficulty = btn.dataset.val;
  });
});

const qCountSlider = document.getElementById('qCount');
const qCountVal    = document.getElementById('qCountVal');
if (qCountSlider) {
  qCountSlider.addEventListener('input', () => {
    qCountVal.textContent = qCountSlider.value + ' questions';
  });
}

const answerText = document.getElementById('answerText');
const charCount  = document.getElementById('charCount');
if (answerText) {
  answerText.addEventListener('input', () => {
    const wc = answerText.value.trim().split(/\s+/).filter(Boolean).length;
    charCount.textContent = wc + ' word' + (wc !== 1 ? 's' : '');
    charCount.style.color = wc < 20 ? 'var(--danger)' : wc > 300 ? 'var(--warning)' : 'var(--muted-2)';
  });
}

// Start interview
const startBtn = document.getElementById('startInterviewBtn');
if (startBtn) {
  startBtn.addEventListener('click', async () => {
    const jobRole = document.getElementById('jobRole').value.trim() || 'Software Engineer';
    const interviewType = document.querySelector('input[name="interviewType"]:checked')?.value || 'mixed';
    const numQ = parseInt(document.getElementById('qCount')?.value || '8');
    totalQuestions = numQ;

    startBtn.disabled = true;
    startBtn.innerHTML = '<span class="spinner"></span> Starting…';

    try {
      const res = await fetch('/api/start-interview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_role: jobRole,
          interview_type: interviewType,
          difficulty: selectedDifficulty,
          total_questions: numQ,
        })
      });
      const data = await res.json();
      if (data.error) { showToast(data.error, 'error'); startBtn.disabled = false; startBtn.textContent = 'Start Interview'; return; }

      currentSessionId = data.session_id;
      currentQuestionId = data.question_id;
      currentQuestionNum = 1;

      document.getElementById('interviewRole').textContent = jobRole;
      document.getElementById('interviewType').textContent = interviewType.charAt(0).toUpperCase() + interviewType.slice(1);
      showQuestion(data);
      switchScreen('interviewScreen');
    } catch(e) {
      showToast('Failed to start interview.', 'error');
      startBtn.disabled = false;
      startBtn.textContent = 'Start Interview';
    }
  });
}

function showQuestion(data) {
  document.getElementById('qNum').textContent = 'Q' + data.question_number;
  document.getElementById('qTopic').textContent = data.topic || '';
  document.getElementById('qTypeBadge').textContent = (data.type || 'general').charAt(0).toUpperCase() + (data.type || 'general').slice(1);
  document.getElementById('questionText').textContent = data.question;

  const diffEl = document.getElementById('qDifficulty');
  const diff = data.difficulty || selectedDifficulty;
  diffEl.textContent = diff.charAt(0).toUpperCase() + diff.slice(1);
  diffEl.className = 'q-difficulty ' + diff;

  const hintEl = document.getElementById('questionHint');
  const hintText = document.getElementById('hintText');
  if (data.hint) {
    hintText.textContent = data.hint;
    hintEl.classList.remove('hidden');
  } else {
    hintEl.classList.add('hidden');
  }

  // Progress
  document.getElementById('progressText').textContent = `Question ${data.question_number} of ${totalQuestions}`;
  const pct = ((data.question_number - 1) / totalQuestions) * 100;
  document.getElementById('progressFill').style.width = Math.max(pct, 8) + '%';

  // Reset answer
  if (answerText) { answerText.value = ''; if (charCount) charCount.textContent = '0 words'; }
  document.getElementById('feedbackCard').classList.add('hidden');
  document.getElementById('questionCard').style.opacity = '1';
  document.getElementById('answerText').closest('.card').style.opacity = '1';

  currentQuestionId = data.question_id;
  currentQuestionNum = data.question_number;
}

// Submit answer
const submitBtn = document.getElementById('submitAnswerBtn');
if (submitBtn) {
  submitBtn.addEventListener('click', submitAnswer);
}

const skipBtn = document.getElementById('skipBtn');
if (skipBtn) {
  skipBtn.addEventListener('click', () => {
    if (!answerText.value.trim()) answerText.value = 'I would like to skip this question.';
    submitAnswer();
  });
}

async function submitAnswer() {
  const answer = answerText?.value.trim();
  if (!answer) { showToast('Please write an answer before submitting.', 'error'); return; }

  submitBtn.disabled = true;
  submitBtn.innerHTML = '<span class="spinner"></span> Evaluating…';
  if (skipBtn) skipBtn.disabled = true;

  try {
    const res = await fetch('/api/submit-answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question_id: currentQuestionId, answer })
    });
    const data = await res.json();
    if (data.error) { showToast(data.error, 'error'); return; }
    renderFeedback(data.evaluation);

    if (data.interview_complete) {
      document.getElementById('nextQuestionBtn').textContent = 'Finish Interview';
      document.getElementById('nextQuestionBtn').onclick = () => finishInterview(data.session_id || currentSessionId);
    } else {
      document.getElementById('nextQuestionBtn').textContent = 'Next Question →';
      document.getElementById('nextQuestionBtn').onclick = () => {
        showQuestion(data.next_question);
        document.getElementById('feedbackCard').classList.add('hidden');
      };
    }
  } catch(e) {
    showToast('Submission failed. Please try again.', 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = 'Submit Answer <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>';
    if (skipBtn) skipBtn.disabled = false;
  }
}

function renderFeedback(ev) {
  const scoreEl = document.getElementById('scoreVal');
  const scoreCircle = document.getElementById('scoreCircle');
  const score = ev.score || 0;

  scoreEl.textContent = score.toFixed(1);
  scoreCircle.className = 'score-circle';
  if (score >= 7) scoreCircle.classList.add('score-circle--good');
  else if (score >= 5) scoreCircle.classList.add('score-circle--avg');
  else scoreCircle.classList.add('score-circle--low');

  // Dimension scores
  const dimGrid = document.getElementById('dimensionGrid');
  if (dimGrid && ev.dimension_scores) {
    const dims = ev.dimension_scores;
    const labels = { technical_accuracy: 'Accuracy', depth: 'Depth', clarity: 'Clarity', relevance: 'Relevance', examples: 'Examples' };
    dimGrid.innerHTML = Object.entries(dims).map(([k, v]) => {
      const pct = (v / 10) * 100;
      const cls = v >= 7 ? 'dim-bar-good' : v >= 5 ? 'dim-bar-avg' : 'dim-bar-low';
      return `<div class="dim-item">
        <div class="dim-label">${labels[k] || k}</div>
        <div class="dim-bar-wrap"><div class="dim-bar ${cls}" style="width:${pct}%"></div></div>
        <div class="dim-score" style="color:${v>=7?'var(--success-dark)':v>=5?'#d97706':'var(--danger)'}">${v.toFixed(1)}</div>
      </div>`;
    }).join('');
  }

  // What went well
  const wellSection = document.getElementById('wellDoneSection');
  const wellText = document.getElementById('fbWellDone');
  if (ev.what_went_well) {
    wellText.textContent = ev.what_went_well;
    wellSection.style.display = 'block';
  } else {
    wellSection.style.display = 'none';
  }

  // Feedback & model answer
  document.getElementById('fbFeedback').textContent = ev.feedback || '';
  document.getElementById('fbImproved').textContent = ev.improved_answer || '';

  // Missing points
  const missingSection = document.getElementById('missingSection');
  const missingList = document.getElementById('missingList');
  if (ev.key_missing_points?.length) {
    missingList.innerHTML = ev.key_missing_points.map(p => `<li>${p}</li>`).join('');
    missingSection.style.display = 'block';
  } else {
    missingSection.style.display = 'none';
  }

  // Follow-up hint
  const fuSection = document.getElementById('followUpSection');
  const fuText = document.getElementById('fbFollowUp');
  if (ev.follow_up_hint) {
    fuText.textContent = ev.follow_up_hint;
    fuSection.classList.remove('hidden');
  } else {
    fuSection.classList.add('hidden');
  }

  // Encouragement
  const encBar = document.getElementById('encouragementBar');
  const encText = document.getElementById('fbEncouragement');
  if (ev.encouragement) {
    encText.textContent = ev.encouragement;
    encBar.style.display = 'flex';
  } else {
    encBar.style.display = 'none';
  }

  document.getElementById('feedbackCard').classList.remove('hidden');
  document.getElementById('feedbackCard').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function finishInterview(sessionId) {
  const btn = document.getElementById('nextQuestionBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Generating report…';

  try {
    const res = await fetch('/api/finish-interview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId })
    });
    const data = await res.json();
    if (data.error) { showToast(data.error, 'error'); return; }

    document.getElementById('finalScore').textContent = data.overall_score?.toFixed(1) || '—';
    const bdGrid = document.getElementById('breakdownGrid');
    if (bdGrid && data.breakdown) {
      bdGrid.innerHTML = Object.entries(data.breakdown).map(([t, s]) =>
        `<div class="breakdown-item">
          <div class="b-topic">${t}</div>
          <div class="b-score" style="color:${s>=7?'var(--success-dark)':s>=5?'#d97706':'var(--danger)'}">${s.toFixed(1)}<span style="font-size:.75rem;font-weight:500;color:var(--muted)">/10</span></div>
        </div>`
      ).join('');
    }
    document.getElementById('viewResultsBtn').href = '/results/' + sessionId;
    switchScreen('completionScreen');
  } catch(e) {
    showToast('Could not complete interview.', 'error');
  } finally {
    btn.disabled = false;
  }
}

function switchScreen(id) {
  ['setupScreen', 'interviewScreen', 'completionScreen'].forEach(s => {
    const el = document.getElementById(s);
    if (el) el.classList.toggle('hidden', s !== id);
  });
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showToast(msg, type = 'success') {
  const t = document.createElement('div');
  t.className = `toast toast--${type}`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.classList.add('show'), 10);
  setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 300); }, 3500);
}
