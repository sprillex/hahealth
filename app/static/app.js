const API_URL = '/api/v1';
const AUTH_URL = '/auth/token';

// State
let token = localStorage.getItem('access_token');
let user = null;

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
            loadProfileData(); // Pre-load profile data
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
    showTab('medications');
}

function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.getElementById(`tab-${tabName}`).classList.remove('hidden');

    if (tabName === 'medications') loadMedications();
    if (tabName === 'reports') loadReports();
    if (tabName === 'settings') loadProfileData();
    if (tabName === 'health-logs') {
        updateWeightUnitDisplay();
        loadExerciseHistory();
    }
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
            card.innerHTML = `
                <h3>${med.name}</h3>
                <p><strong>Freq:</strong> ${med.frequency}</p>
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
        daily_doses: 1
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
    const el = document.getElementById('report-adherence-count');
    try {
        const res = await fetch(`${API_URL}/log/reports/adherence`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        el.innerText = data.total_doses_logged;
    } catch (err) {
        el.innerText = 'Error';
    }
}

// --- Settings / Profile ---

function loadProfileData() {
    if (!user) return;
    document.getElementById('profile-name').value = user.name;
    document.getElementById('profile-units').value = user.unit_system || 'METRIC';

    let height = user.height_cm;
    let weight = user.weight_kg;

    // Convert for display if Imperial
    if (user.unit_system === 'IMPERIAL') {
        height = height / 2.54;
        weight = weight / 0.453592;
    }

    document.getElementById('profile-height').value = height ? height.toFixed(1) : '';
    document.getElementById('profile-weight').value = weight ? weight.toFixed(1) : '';
}

async function handleUpdateProfile(e) {
    e.preventDefault();
    const unitSystem = document.getElementById('profile-units').value;
    let height = parseFloat(document.getElementById('profile-height').value);
    let weight = parseFloat(document.getElementById('profile-weight').value);

    // Convert back to Metric for storage if Imperial
    if (unitSystem === 'IMPERIAL') {
        height = height * 2.54;
        weight = weight * 0.453592;
    }

    const data = {
        unit_system: unitSystem,
        height_cm: height,
        weight_kg: weight
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
            loadProfileData(); // Refresh display
        } else {
            alert('Error updating profile');
        }
    } catch (err) {
        alert('Error updating profile');
    }
}

async function handleChangePassword(e) {
    e.preventDefault();
    const currentPass = document.getElementById('current-password').value;
    const newPass = document.getElementById('new-password').value;

    try {
        const res = await fetch(`${API_URL}/users/me/password`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ current_password: currentPass, new_password: newPass })
        });
        if (res.ok) {
            alert('Password changed');
            e.target.reset();
        } else {
            alert('Error changing password');
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
