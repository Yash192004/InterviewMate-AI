
/* ── Resume Analyzer JS ─────────────────────────────────────── */

const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('resumeFile');
const analyzeBtn = document.getElementById('analyzeBtn');
const loadingBar = document.getElementById('loadingBar');
const loadingFill = document.getElementById('loadingFill');
const loadingText = document.getElementById('loadingText');

// Drag & drop
if (dropZone) {
  dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) handleFileSelect(file);
  });
  dropZone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => { if (fileInput.files[0]) handleFileSelect(fileInput.files[0]); });
}

function handleFileSelect(file) {
  const allowed = ['pdf', 'txt', 'doc', 'docx'];
  const ext = file.name.split('.').pop().toLowerCase();
  if (!allowed.includes(ext)) {
    showToast('Please upload a PDF, TXT, DOC, or DOCX file.', 'error');
    return;
  }
  dropZone.querySelector('.drop-text').textContent = file.name;
  dropZone.querySelector('.drop-sub').textContent = `${(file.size / 1024).toFixed(1)} KB · Ready to analyze`;
  analyzeBtn.disabled = false;
  analyzeBtn.dataset.file = 'ready';
}

// Analyze
if (analyzeBtn) {
  analyzeBtn.addEventListener('click', async () => {
    const file = fileInput.files[0];
    if (!file) return;

    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '<span class="spinner"></span> Analyzing…';
    loadingBar.style.display = 'block';
    loadingFill.style.animation = 'loadAnim 12s ease-in-out forwards';

    const steps = [
      'Extracting text from resume…',
      'Identifying skills and tech stack…',
      'Scoring career field matches…',
      'Analyzing strengths and gaps…',
      'Building your profile…'
    ];
    let step = 0;
    const stepInterval = setInterval(() => {
      loadingText.textContent = steps[Math.min(step++, steps.length - 1)];
    }, 2000);

    try {
      const formData = new FormData();
      formData.append('resume', file);
      const res = await fetch('/api/upload-resume', { method: 'POST', body: formData });
      const data = await res.json();
      clearInterval(stepInterval);

      if (data.error) {
        showToast(data.error, 'error');
        resetBtn();
        return;
      }
      renderAnalysis(data.analysis);
      loadingBar.style.display = 'none';
      analyzeBtn.innerHTML = '✓ Analyzed';
      analyzeBtn.style.background = 'var(--success)';
    } catch (e) {
      clearInterval(stepInterval);
      showToast('Analysis failed. Please try again.', 'error');
      resetBtn();
    }
  });
}

function resetBtn() {
  analyzeBtn.disabled = false;
  analyzeBtn.innerHTML = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg> Analyze Resume with AI';
  loadingBar.style.display = 'none';
}

