// ===== EDU WORKSPACE LOGIC =====
let currentEduTab = 'student';

function switchEduTab(tab) {
  currentEduTab = tab;

  // Toggle buttons
  document.getElementById("toggleStudent").classList.toggle("active", tab === "student");
  document.getElementById("toggleTeacher").classList.toggle("active", tab === "teacher");

  // Toggle tabs
  const studentTab = document.getElementById("studentTab");
  const teacherTab = document.getElementById("teacherTab");

  studentTab.classList.toggle("active", tab === "student");
  teacherTab.classList.toggle("active", tab === "teacher");

  // Load student dashboard when entering Student tab
  if (tab === "student") {
    loadStudentDashboard();
  }
}
  // Load subjects (simulate API)
  loadSubjects();
  // Load today's lesson
  loadDailyLesson();
  // Load mastery
  loadMastery();
}

function loadSubjects() {
  const grid = document.getElementById('subjectGrid');
  // Simulated subjects (replace with GET /api/edu/curriculum)
  const subjects = [
    { name: 'Mathematics', icon: '📐' },
    { name: 'English', icon: '📖' },
    { name: 'Physics', icon: '⚛️' },
    { name: 'Biology', icon: '🧬' },
    { name: 'Chemistry', icon: '🧪' },
    { name: 'ICT', icon: '💻' }
  ];
  grid.innerHTML = subjects.map(s => `
    <div class="subject-card" onclick="alert('Browse ${s.name} topics')">
      <div class="icon">${s.icon}</div>
      <h4>${s.name}</h4>
    </div>
  `).join('');
}

function loadDailyLesson() {
  const div = document.getElementById('dailyLesson');
  // Simulate API
  div.innerHTML = '<p>📖 <strong>Mathematics – Algebra:</strong> Solve quadratic equations by factoring.</p><p><em>Complete the practice quiz below to test your understanding.</em></p>';
}

function startPracticeQuiz() {
  const quizDiv = document.getElementById('quizContainer');
  quizDiv.innerHTML = `
    <p><strong>Q:</strong> What is the solution to x² – 5x + 6 = 0?</p>
    <button class="btn btn-outline" onclick="alert('Correct! x=2 and x=3')">A) x=2, x=3</button>
    <button class="btn btn-outline" style="margin-left:0.5rem;" onclick="alert('Incorrect, try again')">B) x=1, x=6</button>
  `;
}

function loadMastery() {
  const div = document.getElementById('masteryBars');
  const concepts = [
    { name: 'Quadratic Equations', pct: 78 },
    { name: 'Simultaneous Equations', pct: 92 },
    { name: 'Algebraic Fractions', pct: 45 }
  ];
  div.innerHTML = concepts.map(c => `
    <div class="mastery-bar">
      <div class="mastery-label">${c.name} – ${c.pct}%</div>
      <div class="bar-bg"><div class="bar-fill" style="width:${c.pct}%;"></div></div>
    </div>
  `).join('');
}

// Ensure EDU loads when workspace is switched to
// (add a call in the existing switchToWorkspace function)
const origSwitch = switchToWorkspace;
switchToWorkspace = function(ws) {
  origSwitch(ws);
  if (ws === 'edu') switchEduTab('student');
};