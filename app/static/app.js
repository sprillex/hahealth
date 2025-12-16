const API_URL = '/api/v1';
const AUTH_URL = '/auth/token';

// State
let token = localStorage.getItem('access_token');
let user = null;
let summaryData = null;

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    if (token) {
        checkAuth();
    } else {
        showLogin();
    }

    // Event Listeners
    document.getElementById('login-form').addEventListener('submit', handleLogin);
    document.getElementById('med-form').addEventListener('submit', handleSaveMed);
    document.getElementById('bp-form').addEventListener('submit', handleLogBP);
    document.getElementById('weight-form').addEventListener('submit', handleLogWeight);
    document.getElementById('exercise-form').addEventListener('submit', handleLogExercise);
    document.getElementById('profile-form').addEventListener('submit', handleUpdateProfile);
    document.getElementById('windows-form').addEventListener('submit', handleUpdateWindows);
    document.getElementById('password-form').addEventListener('submit', handleChangePassword);
    document.getElementById('dark-mode-toggle').addEventListener('change', toggleTheme);
});

// --- Auth ---

async function handleLogin(e) {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    try {
        const res = await fetch(AUTH_URL, {
            method: 'POST',
            body: formData
        });

        if (res.ok) {
            const data = await res.json();
            token = data.access_token;
            localStorage.setItem('access_token', token);
            checkAuth();
        } else {
            document.getElementById('login-error').innerText = 'Invalid credentials';
        }
    } catch (err) {
        document.getElementById('login-error').innerText = 'Login failed';
    }
}