function renderAnalysis(a) {
  // Career field scores
  const careerSection = document.getElementById('careerScoresSection');
  const scoresList = document.getElementById('careerScoresList');
  if (a.career_field_scores && scoresList) {
    const sorted = Object.entries(a.career_field_scores).sort((x, y) => y[1] - x[1]);
    scoresList.innerHTML = sorted.map(([role, score], i) => `
      <div class="career-score-item" style="animation-delay:${i * 0.05}s">
        <div class="cs-label">${role}</div>
        <div class="cs-bar-wrap">
          <div class="cs-bar ${score >= 70 ? 'cs-bar-high' : score >= 45 ? 'cs-bar-mid' : 'cs-bar-low'}" style="width:0%;transition:width 1.2s ease ${i * 0.07}s"></div>
        </div>
        <div class="cs-score ${score >= 70 ? 'score-good' : score >= 45 ? 'score-avg' : 'score-low'}">${score}</div>
      </div>`).join('');
    careerSection.classList.remove('hidden');
    setTimeout(() => {
      sorted.forEach(([, score], i) => {
        const bar = scoresList.querySelectorAll('.cs-bar')[i];
        if (bar) bar.style.width = score + '%';
      });
    }, 100);
  }

  // Candidate name line
  const nameLine = document.getElementById('candidateNameLine');
  if (nameLine && a.name) {
    nameLine.innerHTML = `<strong>${a.name}</strong>${a.experience_level ? ` · ${a.experience_level}` : ''}${a.education ? ` · ${a.education}` : ''}`;
  }

  // Suggested roles
  const suggestedWrap = document.getElementById('suggestedRolesWrap');
  const suggestedTags = document.getElementById('suggestedRolesTags');
  if (a.suggested_roles && suggestedTags) {
    suggestedTags.innerHTML = a.suggested_roles.map(r => `<span class="tag tag--purple tag-lg">${r}</span>`).join('');
    suggestedWrap.style.display = 'block';
  }

  // Strengths & Weaknesses
  const swSection = document.getElementById('swSection');
  const strengthsList = document.getElementById('strengthsList');
  const weaknessesList = document.getElementById('weaknessesList');
  if (strengthsList && a.strengths) {
    strengthsList.innerHTML = a.strengths.map(s => `<li>${s}</li>`).join('');
    swSection.classList.remove('hidden');
  }
  if (weaknessesList && a.weaknesses) {
    weaknessesList.innerHTML = a.weaknesses.map(w => `<li>${w}</li>`).join('');
  }

  // Skills
  const skillTags = document.getElementById('skillTags');
  const skillsSection = document.getElementById('skillsSection');
  if (skillTags && a.skills) {
    skillTags.innerHTML = a.skills.map(s => `<span class="tag tag--primary">${s}</span>`).join('');
    skillsSection.classList.remove('hidden');
  }

  // Show ATS and career question sections
  document.getElementById('atsSection')?.classList.remove('hidden');
  document.getElementById('careerQuestionsSection')?.classList.remove('hidden');

  showToast('Resume analyzed successfully!', 'success');
}

// ATS Check
const atsBtn = document.getElementById('atsCheckBtn');
if (atsBtn) {
  atsBtn.addEventListener('click', async () => {
    const jobRole = document.getElementById('atsJobRole').value.trim();
    if (!jobRole) { showToast('Please enter a job role.', 'error'); return; }

    atsBtn.disabled = true;
    atsBtn.textContent = 'Checking…';
    document.getElementById('atsLoading').style.display = 'flex';
    document.getElementById('atsResult').style.display = 'none';

    try {
      const res = await fetch('/api/analyze-ats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_role: jobRole })
      });
      const data = await res.json();
      document.getElementById('atsLoading').style.display = 'none';

      if (data.error) { showToast(data.error, 'error'); return; }
      renderATS(data.ats, data.job_role);
    } catch (e) {
      document.getElementById('atsLoading').style.display = 'none';
      showToast('ATS check failed.', 'error');
    } finally {
      atsBtn.disabled = false;
      atsBtn.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg> Check ATS';
    }
  });
}

function renderATS(ats, role) {
  const container = document.getElementById('atsResult');
  const scoreClass = ats.ats_score >= 70 ? 'ats-good' : ats.ats_score >= 50 ? 'ats-avg' : 'ats-low';
  const gradeClass = `grade-${(ats.grade || 'c').toLowerCase()}`;

  container.innerHTML = `
    <div class="ats-result-card">
      <div class="ats-result-header">
        <div>
          <div class="ats-role">${role}</div>
          <div class="ats-grade-wrap">
            <span class="ats-grade ${gradeClass}">${ats.grade}</span>
            <span class="muted-text" style="font-size:.8rem">${(ats.keyword_density || 'low')} keyword density</span>
          </div>
        </div>
        <div class="ats-score-circle ${scoreClass}">${ats.ats_score}<small>/100</small></div>
      </div>
      <p class="ats-summary">${ats.summary || ''}</p>
      ${ats.relevant_keywords?.length ? `<div class="ats-section"><div class="ats-section-title ats-title-good">✓ Relevant Keywords</div><div class="skill-tags">${ats.relevant_keywords.slice(0,10).map(k => `<span class="tag tag--success tag-sm">${k}</span>`).join('')}</div></div>` : ''}
      ${ats.missing_keywords?.length ? `<div class="ats-section"><div class="ats-section-title ats-title-bad">✗ Missing Keywords</div><div class="skill-tags">${ats.missing_keywords.slice(0,10).map(k => `<span class="tag tag--danger tag-sm">${k}</span>`).join('')}</div></div>` : ''}
      ${ats.improvement_suggestions?.length ? `<div class="ats-section"><div class="ats-section-title">💡 Suggestions</div><ul class="ats-suggestions">${ats.improvement_suggestions.map(s => `<li>${s}</li>`).join('')}</ul></div>` : ''}
    </div>`;
  container.style.display = 'block';
  showToast('ATS analysis complete!', 'success');
}

