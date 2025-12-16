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
    // Verify token by fetching user
    try {
        const res = await fetch(`${API_URL}/users/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            user = await res.json();
            showDashboard();
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
    showTab('medications'); // Default tab
}

function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
    document.getElementById(`tab-${tabName}`).classList.remove('hidden');

    if (tabName === 'medications') loadMedications();
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
        daily_doses: 1 // Default for now
    };

    // Note: The backend currently only has POST (Create) and Refill.
    // It does not seem to have a PUT (Update) endpoint in the routers/medication.py based on previous context.
    // I will assume for "Edit" we might need to implement PUT, but for now I'll use POST for Create.
    // If ID exists, we can't really update unless we add that endpoint.

    // Check if we are creating
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
            body: JSON.stringify({ quantity: 30 }) // Default refill amount
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
        }
    } catch (err) {
        alert('Error logging BP');
    }
}

// --- Settings / Theme ---

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