async function checkAuth() {
    try {
        const res = await fetch(`${API_URL}/users/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            user = await res.json();
            showDashboard();
            loadProfileData();
            loadSummary(); // Load Summary on init
        } else {
            logout();
        }
    } catch (err) {
        logout();
    }
}

function logout() {
    token = null;
    user = null;
    localStorage.removeItem('access_token');
    showLogin();
}

// --- Navigation ---

function showLogin() {
    document.getElementById('auth-view').classList.remove('hidden');
    document.getElementById('dashboard-view').classList.add('hidden');
}

function showDashboard() {
    document.getElementById('auth-view').classList.add('hidden');
    document.getElementById('dashboard-view').classList.remove('hidden');
    showTab('dashboard'); // Default to dashboard summary
}

function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.getElementById(`tab-${tabName}`).classList.remove('hidden');

    if (tabName === 'dashboard') loadSummary();
    if (tabName === 'medications') loadMedications();
    if (tabName === 'reports') loadReports();
    if (tabName === 'settings') loadProfileData();
    if (tabName === 'health-logs') {
        updateWeightUnitDisplay();
        loadExerciseHistory();
    }
}

// --- Dashboard Summary & Gauges ---

async function loadSummary() {
    try {
        const res = await fetch(`${API_URL}/log/summary`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        summaryData = await res.json();

        // Update UI
        document.getElementById('summary-bp').innerText = summaryData.blood_pressure;
        document.getElementById('summary-cals-in').innerText = Math.round(summaryData.calories_consumed);
        document.getElementById('summary-cals-out').innerText = Math.round(summaryData.calories_burned);
        document.getElementById('summary-net').innerText = Math.round(summaryData.calories_consumed - summaryData.calories_burned);

        const targets = calculateTargets();
        updateRecommendations(targets);
        renderGauges(summaryData, targets);

    } catch (err) {
        console.error("Summary load error", err);
    }
}

function calculateTargets() {
    if (!user || !user.birth_year || !user.gender) return null;

    // Simple BMR/TDEE logic (Mifflin-St Jeor)
    const age = new Date().getFullYear() - user.birth_year;
    const w = user.weight_kg;
    const h = user.height_cm;
    let bmr = 0;

    if (user.gender === 'M') {
        bmr = (10 * w) + (6.25 * h) - (5 * age) + 5;
    } else {
        bmr = (10 * w) + (6.25 * h) - (5 * age) - 161;
    }

    let targetCals = Math.round(bmr * 1.2);
    if (user.calorie_goal && user.calorie_goal > 0) {
        targetCals = user.calorie_goal;
    }

    return {
        calories: targetCals,
        protein: { min: Math.round((targetCals * 0.15) / 4), max: Math.round((targetCals * 0.25) / 4) },
        fat: { min: Math.round((targetCals * 0.20) / 9), max: Math.round((targetCals * 0.35) / 9) },
        carbs: { min: Math.round((targetCals * 0.45) / 4), max: Math.round((targetCals * 0.65) / 4) },
        fiber: { min: Math.round((targetCals / 1000) * 14) } // Just min
    };
}

function updateRecommendations(targets) {
    if (!targets) {
        document.getElementById('recommendation-text').innerText = "Please complete your profile (Birth Year, Gender, Weight, Goal) in Settings to see recommendations.";
        return;
    }

    let html = `<strong>Daily Target:</strong> ${targets.calories} kcal<br>`;
    html += `<strong>Protein:</strong> ${targets.protein.min}-${targets.protein.max}g<br>`;
    html += `<strong>Fat:</strong> ${targets.fat.min}-${targets.fat.max}g<br>`;
    html += `<strong>Carbs:</strong> ${targets.carbs.min}-${targets.carbs.max}g<br>`;
    html += `<strong>Fiber:</strong> > ${targets.fiber.min}g`;

    document.getElementById('recommendation-text').innerHTML = html;
}

function renderGauges(data, targets) {
    const container = document.getElementById('gauges-container');
    container.innerHTML = '';

    if (!targets) return;

    // 1. Calories (Goal)
    const calVal = Math.round(data.calories_consumed);
    const calMax = targets.calories;
    let calColor = 'color-yellow';
    if (calVal > calMax) calColor = 'color-red';
    else if (calVal >= calMax * 0.75) calColor = 'color-green';

    container.innerHTML += createGaugeHTML('Calories', calVal, calMax, calColor, 'kcal');

    // 2. Macros
    const macros = [
        { key: 'protein', label: 'Protein', val: Math.round(data.macros.protein), unit: 'g' },
        { key: 'fat', label: 'Fat', val: Math.round(data.macros.fat), unit: 'g' },
        { key: 'carbs', label: 'Carbs', val: Math.round(data.macros.carbs), unit: 'g' },
        { key: 'fiber', label: 'Fiber', val: Math.round(data.macros.fiber), unit: 'g' }
    ];

    macros.forEach(m => {
        const t = targets[m.key];
        let color = 'color-yellow';
        let maxDisplay = t.max || (t.min * 2); // Fallback for fiber which only has min

        if (m.val < t.min) color = 'color-yellow';
        else if (t.max && m.val > t.max) color = 'color-red';
        else color = 'color-green'; // Between min/max or > min for fiber

        container.innerHTML += createGaugeHTML(m.label, m.val, maxDisplay, color, m.unit);
    });
}

function createGaugeHTML(label, value, max, colorClass, unit) {
    const radius = 40;
    const circumference = Math.PI * radius; // full circle

    let percentage = value / max;
    if (percentage > 1) percentage = 1;

    const fillLength = percentage * circumference;

    return `
    <div class="gauge-container">
        <svg class="gauge-svg" viewBox="0 0 100 60">
            <!-- Background Arc (Semi-circle) -->
            <path d="M 10 50 A 40 40 0 0 1 90 50" class="gauge-bg" />

            <!-- Fill Arc -->
            <path d="M 10 50 A 40 40 0 0 1 90 50" class="gauge-fill ${colorClass}"
                  stroke-dasharray="${fillLength}, 200" />

            <text x="50" y="45" class="gauge-text" font-size="12">${value} ${unit}</text>
            <text x="50" y="58" class="gauge-label">${label}</text>
        </svg>
    </div>
    `;
}

// --- Medications ---

async function loadMedications() {
    const listEl = document.getElementById('med-list');
    listEl.innerHTML = 'Loading...';

    try {
        const res = await fetch(`${API_URL}/medications/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const meds = await res.json();

        listEl.innerHTML = '';
        meds.forEach(med => {
            const card = document.createElement('div');
            card.className = 'med-card';
            // Show Schedule
            let sched = [];
            if(med.schedule_morning) sched.push('M');
            if(med.schedule_afternoon) sched.push('A');
            if(med.schedule_evening) sched.push('E');
            if(med.schedule_bedtime) sched.push('B');

            card.innerHTML = `
                <h3>${med.name}</h3>
                <p><strong>Freq:</strong> ${med.frequency}</p>
                <p><strong>Schedule:</strong> ${sched.length ? sched.join(', ') : 'None'}</p>
                <p><strong>Type:</strong> ${med.type}</p>
                <p><strong>Stock:</strong> ${med.current_inventory} (Refills: ${med.refills_remaining})</p>
                <div class="form-actions">
                    <button onclick='openMedModal(${JSON.stringify(med)})'>Edit</button>
                    <button class="btn-primary" onclick="refillMed(${med.med_id})">Refill (+30)</button>
                </div>
            `;
            listEl.appendChild(card);
        });
    } catch (err) {
        listEl.innerHTML = 'Error loading medications';
    }
}

function openMedModal(med = null) {
    const modal = document.getElementById('med-modal');
    modal.classList.remove('hidden');

    if (med) {
        document.getElementById('med-modal-title').innerText = 'Edit Medication';
        document.getElementById('med_id').value = med.med_id;
        document.getElementById('med_name').value = med.name;
        document.getElementById('med_frequency').value = med.frequency;
        document.getElementById('med_type').value = med.type;
        document.getElementById('med_inventory').value = med.current_inventory;
        document.getElementById('med_refills').value = med.refills_remaining;

        document.getElementById('sched_morning').checked = med.schedule_morning;
        document.getElementById('sched_afternoon').checked = med.schedule_afternoon;
        document.getElementById('sched_evening').checked = med.schedule_evening;
        document.getElementById('sched_bedtime').checked = med.schedule_bedtime;
    } else {
        document.getElementById('med-modal-title').innerText = 'Add Medication';
        document.getElementById('med-form').reset();
        document.getElementById('med_id').value = '';
    }
}

function closeMedModal() {
    document.getElementById('med-modal').classList.add('hidden');
}

async function handleSaveMed(e) {
    e.preventDefault();
    const id = document.getElementById('med_id').value;
    const data = {
        name: document.getElementById('med_name').value,
        frequency: document.getElementById('med_frequency').value,
        type: document.getElementById('med_type').value,
        current_inventory: parseInt(document.getElementById('med_inventory').value),
        refills_remaining: parseInt(document.getElementById('med_refills').value),
        daily_doses: 1,
        schedule_morning: document.getElementById('sched_morning').checked,
        schedule_afternoon: document.getElementById('sched_afternoon').checked,
        schedule_evening: document.getElementById('sched_evening').checked,
        schedule_bedtime: document.getElementById('sched_bedtime').checked
    };

    if (!id) {
        try {
            const res = await fetch(`${API_URL}/medications/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(data)
            });
            if (res.ok) {
                closeMedModal();
                loadMedications();
            } else {
                alert('Error saving medication');
            }
        } catch (err) {
            alert('Error saving medication');
        }
    } else {
        alert("Edit functionality requires backend update. Only Create is fully supported in UI now.");
    }
}

async function refillMed(id) {
    try {
        const res = await fetch(`${API_URL}/medications/${id}/refill`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ quantity: 30 })
        });
        if (res.ok) {
            loadMedications();
        }
    } catch (err) {
        alert('Refill failed');
    }
}

// --- Health Logs ---

async function handleLogBP(e) {
    e.preventDefault();
    const data = {
        systolic: parseInt(document.querySelector('[name="systolic"]').value),
        diastolic: parseInt(document.querySelector('[name="diastolic"]').value),
        pulse: parseInt(document.querySelector('[name="pulse"]').value),
        location: "Manual",
        stress_level: 0,
        meds_taken_before: "N/A"
    };

    try {
        const res = await fetch(`${API_URL}/log/bp`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            alert('BP Logged');
            e.target.reset();
        } else {
            alert('Error logging BP');
        }
    } catch (err) {
        alert('Error logging BP');
    }
}

async function handleLogExercise(e) {
    e.preventDefault();
    const data = {
        activity_type: document.getElementById('activity_type').value,
        duration_minutes: parseFloat(document.querySelector('[name="duration"]').value),
    };

    const cals = document.querySelector('[name="calories"]').value;
    if (cals) data.calories_burned = parseFloat(cals);

    try {
        const res = await fetch(`${API_URL}/log/exercise`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            const resp = await res.json();
            alert(`Exercise Logged. Calories: ${resp.calories_burned.toFixed(1)}`);
            e.target.reset();
            loadExerciseHistory(); // Refresh history
        } else {
            alert('Error logging exercise');
        }
    } catch (err) {
        alert('Error logging exercise');
    }
}

async function loadExerciseHistory() {
    const tbody = document.getElementById('exercise-history-body');
    try {
        const res = await fetch(`${API_URL}/log/history/exercise`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const logs = await res.json();

        if (logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4">No history found.</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        logs.forEach(log => {
            const date = new Date(log.timestamp).toLocaleDateString() + ' ' + new Date(log.timestamp).toLocaleTimeString();
            const row = `<tr>
                <td>${date}</td>
                <td>${log.activity_type}</td>
                <td>${log.duration_minutes} min</td>
                <td>${log.calories_burned.toFixed(1)} kcal</td>
            </tr>`;
            tbody.innerHTML += row;
        });
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="4">Error loading history.</td></tr>';
    }
}

async function handleLogWeight(e) {
    e.preventDefault();
    let weightInput = parseFloat(document.getElementById('weight-input').value);

    // Convert if Imperial
    if (user.unit_system === 'IMPERIAL') {
        weightInput = weightInput * 0.453592;
    }

    // We update the profile with the new weight
    const data = {
        weight_kg: weightInput
    };

    try {
        const res = await fetch(`${API_URL}/users/me`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            user = await res.json(); // Update local user state
            alert('Weight updated successfully');
            e.target.reset();
        } else {
            alert('Error updating weight');
        }
    } catch (err) {
        alert('Error updating weight');
    }
}

function updateWeightUnitDisplay() {
    const span = document.getElementById('weight-unit-display');
    if (user && user.unit_system === 'IMPERIAL') {
        span.innerText = '(lbs)';
    } else {
        span.innerText = '(kg)';
    }
}

// --- Reports ---

async function loadReports() {
    try {
        const res = await fetch(`${API_URL}/log/reports/compliance`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        document.getElementById('report-compliance-pct').innerText = data.compliance_percentage + '%';
        document.getElementById('report-missed-doses').innerText = data.missed_doses;
        document.getElementById('report-taken-doses').innerText = data.taken_doses;
    } catch (err) {
        console.error("Report Error", err);
    }
}

// --- Settings / Profile ---

function loadProfileData() {
    if (!user) return;
    document.getElementById('profile-name').value = user.name;
    document.getElementById('profile-units').value = user.unit_system || 'METRIC';

    let height = user.height_cm;
    let weight = user.weight_kg;
    let goalWeight = user.goal_weight_kg;

    // Convert for display if Imperial
    if (user.unit_system === 'IMPERIAL') {
        if (height) height = height / 2.54;
        if (weight) weight = weight / 0.453592;
        if (goalWeight) goalWeight = goalWeight / 0.453592;
    }

    document.getElementById('profile-height').value = height ? height.toFixed(1) : '';
    document.getElementById('profile-weight').value = weight ? weight.toFixed(1) : '';
    document.getElementById('profile-goal-weight').value = goalWeight ? goalWeight.toFixed(1) : '';
    document.getElementById('profile-birthyear').value = user.birth_year || '';
    document.getElementById('profile-gender').value = user.gender || '';
    document.getElementById('profile-cal-goal').value = user.calorie_goal || '';

    // Windows
    if(user.window_morning_start) document.getElementById('win-morning').value = user.window_morning_start.substring(0, 5);
    if(user.window_afternoon_start) document.getElementById('win-afternoon').value = user.window_afternoon_start.substring(0, 5);
    if(user.window_evening_start) document.getElementById('win-evening').value = user.window_evening_start.substring(0, 5);
    if(user.window_bedtime_start) document.getElementById('win-bedtime').value = user.window_bedtime_start.substring(0, 5);
}

async function handleUpdateProfile(e) {
    e.preventDefault();
    const unitSystem = document.getElementById('profile-units').value;
    let height = parseFloat(document.getElementById('profile-height').value);
    let weight = parseFloat(document.getElementById('profile-weight').value);
    let goalWeight = parseFloat(document.getElementById('profile-goal-weight').value);

    // Convert back to Metric for storage if Imperial
    if (unitSystem === 'IMPERIAL') {
        if (height) height = height * 2.54;
        if (weight) weight = weight * 0.453592;
        if (goalWeight) goalWeight = goalWeight * 0.453592;
    }

    const data = {
        unit_system: unitSystem,
        height_cm: height || null,
        weight_kg: weight || null,
        goal_weight_kg: goalWeight || null,
        birth_year: parseInt(document.getElementById('profile-birthyear').value) || null,
        gender: document.getElementById('profile-gender').value || null,
        calorie_goal: parseInt(document.getElementById('profile-cal-goal').value) || null
    };

    try {
        const res = await fetch(`${API_URL}/users/me`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            user = await res.json();
            alert('Profile updated');
            loadProfileData();
            // Also refresh recommendations if on dashboard
            updateRecommendations();
        } else {
            alert('Error updating profile');
        }
    } catch (err) {
        alert('Error updating profile');
    }
}

async function handleUpdateWindows(e) {
    e.preventDefault();
    const data = {
        window_morning_start: document.getElementById('win-morning').value || null,
        window_afternoon_start: document.getElementById('win-afternoon').value || null,
        window_evening_start: document.getElementById('win-evening').value || null,
        window_bedtime_start: document.getElementById('win-bedtime').value || null
    };

    // Append seconds if missing
    for(let k in data) {
        if(data[k] && data[k].length === 5) data[k] += ':00';
    }

    try {
        const res = await fetch(`${API_URL}/users/me`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            user = await res.json();
            alert('Schedule windows updated');
        } else {
            alert('Error updating windows');
        }
    } catch (err) {
        alert('Error updating windows');
    }
}


async function handleChangePassword(e) {
    e.preventDefault();
    const currentPass = document.getElementById('current-password').value;
    const newPass = document.getElementById('new-password').value;
    const confirmPass = document.getElementById('confirm-password').value;

    if (newPass !== confirmPass) {
        alert("New passwords do not match!");
        return;
    }

    try {
        const res = await fetch(`${API_URL}/users/me/password`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                current_password: currentPass,
                new_password: newPass,
                confirm_password: confirmPass
            })
        });

        if (res.ok) {
            alert('Password changed');
            e.target.reset();
        } else {
            const err = await res.json();
            alert(err.detail || 'Error changing password');
        }
    } catch (err) {
        alert('Error changing password');
    }
}

// --- Theme ---

function initTheme() {
    const isDark = localStorage.getItem('theme') === 'dark';
    if (isDark) {
        document.body.classList.add('dark-theme');
        document.getElementById('dark-mode-toggle').checked = true;
    }
}

function toggleTheme(e) {
    if (e.target.checked) {
        document.body.classList.add('dark-theme');
        localStorage.setItem('theme', 'dark');
    } else {
        document.body.classList.remove('dark-theme');
        localStorage.setItem('theme', 'light');
    }
}