// Career Interests
const saveInterestsBtn = document.getElementById('saveInterestsBtn');
if (saveInterestsBtn) {
  saveInterestsBtn.addEventListener('click', async () => {
    const interests = {};
    // Collect radio selections
    document.querySelectorAll('#careerQForm input[type="radio"]:checked').forEach(radio => {
      const name = radio.name.replace('cq_', '');
      interests[name] = radio.value;
    });
    // Collect text inputs
    document.querySelectorAll('#careerQForm input[type="text"]').forEach(input => {
      if (input.name) {
        const name = input.name.replace('cq_', '');
        interests[name] = input.value.trim();
      }
    });

    saveInterestsBtn.disabled = true;
    saveInterestsBtn.textContent = 'Processing…';
    document.getElementById('interestsLoading').style.display = 'flex';

    try {
      const res = await fetch('/api/save-career-interests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ interests })
      });
      const data = await res.json();
      document.getElementById('interestsLoading').style.display = 'none';

      if (data.error) { showToast(data.error, 'error'); return; }
      renderRecommendation(data.recommendation);
      showToast('Personalized recommendation ready!', 'success');
    } catch (e) {
      document.getElementById('interestsLoading').style.display = 'none';
      showToast('Could not generate recommendation.', 'error');
    } finally {
      saveInterestsBtn.disabled = false;
      saveInterestsBtn.textContent = 'Get Personalized Recommendations';
    }
  });
}

function renderRecommendation(rec) {
  const section = document.getElementById('recommendationSection');
  const content = document.getElementById('recommendationContent');
  if (!section || !content || !rec) return;

  content.innerHTML = `
    <div class="rec-role">${rec.recommended_role || ''}</div>
    <p class="rec-reason">${rec.recommendation_reason || ''}</p>
    ${rec.alignment_score != null ? `
    <div class="rec-align">
      <span>Resume alignment: </span>
      <div class="rec-align-bar-wrap"><div class="rec-align-bar" style="width:${rec.alignment_score}%"></div></div>
      <span class="font-bold">${rec.alignment_score}%</span>
    </div>` : ''}
    ${rec.gap_analysis ? `<div class="rec-gap mt-3"><strong>Gap Analysis:</strong> ${rec.gap_analysis}</div>` : ''}
    ${rec.action_plan?.length ? `<div class="mt-3"><strong>Action Plan</strong><ol class="rec-plan">${rec.action_plan.map(s => `<li>${s}</li>`).join('')}</ol></div>` : ''}
    ${rec.timeline ? `<div class="rec-timeline mt-3"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg> Timeline: <strong>${rec.timeline}</strong></div>` : ''}
  `;
  section.classList.remove('hidden');
  section.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function showToast(msg, type = 'success') {
  const t = document.createElement('div');
  t.className = `toast toast--${type}`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.classList.add('show'), 10);
  setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 300); }, 3500);
}

// Animate initial bars on page load
window.addEventListener('load', () => {
  setTimeout(() => {
    document.querySelectorAll('.cs-bar').forEach(bar => {
      const targetWidth = bar.style.width;
      bar.style.width = '0%';
      setTimeout(() => { bar.style.width = targetWidth; }, 100);
    });
  }, 200);
});
