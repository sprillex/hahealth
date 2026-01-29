const API_URL = '/api/v1';
const AUTH_URL = '/auth/token';

// State
let token = localStorage.getItem('access_token');
let user = null;
let summaryData = null;
let currentDashboardDate = new Date(); // Defaults to today
let selectedFoodItem = null; // Store selected food for preview
// Globals for Recipes
let currentScope = 'food';
let currentRecipeIngredients = [];
let currentEditingIngredientIndex = -1; // For unit selector
// Globals for Planner
let currentPlannerDate = new Date();
let plannerLogs = []; // Stores the raw food logs for planner
let isPlanningMode = false; // Flag to indicate if we are adding to plan

const UNIT_CONVERSIONS = {
    "tsp": 4.92892,
    "tbsp": 14.7868,
    "cup": 236.588,
    "fl oz": 29.5735,
    "pint": 473.176,
    "quart": 946.353,
    "gallon": 3785.41,
    "ml": 1.0,
    "l": 1000.0
};

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
    document.getElementById('vac-form').addEventListener('submit', handleLogVaccination);
    document.getElementById('allergy-form').addEventListener('submit', handleAddAllergy);
    document.getElementById('profile-form').addEventListener('submit', handleUpdateProfile);
    document.getElementById('windows-form').addEventListener('submit', handleUpdateWindows);
    document.getElementById('meal-windows-form').addEventListener('submit', handleUpdateMealWindows);
    document.getElementById('password-form').addEventListener('submit', handleChangePassword);
    // document.getElementById('dark-mode-toggle').addEventListener('change', toggleTheme); // Removed old toggle

    // Admin Listeners
    document.getElementById('admin-key-form').addEventListener('submit', handleUpdateAdminKey);
    document.getElementById('restore-form').addEventListener('submit', handleRestoreBackup);

    // Timezone Init
    populateTimezones();

    // Load Version
    loadVersion();

    // Nutrition Listeners
    document.getElementById('create-food-form').addEventListener('submit', handleCreateFood);
    document.getElementById('food-log-form').addEventListener('submit', handleLogFood);
    document.getElementById('recipe-form').addEventListener('submit', handleSaveRecipe);

    const recipeIngInput = document.getElementById('recipe-ing-search');
    if(recipeIngInput) {
        let debounceIng;
        recipeIngInput.addEventListener('input', (e) => {
             clearTimeout(debounceIng);
             debounceIng = setTimeout(() => handleSearchRecipeIngredient(e.target.value), 300);
        });
    }

    // Profile Listeners
    document.getElementById('profile-units').addEventListener('change', updateProfileUnitLabels);

    const searchInput = document.getElementById('food-search-input');
    if (searchInput) {
        let debounceTimer;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => handleSearchFood(e.target.value), 300);
        });
    }
});

function populateTimezones() {
    const select = document.getElementById('profile-timezone');
    if (!select) return;

    // Use Intl to guess list or hardcode common ones
    // Modern browsers support Intl.supportedValuesOf('timeZone')
    let timezones = [];
    if (Intl.supportedValuesOf) {
        try {
            timezones = Intl.supportedValuesOf('timeZone');
        } catch (e) {
            console.error("Intl not supported", e);
        }
    }

    if (timezones.length === 0) {
        timezones = ["UTC", "America/New_York", "America/Los_Angeles", "America/Chicago", "Europe/London", "Europe/Paris", "Asia/Tokyo", "Australia/Sydney"];
    }

    // Clear and fill
    select.innerHTML = '';

    // Add current browser guess as top option?
    // Actually just list them alphabetically
    timezones.forEach(tz => {
        const opt = document.createElement('option');
        opt.value = tz;
        opt.innerText = tz;
        select.appendChild(opt);
    });
}

async function loadVersion() {
    try {
        const res = await fetch(`${API_URL}/version`);
        if (res.ok) {
            const data = await res.json();
            const el = document.getElementById('app-version');
            if(el) el.innerText = `${data.version} (${data.date})`;
        }
    } catch (e) {
        console.error("Version load failed", e);
    }
}

async function fetchWithAuth(url, options = {}) {
    if (!options.headers) options.headers = {};
    if (token) {
        options.headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(url, options);

    if (res.status === 401) {
        // Token expired or invalid
        console.warn("401 Unauthorized - Logging out");
        // Only alert if we haven't already just logged out (debounce?)
        // Simple approach: Alert and logout
        if (token) {
            alert("Session expired. Please log in again.");
            logout();
        }
        throw new Error("Session expired");
    }

    return res;
}

// --- Utils ---

function formatWeight(kg) {
    if (!user || !kg) return '0 kg';
    if (user.unit_system === 'IMPERIAL') {
        const lbs = kg / 0.453592;
        return `${lbs.toFixed(1)} lbs`;
    }
    return `${kg.toFixed(1)} kg`;
}

function formatHeight(cm) {
    if (!user || !cm) return '0 cm';
    if (user.unit_system === 'IMPERIAL') {
        const inches = cm / 2.54;
        const ft = Math.floor(inches / 12);
        const remIn = Math.round(inches % 12);
        return `${ft}'${remIn}"`;
    }
    return `${cm.toFixed(1)} cm`;
}

function escapeHtml(text) {
    if (!text) return text;
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

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
        const res = await fetchWithAuth(`${API_URL}/users/me`);
        if (res.ok) {
            user = await res.json();

            // Admin check
            try {
                if (user.is_admin) {
                    const navAdmin = document.getElementById('nav-admin');
                    if(navAdmin) navAdmin.classList.remove('hidden');

                    const mobileAdmin = document.getElementById('mobile-nav-admin');
                    if (mobileAdmin) mobileAdmin.classList.remove('hidden');

                    const importBtn = document.getElementById('btn-import-json');
                    if(importBtn) importBtn.classList.remove('hidden');
                } else {
                    const navAdmin = document.getElementById('nav-admin');
                    if(navAdmin) navAdmin.classList.add('hidden');

                    const mobileAdmin = document.getElementById('mobile-nav-admin');
                    if (mobileAdmin) mobileAdmin.classList.add('hidden');

                    const importBtn = document.getElementById('btn-import-json');
                    if(importBtn) importBtn.classList.add('hidden');
                }
            } catch(e) {
                console.warn("Error updating admin UI elements", e);
            }

            try { showDashboard(); } catch(e) { console.error("Error showing dashboard", e); }
            try { loadProfileData(); } catch(e) { console.error("Error loading profile", e); }
            try { loadSummary(); } catch(e) { console.error("Error loading summary", e); }
            try { applyTheme(); } catch(e) { console.error("Error applying theme", e); }

        } else {
            console.warn("Check auth failed with status", res.status);
            logout();
        }
    } catch (err) {
        console.error("Check auth crashed", err);
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

    // Update Bottom Nav Active State
    document.querySelectorAll('.bottom-nav .nav-item').forEach(btn => btn.classList.remove('active'));
    const navBtn = document.getElementById(`nav-btn-${tabName}`);
    if(navBtn) navBtn.classList.add('active');

    if (tabName === 'dashboard') {
        updateDateDisplay();
        loadSummary();
        loadDailyMeds();
    }
    if (tabName === 'medications') loadMedications();
    if (tabName === 'nutrition') {
        // Clear forms
        document.getElementById('food-search-input').value = '';
        document.getElementById('food-search-results').classList.add('hidden');
        updateDefaultMeal();
        // Default view
        if(document.getElementById('nutrition-view-planner') && !document.getElementById('nutrition-view-planner').classList.contains('hidden')) {
             loadPlanner();
        }
    }
    if (tabName === 'reports') {
        loadReports();
        loadBPHistory();
    }
    if (tabName === 'settings') {
        loadProfileData();
        loadAllergiesSettings();
        refreshMQTTStatus();
    }
    if (tabName === 'health-logs') {
        console.log("Switching to Health Logs tab.");
        updateWeightUnitDisplay();
        loadExerciseHistory();
        loadVaccinationReport();
        loadAllergyReport();
    }
}

// --- Dashboard Summary & Gauges ---

function changeDate(offset) {
    currentDashboardDate.setDate(currentDashboardDate.getDate() + offset);
    updateDateDisplay();
    loadSummary();
    loadDailyMeds();
}

function updateDateDisplay() {
    // Abbreviated format (e.g., "Mon, Jan 1, 2024") for better mobile fit
    const options = { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' };
    document.getElementById('current-date-display').innerText = currentDashboardDate.toLocaleDateString(undefined, options);

    // Check if today
    const today = new Date();
    if (currentDashboardDate.toDateString() === today.toDateString()) {
        document.getElementById('dashboard-date-title').innerText = "Today's Summary";
    } else {
        document.getElementById('dashboard-date-title').innerText = "Daily Summary";
    }
}

function getFormattedDate(dateObj) {
    // YYYY-MM-DD
    const y = dateObj.getFullYear();
    const m = String(dateObj.getMonth() + 1).padStart(2, '0');
    const d = String(dateObj.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
}

async function loadSummary() {
    try {
        const dateStr = getFormattedDate(currentDashboardDate);
        const res = await fetchWithAuth(`${API_URL}/log/summary?date_str=${dateStr}`);
        summaryData = await res.json();

        // Update UI
        document.getElementById('summary-bp').innerText = summaryData.blood_pressure;
        document.getElementById('summary-cals-in').innerText = Math.round(summaryData.calories_consumed);
        document.getElementById('summary-cals-out').innerText = Math.round(summaryData.calories_burned);
        document.getElementById('summary-net').innerText = Math.round(summaryData.calories_consumed - summaryData.calories_burned);

        // New stats
        document.getElementById('summary-streak').innerText = (summaryData.exercise_streak || 0) + ' days';
        const wc = summaryData.weight_change_30d;
        if (wc !== undefined && wc !== null) {
            let changeStr = formatWeight(Math.abs(wc));
            if (wc > 0) changeStr = "+" + changeStr;
            else if (wc < 0) changeStr = "-" + changeStr;
            else changeStr = "No Change";
            document.getElementById('summary-weight-change').innerText = changeStr;
        } else {
            document.getElementById('summary-weight-change').innerText = '--';
        }

        const targets = calculateTargets();
        updateRecommendations(targets);
        renderGauges(summaryData, targets);

        // Render Today Lists
        renderTodayLists(summaryData);

    } catch (err) {
        console.error("Summary load error", err);
    }
}

function renderTodayLists(data) {
    const exList = document.getElementById('exercises-today-list');
    const foodList = document.getElementById('food-today-list');

    if (data.exercises && data.exercises.length > 0) {
        exList.innerHTML = '<ul>' + data.exercises.map(ex => `<li>${ex.activity} (${ex.duration} min) - ${Math.round(ex.calories)} kcal</li>`).join('') + '</ul>';
    } else {
        exList.innerHTML = '<em>No exercise.</em>';
    }

    // Filter Planned vs Eaten
    const planned = (data.food_logs || []).filter(f => f.quantity === 0 && f.planned_quantity > 0);
    const eaten = (data.food_logs || []).filter(f => f.quantity > 0);

    // Render Planned
    const plannedList = document.getElementById('planned-today-list');
    if(plannedList) {
        if (planned.length > 0) {
            plannedList.innerHTML = '<ul class="grid-list" style="grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; margin-top: 10px;">' + planned.map(f => {
                const unit = f.unit || 'serving';
                // Pass log_id to openEditLog
                return `<li class="card" style="padding: 10px; cursor: pointer; border: 1px dashed var(--primary-color);" onclick="openEditLog(${f.log_id})">
                    <strong>${f.name}</strong><br>
                    <span style="color: #666; font-size: 0.9em;">Planned: ${f.planned_quantity} ${unit}</span>
                </li>`;
            }).join('') + '</ul>';
        } else {
            plannedList.innerHTML = '<em style="color: #888;">No planned meals.</em>';
        }
    }

    // Render Eaten
    if (eaten.length > 0) {
        foodList.innerHTML = '<ul>' + eaten.map(f => {
            const unit = f.unit || 'serving';
            // Make clickable using openEditLog
            return `<li onclick="openEditLog(${f.log_id})" style="cursor: pointer; padding: 5px 0; border-bottom: 1px solid #eee;">
                ${f.quantity} Servings of ${unit} <strong>${f.name}</strong> - (${Math.round(f.calories)} kcal)
            </li>`;
        }).join('') + '</ul>';
    } else {
        foodList.innerHTML = '<em>No food logged.</em>';
    }
}

// Renamed from openConfirmLogForPlan to openEditLog to reflect shared usage
async function openEditLog(logId) {
    if (!summaryData || !summaryData.food_logs) return;
    const item = summaryData.food_logs.find(l => l.log_id === logId);
    if (!item) return;

    // Fetch full food details to populate the preview modal properly
    try {
        const res = await fetchWithAuth(`${API_URL}/nutrition/${item.food_id}`);
        if(res.ok) {
            const food = await res.json();

            // Determine quantity to show: Eaten (quantity) takes precedence over Planned (planned_quantity)
            // if we are editing an eaten log.
            const qty = (item.quantity > 0) ? item.quantity : item.planned_quantity;

            // Open modal with explicit update target
            openPreviewModal(food, {
                quantity: qty,
                meal_id: item.meal,
                update_log_id: logId // Pass this to switch mode from CREATE to UPDATE
            });
        } else {
            alert("Could not load food details.");
        }
    } catch(e) {
        console.error(e);
        alert("Error loading food details.");
    }
}

// Alias for backward compatibility if needed, though replaced in HTML
const openConfirmLogForPlan = openEditLog;

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
        fiber: { min: Math.round((targetCals / 1000) * 14) }, // Just min
        sodium: { max: 2300 } // Recommended max
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
    html += `<strong>Fiber:</strong> > ${targets.fiber.min}g<br>`;
    html += `<strong>Sodium:</strong> < ${targets.sodium.max}mg`;

    document.getElementById('recommendation-text').innerHTML = html;
}

function renderGauges(data, targets, containerId = 'gauges-container') {
    const container = document.getElementById(containerId);
    if (!container) return;
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
        { key: 'fiber', label: 'Fiber', val: Math.round(data.macros.fiber), unit: 'g' },
        { key: 'sodium', label: 'Sodium', val: Math.round(data.macros.sodium || 0), unit: 'mg' }
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

async function loadDailyMeds() {
    const listEl = document.getElementById('meds-taken-list');
    listEl.innerHTML = 'Loading...';
    try {
        const dateStr = getFormattedDate(currentDashboardDate);
        const res = await fetchWithAuth(`${API_URL}/medications/log?date_str=${dateStr}`);
        const logs = await res.json();

        if (logs.length === 0) {
            listEl.innerHTML = '<p style="color: #666; font-style: italic;">No medications logged for this date.</p>';
            return;
        }

        listEl.innerHTML = '';
        const ul = document.createElement('ul');
        logs.forEach(log => {
            const li = document.createElement('li');
            const timeStr = new Date(log.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            li.innerHTML = `<strong>${log.med_name}</strong> at ${timeStr}`;
            ul.appendChild(li);
        });
        listEl.appendChild(ul);

    } catch (err) {
        listEl.innerHTML = 'Error loading logs.';
    }
}

async function loadMedications() {
    const listEl = document.getElementById('med-list');
    listEl.innerHTML = 'Loading...';

    try {
        const res = await fetchWithAuth(`${API_URL}/medications/`);
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
                <p><strong>Active:</strong> ${med.start_date || '?'} to ${med.end_date || '?'}</p>
                <div class="form-actions">
                    <button onclick='openMedModal(${JSON.stringify(med)})'>Edit</button>
                    <button class="btn-primary" onclick="refillMed(${med.med_id}, ${med.refill_quantity || 30})">Refill Received</button>
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
        document.getElementById('med_refill_quantity').value = med.refill_quantity || 30;
        document.getElementById('med_start_date').value = med.start_date || '';
        document.getElementById('med_end_date').value = med.end_date || '';

        document.getElementById('sched_morning').checked = med.schedule_morning;
        document.getElementById('sched_afternoon').checked = med.schedule_afternoon;
        document.getElementById('sched_evening').checked = med.schedule_evening;
        document.getElementById('sched_bedtime').checked = med.schedule_bedtime;
    } else {
        document.getElementById('med-modal-title').innerText = 'Add Medication';
        document.getElementById('med-form').reset();
        document.getElementById('med_id').value = '';
        // Set defaults
        document.getElementById('med_refill_quantity').value = 30;
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
        refill_quantity: parseInt(document.getElementById('med_refill_quantity').value),
        start_date: document.getElementById('med_start_date').value || null,
        end_date: document.getElementById('med_end_date').value || null,
        daily_doses: 1,
        schedule_morning: document.getElementById('sched_morning').checked,
        schedule_afternoon: document.getElementById('sched_afternoon').checked,
        schedule_evening: document.getElementById('sched_evening').checked,
        schedule_bedtime: document.getElementById('sched_bedtime').checked
    };

    if (!id) {
        try {
            const res = await fetchWithAuth(`${API_URL}/medications/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
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
        try {
            const res = await fetchWithAuth(`${API_URL}/medications/${id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            if (res.ok) {
                closeMedModal();
                loadMedications();
            } else {
                alert('Error updating medication');
            }
        } catch (err) {
            alert('Error updating medication');
        }
    }
}

async function refillMed(id, qty) {
    if(!confirm(`Refill received? Adding ${qty} to stock and decrementing refills left.`)) return;
    try {
        const res = await fetchWithAuth(`${API_URL}/medications/${id}/refill`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ quantity: qty })
        });
        if (res.ok) {
            loadMedications();
        } else {
             alert('Refill failed');
        }
    } catch (err) {
        alert('Refill failed');
    }
}

// --- Nutrition ---

function openFoodModal() {
    isPlanningMode = false; // Reset by default
    document.getElementById('food-modal').classList.remove('hidden');
    document.getElementById('create-food-form').reset();
}

function closeFoodModal() {
    document.getElementById('food-modal').classList.add('hidden');
}

async function handleCreateFood(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = Object.fromEntries(fd.entries());

    // Parse numbers
    ['calories', 'protein', 'fat', 'carbs', 'fiber', 'sodium'].forEach(k => {
        data[k] = parseFloat(data[k]) || 0;
    });

    // Parse new fields (allow null)
    ['serving_weight_grams', 'serving_volume_ml'].forEach(k => {
        const v = parseFloat(data[k]);
        data[k] = isNaN(v) ? null : v;
    });

    data.source = 'MANUAL';
    if (!data.barcode) delete data.barcode; // Send null or undefined if empty

    try {
        const res = await fetchWithAuth(`${API_URL}/nutrition/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (res.ok) {
            alert('Food created successfully');
            closeFoodModal();
        } else {
            const err = await res.json();
            alert(err.detail || 'Error creating food');
        }
    } catch(err) {
        alert('Error creating food');
    }
}

async function handleSearchFood(query) {
    const resultsDiv = document.getElementById('food-search-results');
    if (!query || query.length < 2) {
        resultsDiv.classList.add('hidden');
        selectedFoodItem = null;
        document.getElementById('log-unit-display').innerText = '1';
        return;
    }

    try {
        const res = await fetchWithAuth(`${API_URL}/nutrition/search?query=${encodeURIComponent(query)}&scope=${currentScope}`);
        const foods = await res.json();

        resultsDiv.innerHTML = '';
        if (foods.length > 0) {
            resultsDiv.classList.remove('hidden');
            // Force styles as belt-and-suspenders against caching
            resultsDiv.style.backgroundColor = 'var(--card-bg)';
            resultsDiv.style.color = 'var(--text-color)';

            foods.forEach(food => {
                const div = document.createElement('div');
                div.className = 'search-item';
                div.innerText = `${food.food_name} (${food.calories} kcal)`;
                div.onclick = () => selectFood(food);
                resultsDiv.appendChild(div);
            });
        } else {
            resultsDiv.classList.add('hidden');
        }

    } catch(err) {
        console.error(err);
    }
}

function selectFood(food) {
    selectedFoodItem = food;
    document.getElementById('food-search-input').value = food.food_name;
    document.getElementById('selected-food-name').value = food.food_name;
    document.getElementById('selected-food-barcode').value = food.barcode || '';
    document.getElementById('log-unit-display').innerText = food.serving_size_unit || '1';
    document.getElementById('food-search-results').classList.add('hidden');
}

async function handleLogFood(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = {
        food_name: fd.get('food_name'),
        barcode: fd.get('barcode') || null,
        meal_id: fd.get('meal_id'),
        serving_size: parseFloat(fd.get('serving_size')),
        quantity: parseFloat(fd.get('quantity'))
    };

    if (isPlanningMode) {
        data.planned_quantity = data.quantity;
        data.quantity = 0;
    }

    if (!data.food_name && document.getElementById('food-search-input').value) {
        data.food_name = document.getElementById('food-search-input').value;
    }

    if (!data.food_name) {
        alert("Please enter a food name");
        return;
    }

    // Check if we can show preview
    // Strict check: selectedFoodItem must exist and name must match what is currently in the form/input
    if (selectedFoodItem && selectedFoodItem.food_name === data.food_name) {
        openPreviewModal(selectedFoodItem, data);
        return;
    }

    // Manual/Fallback Log
    submitLog(data, e.target);
}

async function submitLog(data, formElement) {
    try {
        const res = await fetchWithAuth(`${API_URL}/nutrition/log`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (res.ok) {
            if (isPlanningMode) {
                alert('Added to Meal Plan');
                loadPlanner(); // Refresh planner
            } else {
                alert('Food logged successfully');
            }

            if(formElement) formElement.reset();
            document.getElementById('food-search-results').classList.add('hidden');
            selectedFoodItem = null;

            // Reset mode
            isPlanningMode = false;
        } else {
            const err = await res.json();
            if (res.status === 404) {
                if (confirm("Food not found. Create it now?")) {
                    openFoodModal();
                    document.querySelector('#create-food-form [name="food_name"]').value = data.food_name;
                }
            } else {
                alert(err.detail || 'Error logging food');
            }
        }
    } catch(err) {
        alert('Error logging food');
    }
}

// --- Preview Modal Logic ---

function openPreviewModal(food, formData) {
    const modal = document.getElementById('food-preview-modal');
    modal.classList.remove('hidden');

    // Header
    document.getElementById('preview-food-name').innerText = food.food_name;
    document.getElementById('preview-brand').innerText = food.brand || 'Generic';
    document.getElementById('preview-unit').innerText = food.serving_size_unit || '1 serving';

    // Score & Header Color
    const dot = document.getElementById('preview-score-dot');
    const headerBox = document.getElementById('preview-color-header');
    const score = food.health_score;

    if (score) {
        const color = getScoreColor(score);
        dot.style.backgroundColor = color;
        dot.style.display = 'inline-block';
        headerBox.style.backgroundColor = color;

        // Simple contrast check for text color (White text on dark/saturated backgrounds)
        // Adjust based on specific colors if needed. For now, white looks good on Green/Red/Orange.
        // Yellow is tricky.
        if (['yellow', 'c'].includes(score.toLowerCase()) || color === '#f1c40f') {
             headerBox.style.color = '#333'; // Dark text for yellow
        } else {
             headerBox.style.color = '#fff'; // White text for others
        }

    } else {
        dot.style.display = 'none';
        headerBox.style.backgroundColor = 'transparent'; // Or default
        headerBox.style.color = 'var(--text-color)';
    }

    // Insights
    document.getElementById('preview-insight').innerText = food.health_insight || '--';
    document.getElementById('preview-tip').innerText = food.pairing_tip || '--';

    // Inputs
    document.getElementById('preview-quantity').value = formData.quantity || 1;

    // Store meal_id for confirmation
    modal.dataset.mealId = formData.meal_id;
    // Store update target if present (for Planned items)
    if (formData.update_log_id) {
        modal.dataset.updateLogId = formData.update_log_id;
    } else {
        delete modal.dataset.updateLogId;
    }

    // Store update target if present (for Planned items) and toggle Delete button
    const deleteBtn = document.getElementById('preview-btn-delete');
    if (formData.update_log_id) {
        modal.dataset.updateLogId = formData.update_log_id;
        if(deleteBtn) deleteBtn.classList.remove('hidden');
    } else {
        delete modal.dataset.updateLogId;
        if(deleteBtn) deleteBtn.classList.add('hidden');
    }

    updatePreviewTotals();
}

function deletePreviewItem() {
    const modal = document.getElementById('food-preview-modal');
    const updateLogId = modal.dataset.updateLogId;

    if (updateLogId) {
        deleteFoodLog(parseInt(updateLogId));
        closePreviewModal();
    }
}

function closePreviewModal() {
    document.getElementById('food-preview-modal').classList.add('hidden');
}

function updatePreviewTotals() {
    if (!selectedFoodItem) return;

    const s = 1.0;
    const q = parseFloat(document.getElementById('preview-quantity').value) || 0;
    const m = s * q;

    const f = selectedFoodItem;

    // Helper
    const set = (id, val, unit='', fixed=1) => {
        const el = document.getElementById(id);
        if(el) el.innerText = (val * m).toFixed(fixed) + unit;
    };
    const setInt = (id, val, unit='') => {
        const el = document.getElementById(id);
        if(el) el.innerText = Math.round(val * m) + unit;
    };

    setInt('preview-cal', f.calories);
    set('preview-fat', f.fat, 'g');
    setInt('preview-chol', f.cholesterol || 0, 'mg');
    setInt('preview-sod', f.sodium || 0, 'mg');
    set('preview-carb', f.carbs, 'g');
    set('preview-fib', f.fiber, 'g');
    set('preview-sugar', f.total_sugars || 0, 'g');
    set('preview-added-sugar', f.added_sugars || 0, '', 1);
    set('preview-prot', f.protein, 'g');

    // Micros
    setInt('preview-vitd', f.vitamin_d || 0);
    setInt('preview-calc', f.calcium || 0);
    setInt('preview-iron', f.iron || 0);
    setInt('preview-pot', f.potassium || 0);
}

function getScoreColor(score) {
    if (!score) return '#ccc';
    const s = score.toLowerCase();
    if (s === 'green' || s === 'a') return '#2ecc71';
    if (s === 'yellow' || s === 'c') return '#f1c40f';
    if (s === 'red' || s === 'e') return '#e74c3c';
    if (s === 'orange' || s === 'd') return '#e67e22';
    if (s === 'lightgreen' || s === 'b') return '#82e0aa';
    // Return as is (assuming hex)
    return score;
}

async function confirmLogFood() {
    if (!selectedFoodItem) return;

    const s = 1.0;
    const q = parseFloat(document.getElementById('preview-quantity').value);
    const modal = document.getElementById('food-preview-modal');
    const mealId = modal.dataset.mealId;
    const updateLogId = modal.dataset.updateLogId;

    // Close modal first
    closePreviewModal();

    if (updateLogId) {
        // We are updating a planned item to eaten
        await commitPlanItem(parseInt(updateLogId), q);
        // Refresh dashboard if we are there
        if(document.getElementById('tab-dashboard') && !document.getElementById('tab-dashboard').classList.contains('hidden')) {
            loadSummary();
        }
        return;
    }

    const data = {
        food_name: selectedFoodItem.food_name,
        barcode: selectedFoodItem.barcode,
        meal_id: mealId,
        serving_size: s,
        quantity: q
    };

    if (isPlanningMode) {
        data.planned_quantity = data.quantity;
        data.quantity = 0;
    }

    // Use shared submit logic
    // Pass form element if we want it reset. We can find it.
    const form = document.getElementById('food-log-form');
    submitLog(data, form);
}

// --- Medical (Allergies & Vaccinations) ---

function openAllergyModal(allergy = null) {
    document.getElementById('allergy-modal').classList.remove('hidden');
    const form = document.getElementById('allergy-form');
    form.reset();

    // Cleanup any existing ID input
    const existingId = form.querySelector('input[name="allergy_id"]');
    if(existingId) existingId.remove();

    if (allergy) {
        // Edit mode
        const idInput = document.createElement('input');
        idInput.type = 'hidden';
        idInput.name = 'allergy_id';
        idInput.value = allergy.allergy_id;
        form.appendChild(idInput);

        form.querySelector('input[name="allergen"]').value = allergy.allergen;
        form.querySelector('input[name="reaction"]').value = allergy.reaction || '';
        form.querySelector('select[name="severity"]').value = allergy.severity || 'Mild';
    }
}

function closeAllergyModal() {
    document.getElementById('allergy-modal').classList.add('hidden');
}

async function handleAddAllergy(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = Object.fromEntries(fd.entries());
    const id = data.allergy_id;
    if (id) delete data.allergy_id;

    try {
        let url = `${API_URL}/medical/allergies`;
        let method = 'POST';

        if (id) {
            url = `${API_URL}/medical/allergies/${id}`;
            method = 'PUT';
        }

        const res = await fetchWithAuth(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            alert(id ? 'Allergy updated' : 'Allergy added');
            closeAllergyModal();
            loadAllergiesSettings();
        } else {
            alert('Error saving allergy');
        }
    } catch(err) {
        alert('Error saving allergy');
    }
}

async function deleteAllergy(id) {
    if (!confirm("Are you sure?")) return;
    try {
        const res = await fetchWithAuth(`${API_URL}/medical/allergies/${id}`, {
            method: 'DELETE'
        });
        if (res.ok) {
            loadAllergiesSettings();
        } else {
            alert('Error deleting allergy');
        }
    } catch(err) {
        alert('Error deleting allergy');
    }
}

async function handleLogVaccination(e) {
    e.preventDefault();
    const fd = new FormData(e.target);
    const data = Object.fromEntries(fd.entries());

    try {
        const res = await fetchWithAuth(`${API_URL}/medical/vaccinations`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            alert('Vaccination logged');
            e.target.reset();
        } else {
            alert('Error logging vaccination');
        }
    } catch(err) {
        alert('Error logging vaccination');
    }
}

async function loadAllergiesSettings() {
    const div = document.getElementById('allergy-list-settings');
    if(!div) return;
    div.innerHTML = 'Loading...';
    try {
        const res = await fetchWithAuth(`${API_URL}/medical/allergies`);
        const list = await res.json();
        if (list.length === 0) {
            div.innerHTML = '<em>No allergies logged.</em>';
            return;
        }

        let html = '<ul>';
        list.forEach(a => {
            // Need to escape strings in real app
            const json = JSON.stringify(a).replace(/"/g, '&quot;');
            html += `
            <li style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                <span><strong>${a.allergen}</strong> - ${a.severity || ''}</span>
                <div>
                    <button onclick="openAllergyModal(${json})" style="padding: 2px 5px; font-size: 0.8em; margin-right: 5px;">Edit</button>
                    <button onclick="deleteAllergy(${a.allergy_id})" style="padding: 2px 5px; font-size: 0.8em; background-color: #dc3545;">Del</button>
                </div>
            </li>`;
        });
        html += '</ul>';
        div.innerHTML = html;

    } catch(err) {
        div.innerHTML = 'Error loading allergies';
    }
}

async function loadVaccinationReport() {
    console.log("Attempting to load vaccination report.");
    const div = document.getElementById('vaccination-report');
    if(!div) return;
    div.innerHTML = 'Loading...';
    try {
        const res = await fetchWithAuth(`${API_URL}/medical/reports/vaccinations`);
        const report = await res.json();

        let html = '<table style="width:100%; text-align:left;"><thead><tr><th>Vaccine</th><th>Last Date</th><th>Status</th></tr></thead><tbody>';
        report.forEach(r => {
            let cls = 'status-neutral';
            if (r.status === 'Overdue') cls = 'status-warning';
            if (r.status === 'Up to Date' || r.status === 'Completed') cls = 'status-ok';

            const dateStr = r.last_date ? new Date(r.last_date).toLocaleDateString() : 'Never';
            let statusText = r.status;
            if (r.next_due) {
                statusText += ` (Due: ${new Date(r.next_due).toLocaleDateString()})`;
            }

            html += `<tr>
                <td>${r.vaccine_type}</td>
                <td>${dateStr}</td>
                <td class="${cls}">${statusText}</td>
            </tr>`;
        });
        html += '</tbody></table>';
        div.innerHTML = html;

    } catch(err) {
        div.innerHTML = 'Error loading report';
    }
}

async function loadAllergyReport() {
    console.log("Attempting to load allergy report.");
    const div = document.getElementById('allergy-report');
    if(!div) return;
    try {
        const res = await fetchWithAuth(`${API_URL}/medical/allergies`);
        const list = await res.json();
        if (list.length === 0) {
            div.innerHTML = '<em>No allergies known.</em>';
            return;
        }
        div.innerHTML = '<ul>' + list.map(a => `<li><strong style="color:red;">${a.allergen}</strong>: ${a.reaction || ''} [${a.severity || ''}]</li>`).join('') + '</ul>';
    } catch(err) {
        div.innerHTML = 'Error loading allergies';
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
        const res = await fetchWithAuth(`${API_URL}/log/bp`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
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
        const res = await fetchWithAuth(`${API_URL}/log/exercise`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
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
        const res = await fetchWithAuth(`${API_URL}/log/history/exercise`);
        const logs = await res.json();

        if (logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4">No history found.</td></tr>';
            return;
        }

        tbody.innerHTML = '';
        logs.forEach(log => {
            // log.timestamp should be ISO UTC e.g. "2025-12-18T05:00:00+00:00"
            // browser new Date() handles conversion to local time
            const d = new Date(log.timestamp);
            const dateStr = d.toLocaleDateString() + ' ' + d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            const row = `<tr>
                <td>${dateStr}</td>
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

async function loadBPHistory() {
    const tbody = document.getElementById('bp-history-body');
    try {
        const res = await fetchWithAuth(`${API_URL}/log/history/bp`);
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
                <td>${log.systolic}/${log.diastolic}</td>
                <td>${log.pulse} bpm</td>
                <td>${log.stress_level} / ${log.location}</td>
            </tr>`;
            tbody.innerHTML += row;
        });

        // Store for CSV download
        window.bpHistoryData = logs;

    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="4">Error loading history.</td></tr>';
    }
}

function downloadBPCSV() {
    if (!window.bpHistoryData || window.bpHistoryData.length === 0) {
        alert("No data to download");
        return;
    }

    const rows = [
        ["Date", "Systolic", "Diastolic", "Pulse", "Location", "Stress Level", "Meds Taken Before"]
    ];

    window.bpHistoryData.forEach(log => {
        rows.push([
            log.timestamp,
            log.systolic,
            log.diastolic,
            log.pulse,
            log.location,
            log.stress_level,
            log.meds_taken_before
        ]);
    });

    let csvContent = "data:text/csv;charset=utf-8,";
    rows.forEach(rowArray => {
        const row = rowArray.join(",");
        csvContent += row + "\r\n";
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "blood_pressure_history.csv");
    document.body.appendChild(link); // Required for FF
    link.click();
    link.remove();
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
        const res = await fetchWithAuth(`${API_URL}/users/me`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
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
    // Populate User Info
    if (user) {
        document.getElementById('rep-name').innerText = user.name;
        let dobStr = 'N/A';
        if (user.date_of_birth) {
            // Fix for timezone bug where "YYYY-MM-DD" is parsed as UTC midnight
            // and can roll back to the previous day in some timezones.
            // By splitting the string, we force the Date constructor to use local time.
            const parts = user.date_of_birth.split('-');
            const dob = new Date(parts[0], parts[1] - 1, parts[2]);
            dobStr = dob.toLocaleDateString(undefined, {year:'numeric', month:'long', day:'numeric', timeZone: 'UTC'});
        } else if (user.birth_year) {
            dobStr = user.birth_year;
        }
        document.getElementById('rep-dob').innerText = dobStr;
        document.getElementById('rep-weight').innerText = formatWeight(user.weight_kg);
        document.getElementById('rep-date').innerText = new Date().toLocaleDateString();
    }

    try {
        const res = await fetchWithAuth(`${API_URL}/log/reports/compliance`);
        const data = await res.json();
        document.getElementById('report-compliance-pct').innerText = data.compliance_percentage + '%';
        document.getElementById('report-missed-doses').innerText = data.missed_doses;
        document.getElementById('report-taken-doses').innerText = data.taken_doses;

        // Breakdown
        const tbody = document.getElementById('med-breakdown-body');
        if (data.medications && data.medications.length > 0) {
            tbody.innerHTML = '';
            data.medications.forEach(med => {
                let color = 'red';
                if (med.compliance_percentage >= 80) color = 'green';
                else if (med.compliance_percentage >= 50) color = 'orange';

                const row = `<tr>
                    <td>${med.name}</td>
                    <td>${med.schedule}</td>
                    <td>${med.taken} / ${med.expected}</td>
                    <td style="color: ${color}; font-weight: bold;">${med.compliance_percentage}%</td>
                </tr>`;
                tbody.innerHTML += row;
            });
        } else {
            tbody.innerHTML = '<tr><td colspan="4">No data available.</td></tr>';
        }

    } catch (err) {
        console.error("Report Error", err);
    }
}

// --- Admin ---

async function handleUpdateAdminKey(e) {
    e.preventDefault();
    const key = document.getElementById('admin-key').value;
    try {
        const res = await fetchWithAuth(`${API_URL}/admin/key`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ key: key })
        });
        if (res.ok) {
            alert('Encryption key updated.');
            e.target.reset();
        } else {
            const err = await res.json();
            alert(err.detail || 'Error updating key');
        }
    } catch(err) {
        alert('Error updating key');
    }
}

async function createBackup() {
    try {
        const res = await fetchWithAuth(`${API_URL}/admin/backup`, {
            method: 'POST'
        });
        if (res.ok) {
            alert('Backup created successfully.');
        } else {
            const err = await res.json();
            alert(err.detail || 'Backup failed');
        }
    } catch(err) {
        alert('Backup failed');
    }
}

function downloadLatestBackup() {
    // Triggers direct download
    window.open(`${API_URL}/admin/backup/latest?token=${token}`, '_blank');
    // Note: Bearer token usually in header. Window.open can't set headers.
    // We might need a one-time token or handle authentication via query param for download.
    // Or fetch blob and create object URL.
    fetch(`${API_URL}/admin/backup/latest`, {
        headers: { 'Authorization': `Bearer ${token}` }
    })
    .then(res => {
        if (!res.ok) throw new Error('Download failed');
        return res.blob();
    })
    .then(blob => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = "health_app_backup.enc";
        document.body.appendChild(a);
        a.click();
        a.remove();
    })
    .catch(err => alert('Download failed: ' + err.message));
}

async function handleRestoreBackup(e) {
    e.preventDefault();
    const fileInput = document.getElementById('restore-file');
    if (!fileInput.files.length) return;

    if(!confirm("Are you sure? This will overwrite the current database!")) return;

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const res = await fetchWithAuth(`${API_URL}/admin/restore`, {
            method: 'POST',
            body: formData
        });
        if (res.ok) {
            alert('Restore complete. Please refresh the page.');
            location.reload();
        } else {
            const err = await res.json();
            alert(err.detail || 'Restore failed');
        }
    } catch(err) {
        alert('Restore failed');
    }
}

// --- Settings / Profile ---

function loadProfileData() {
    if (!user) return;
    document.getElementById('profile-name').value = user.name;
    document.getElementById('profile-units').value = user.unit_system || 'METRIC';

    // Set Timezone
    if (user.timezone) {
        document.getElementById('profile-timezone').value = user.timezone;
    } else {
        // Guess
        document.getElementById('profile-timezone').value = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
    }

    let height = user.height_cm;
    let weight = user.weight_kg;
    let goalWeight = user.goal_weight_kg;

    // Convert for display if Imperial
    if (user.unit_system === 'IMPERIAL') {
        if (height) height = height / 2.54;
        if (weight) weight = weight / 0.453592;
        if (goalWeight) goalWeight = goalWeight / 0.453592;
    }

    updateProfileUnitLabels();

    document.getElementById('profile-height').value = height ? height.toFixed(1) : '';
    document.getElementById('profile-weight').value = weight ? weight.toFixed(1) : '';
    document.getElementById('profile-goal-weight').value = goalWeight ? goalWeight.toFixed(1) : '';

    // DOB
    if (user.date_of_birth) {
        document.getElementById('profile-dob').value = user.date_of_birth; // YYYY-MM-DD
    } else if (user.birth_year) {
        // Fallback? Or leave empty?
        // User asked for "full birthday", so previous data (year) might be incomplete.
        // We can just leave date picker empty if no full date.
    }
    document.getElementById('profile-birthyear').value = user.birth_year || ''; // Keep hidden for legacy? Or deprecated.

    document.getElementById('profile-gender').value = user.gender || '';
    document.getElementById('profile-cal-goal').value = user.calorie_goal || '';

    // Windows
    if(user.window_morning_start) document.getElementById('win-morning').value = user.window_morning_start.substring(0, 5);
    if(user.window_afternoon_start) document.getElementById('win-afternoon').value = user.window_afternoon_start.substring(0, 5);
    if(user.window_evening_start) document.getElementById('win-evening').value = user.window_evening_start.substring(0, 5);
    if(user.window_bedtime_start) document.getElementById('win-bedtime').value = user.window_bedtime_start.substring(0, 5);

    // Meal Windows
    if(user.meal_breakfast_start) document.getElementById('meal-breakfast').value = user.meal_breakfast_start.substring(0, 5);
    else document.getElementById('meal-breakfast').value = "09:00";

    if(user.meal_lunch_start) document.getElementById('meal-lunch').value = user.meal_lunch_start.substring(0, 5);
    else document.getElementById('meal-lunch').value = "11:00";

    if(user.meal_dinner_start) document.getElementById('meal-dinner').value = user.meal_dinner_start.substring(0, 5);
    else document.getElementById('meal-dinner').value = "15:00";

    if(user.meal_dinner_end) document.getElementById('meal-dinner-end').value = user.meal_dinner_end.substring(0, 5);
    else document.getElementById('meal-dinner-end').value = "19:00";
}

function updateProfileUnitLabels() {
    const unitSystem = document.getElementById('profile-units').value;
    const hSpan = document.getElementById('unit-height');
    const wSpan = document.getElementById('unit-weight');
    const gwSpan = document.getElementById('unit-goal-weight');

    if (unitSystem === 'IMPERIAL') {
        hSpan.innerText = '(inches)';
        wSpan.innerText = '(lbs)';
        gwSpan.innerText = '(lbs)';
    } else {
        hSpan.innerText = '(cm)';
        wSpan.innerText = '(kg)';
        gwSpan.innerText = '(kg)';
    }
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
        birth_year: null, // Deprecated in UI, or keep sync?
        date_of_birth: document.getElementById('profile-dob').value || null,
        gender: document.getElementById('profile-gender').value || null,
        calorie_goal: parseInt(document.getElementById('profile-cal-goal').value) || null,
        timezone: document.getElementById('profile-timezone').value
    };

    try {
        const res = await fetchWithAuth(`${API_URL}/users/me`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
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
        const res = await fetchWithAuth(`${API_URL}/users/me`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
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

async function handleUpdateMealWindows(e) {
    e.preventDefault();
    const data = {
        meal_breakfast_start: document.getElementById('meal-breakfast').value || null,
        meal_lunch_start: document.getElementById('meal-lunch').value || null,
        meal_dinner_start: document.getElementById('meal-dinner').value || null,
        meal_dinner_end: document.getElementById('meal-dinner-end').value || null
    };

    // Append seconds if missing
    for(let k in data) {
        if(data[k] && data[k].length === 5) data[k] += ':00';
    }

    try {
        const res = await fetchWithAuth(`${API_URL}/users/me`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        if (res.ok) {
            user = await res.json();
            alert('Meal schedule updated');
        } else {
            alert('Error updating meal schedule');
        }
    } catch (err) {
        alert('Error updating meal schedule');
    }
}

function determineDefaultMeal() {
    if (!user) return "Snack";

    // Defaults
    const defaults = {
        b: "09:00",
        l: "11:00",
        d: "15:00",
        e: "19:00"
    };

    // User values or defaults
    const bStart = user.meal_breakfast_start ? user.meal_breakfast_start.substring(0, 5) : defaults.b;
    const lStart = user.meal_lunch_start ? user.meal_lunch_start.substring(0, 5) : defaults.l;
    const dStart = user.meal_dinner_start ? user.meal_dinner_start.substring(0, 5) : defaults.d;
    const dEnd = user.meal_dinner_end ? user.meal_dinner_end.substring(0, 5) : defaults.e;

    // Current Time HH:MM
    const now = new Date();
    const current = now.toTimeString().substring(0, 5); // "14:30"

    // Logic:
    // Snack: < bStart OR >= dEnd
    // Breakfast: >= bStart AND < lStart
    // Lunch: >= lStart AND < dStart
    // Dinner: >= dStart AND < dEnd

    if (current < bStart) return "Snack";
    if (current >= bStart && current < lStart) return "Breakfast";
    if (current >= lStart && current < dStart) return "Lunch";
    if (current >= dStart && current < dEnd) return "Dinner";

    return "Snack";
}

function updateDefaultMeal() {
    const meal = determineDefaultMeal();
    const select = document.getElementById('food-meal');
    if (select) select.value = meal;
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
        const res = await fetchWithAuth(`${API_URL}/users/me/password`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
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
    // We defer actual theme application until user profile is loaded or fallback to system
    applyTheme();

    // Listen for system changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
        // Only react if user pref is SYSTEM or not loaded yet
        if (!user || user.theme_preference === 'SYSTEM') {
            applyTheme();
        }
    });
}

function applyTheme() {
    let pref = 'SYSTEM';
    if (user && user.theme_preference) pref = user.theme_preference;

    // Update Dropdown if on settings page
    const select = document.getElementById('theme-select');
    if (select) select.value = pref;

    let useDark = false;
    if (pref === 'DARK') useDark = true;
    else if (pref === 'LIGHT') useDark = false;
    else {
        // System
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            useDark = true;
        }
    }

    if (useDark) {
        document.body.classList.add('dark-theme');
    } else {
        document.body.classList.remove('dark-theme');
    }
}

async function updateThemePreference(val) {
    // Optimistic update
    if (user) {
        user.theme_preference = val;
        applyTheme();

        // Save to backend
        try {
            await fetchWithAuth(`${API_URL}/users/me`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ theme_preference: val })
            });
        } catch(err) {
            console.error("Failed to save theme pref");
        }
    }
}

function printReport() {
    window.print();
}

async function refreshMQTTStatus() {
    const card = document.getElementById('mqtt-status-card');
    const content = document.getElementById('mqtt-status-content');

    // Only show for admins (simple check, backend enforces security)
    if (!user || !user.is_admin) {
        card.classList.add('hidden');
        return;
    }
    card.classList.remove('hidden');
    content.innerHTML = 'Checking...';

    try {
        const res = await fetchWithAuth(`${API_URL}/admin/mqtt_status`);
        if (res.ok) {
            const status = await res.json();
            const color = status.connected ? 'green' : 'red';
            const text = status.connected ? 'Connected' : 'Disconnected';

            content.innerHTML = `
                <p><strong>Status:</strong> <span style="color: ${color}; font-weight: bold;">${text}</span></p>
                <p><strong>Broker:</strong> ${status.broker}:${status.port}</p>
                <p><strong>User:</strong> ${status.username}</p>
                <p><strong>Topic Prefix:</strong> ${status.topic_prefix}</p>
            `;
        } else {
            content.innerHTML = '<p style="color: red;">Failed to fetch status.</p>';
        }
    } catch (e) {
        content.innerHTML = '<p style="color: red;">Error checking status.</p>';
    }
}

// --- Management Functions (Appended) ---

async function openManageMedsModal() {
    const modal = document.getElementById('manage-meds-modal');
    modal.classList.remove('hidden');
    loadManageMedsList();
}

function closeManageMedsModal() {
    document.getElementById('manage-meds-modal').classList.add('hidden');
    document.getElementById('edit-med-form-container').classList.add('hidden');
    // Refresh dashboard list
    loadDailyMeds();
}

async function loadManageMedsList() {
    const listDiv = document.getElementById('manage-meds-list');
    listDiv.innerHTML = 'Loading...';
    try {
        const dateStr = getFormattedDate(currentDashboardDate);
        const res = await fetchWithAuth(`${API_URL}/medications/log?date_str=${dateStr}`);
        const logs = await res.json();

        if (logs.length === 0) {
            listDiv.innerHTML = '<em>No logs for this date.</em>';
            return;
        }

        let html = '<ul style="list-style: none; padding: 0;">';
        logs.forEach(log => {
             // log has log_id, med_name, timestamp, dose_window
             // need to escape JSON for onclick
             const safeLog = JSON.stringify(log).replace(/"/g, '&quot;');
             const timeStr = new Date(log.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

             html += `
             <li style="border-bottom: 1px solid #eee; padding: 8px 0; display: flex; justify-content: space-between; align-items: center;">
                <span>
                    <strong>${log.med_name}</strong> <br>
                    <small>${timeStr}</small>
                </span>
                <div>
                    <button onclick="editMedLog(${safeLog})" class="btn-secondary" style="font-size: 0.8em; padding: 2px 5px;">Edit</button>
                    <button onclick="deleteMedLog(${log.log_id})" class="btn-warning" style="font-size: 0.8em; padding: 2px 5px;">Del</button>
                </div>
             </li>
             `;
        });
        html += '</ul>';
        listDiv.innerHTML = html;

    } catch (err) {
        listDiv.innerHTML = 'Error loading logs.';
    }
}

async function deleteMedLog(logId) {
    if(!confirm("Are you sure? This will increment stock.")) return;
    try {
        const res = await fetchWithAuth(`${API_URL}/medications/log/${logId}`, {
            method: 'DELETE'
        });
        if(res.ok) {
            loadManageMedsList();
        } else {
            alert("Delete failed");
        }
    } catch(err) { alert("Delete failed"); }
}

function editMedLog(log) {
    const container = document.getElementById('edit-med-form-container');
    container.classList.remove('hidden');

    document.getElementById('edit_med_log_id').value = log.log_id;
    // Format timestamp for datetime-local input: YYYY-MM-DDTHH:mm
    const dt = new Date(log.timestamp);
    // Adjust to local ISO string roughly
    // Or just use the time part if date is fixed?
    // The user might want to change date too (fix "wrong day").
    // datetime-local expects local time string.
    const localIso = new Date(dt.getTime() - (dt.getTimezoneOffset() * 60000)).toISOString().slice(0, 19);
    document.getElementById('edit_med_time').value = localIso;

    document.getElementById('edit_med_window').value = log.dose_window || "";
}

document.getElementById('edit-med-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const logId = document.getElementById('edit_med_log_id').value;
    const timeVal = document.getElementById('edit_med_time').value; // Local string
    // Convert back to ISO/UTC for API?
    // API expects datetime. User sends "2023-01-01T10:00".
    // If we send this as string, Pydantic might interpret as naive (local) or UTC depending on parsing.
    // Ideally we send ISO with offset or UTC.
    const dateObj = new Date(timeVal);
    const isoStr = dateObj.toISOString();

    const windowVal = document.getElementById('edit_med_window').value;

    const updates = {
        timestamp: isoStr,
        dose_window: windowVal || null
    };

    try {
        const res = await fetchWithAuth(`${API_URL}/medications/log/${logId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updates)
        });
        if(res.ok) {
            document.getElementById('edit-med-form-container').classList.add('hidden');
            loadManageMedsList();
        } else {
            alert("Update failed");
        }
    } catch(err) { alert("Update failed"); }
});


// --- Manage Exercise ---

async function openManageExerciseModal() {
    const modal = document.getElementById('manage-exercise-modal');
    modal.classList.remove('hidden');
    loadManageExerciseList();
}

function closeManageExerciseModal() {
    document.getElementById('manage-exercise-modal').classList.add('hidden');
    document.getElementById('edit-exercise-form-container').classList.add('hidden');
    loadSummary(); // Refresh summary stats
}

async function loadManageExerciseList() {
    const listDiv = document.getElementById('manage-exercise-list');
    listDiv.innerHTML = 'Loading...';
    try {
        // Need specific endpoint for daily exercise logs with IDs
        // The summary endpoint returns a simplified list WITHOUT IDs currently in backend patch?
        // Wait, I updated `get_daily_summary` in `health.py` to include `log_id`.
        // So I can reuse `summaryData` or fetch again.
        // Let's fetch again via summary endpoint to be safe or use what I have.
        // Summary endpoint needs date_str.
        const dateStr = getFormattedDate(currentDashboardDate);
        const res = await fetchWithAuth(`${API_URL}/log/summary?date_str=${dateStr}`);
        const data = await res.json();
        const logs = data.exercises; // These should now have log_id from my patch

        if (!logs || logs.length === 0) {
            listDiv.innerHTML = '<em>No logs.</em>';
            return;
        }

        let html = '<ul style="list-style: none; padding: 0;">';
        logs.forEach(log => {
             const safeLog = JSON.stringify(log).replace(/"/g, '&quot;');

             html += `
             <li style="border-bottom: 1px solid #eee; padding: 8px 0; display: flex; justify-content: space-between; align-items: center;">
                <span>
                    <strong>${log.activity}</strong> (${log.duration}m)<br>
                    <small>${Math.round(log.calories)} kcal</small>
                </span>
                <div>
                    <button onclick="editExerciseLog(${safeLog})" class="btn-secondary" style="font-size: 0.8em; padding: 2px 5px;">Edit</button>
                    <button onclick="deleteExerciseLog(${log.log_id})" class="btn-warning" style="font-size: 0.8em; padding: 2px 5px;">Del</button>
                </div>
             </li>
             `;
        });
        html += '</ul>';
        listDiv.innerHTML = html;

    } catch (err) {
        listDiv.innerHTML = 'Error loading logs.';
    }
}

async function deleteExerciseLog(id) {
    if(!confirm("Are you sure?")) return;
    try {
        const res = await fetchWithAuth(`${API_URL}/log/exercise/${id}`, {
            method: 'DELETE'
        });
        if(res.ok) loadManageExerciseList();
        else alert("Delete failed");
    } catch(err) { alert("Delete failed"); }
}

function editExerciseLog(log) {
    const container = document.getElementById('edit-exercise-form-container');
    container.classList.remove('hidden');
    document.getElementById('edit_exercise_log_id').value = log.log_id;
    document.getElementById('edit_exercise_activity').value = log.activity;
    document.getElementById('edit_exercise_duration').value = log.duration;
    document.getElementById('edit_exercise_cals').value = log.calories;

    if (log.timestamp) {
        const dt = new Date(log.timestamp);
        const localIso = new Date(dt.getTime() - (dt.getTimezoneOffset() * 60000)).toISOString().slice(0, 19);
        document.getElementById('edit_exercise_time').value = localIso;
    } else {
        // Fallback
        const d = new Date(currentDashboardDate);
        d.setHours(12, 0, 0);
        const localIso = new Date(d.getTime() - (d.getTimezoneOffset() * 60000)).toISOString().slice(0, 19);
        document.getElementById('edit_exercise_time').value = localIso;
    }
}

document.getElementById('edit-exercise-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('edit_exercise_log_id').value;
    const timeVal = document.getElementById('edit_exercise_time').value;
    const isoStr = new Date(timeVal).toISOString();

    const updates = {
        timestamp: isoStr,
        activity_type: document.getElementById('edit_exercise_activity').value,
        duration_minutes: parseFloat(document.getElementById('edit_exercise_duration').value),
        calories_burned: parseFloat(document.getElementById('edit_exercise_cals').value)
    };

    try {
         const res = await fetchWithAuth(`${API_URL}/log/exercise/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updates)
        });
        if(res.ok) {
            document.getElementById('edit-exercise-form-container').classList.add('hidden');
            loadManageExerciseList();
        } else alert("Update failed");
    } catch(e) { alert("Update failed"); }
});

// --- Import JSON Logic ---

let importedJsonPayload = null;

function openImportJsonModal() {
    document.getElementById('import-json-modal').classList.remove('hidden');
    document.getElementById('import-json-text').value = '';
    document.getElementById('import-preview').classList.add('hidden');
    document.getElementById('btn-import-submit').classList.add('hidden');
    importedJsonPayload = null;
}

function closeImportJsonModal() {
    document.getElementById('import-json-modal').classList.add('hidden');
}

function handlePreviewJson() {
    const text = document.getElementById('import-json-text').value;
    const previewDiv = document.getElementById('import-preview');
    const contentDiv = document.getElementById('import-preview-content');
    const submitBtn = document.getElementById('btn-import-submit');

    try {
        const json = JSON.parse(text);

        // Basic Validation
        if (!json.variables) throw new Error("Missing 'variables' object.");

        const keys = Object.keys(json.variables);
        if (keys.length === 0) throw new Error("No items in 'variables'.");

        const firstKey = keys[0];
        const item = json.variables[firstKey];

        if (!item.metadata || !item.macros) throw new Error("Missing metadata or macros in first variable.");

        // Valid
        importedJsonPayload = json;
        previewDiv.classList.remove('hidden');
        submitBtn.classList.remove('hidden');

        // Render Summary
        const meta = item.metadata;
        const macros = item.macros;
        const srv = item.serving_info || {};

        // Check for missing/invalid UPC
        let upcDisplay = escapeHtml(meta.upc);
        let showGenerateBtn = false;
        // Check for null, undefined, empty string, or explicit "null"/"na"/"n/a" strings
        if (!meta.upc || ['null', 'na', 'n/a', 'none'].includes(String(meta.upc).toLowerCase())) {
             upcDisplay = '<span style="color: red; font-style: italic;">Missing</span>';
             showGenerateBtn = true;
        }

        let generateBtnHtml = '';
        if (showGenerateBtn) {
            generateBtnHtml = `<button onclick="handleGenerateUPC()" class="btn-secondary" style="margin-left: 10px; font-size: 0.8em; padding: 2px 8px; width: auto;">Generate Internal UPC</button>`;
        }

        contentDiv.innerHTML = `
            <p><strong>Name:</strong> ${escapeHtml(meta.name)}</p>
            <p><strong>Brand:</strong> ${escapeHtml(meta.brand)}</p>
            <p><strong>UPC:</strong> <span id="import-preview-upc">${upcDisplay}</span> ${generateBtnHtml}</p>
            <p><strong>Macros:</strong> ${macros.calories} kcal | P: ${macros.protein_g}g | F: ${macros.fat_g}g | C: ${macros.carbs_g}g</p>
            <p><strong>Serving:</strong> ${escapeHtml(srv.size || 'N/A')}</p>
            <p><strong>Density:</strong> ${srv.weight_g || '-'}g / ${srv.volume_ml || '-'}ml</p>
        `;

    } catch (e) {
        alert("Invalid JSON: " + e.message);
        previewDiv.classList.add('hidden');
        submitBtn.classList.add('hidden');
        importedJsonPayload = null;
    }
}

async function handleGenerateUPC() {
    try {
        const res = await fetchWithAuth(`/api/v2/nutrition/generate_upc`);
        if (res.ok) {
            const data = await res.json();
            const newUpc = data.upc;

            // Update Payload
            if (importedJsonPayload && importedJsonPayload.variables) {
                const keys = Object.keys(importedJsonPayload.variables);
                if (keys.length > 0) {
                     importedJsonPayload.variables[keys[0]].metadata.upc = newUpc;
                }
            }

            // Update UI
            const upcSpan = document.getElementById('import-preview-upc');
            if(upcSpan) {
                upcSpan.innerHTML = newUpc;
                upcSpan.style.color = "var(--text-color)";
                upcSpan.style.fontStyle = "normal";
            }

            const btn = document.querySelector('#import-preview-content button');
            if(btn) {
                btn.innerText = "Generated";
                btn.disabled = true;
                btn.classList.remove('btn-secondary');
                btn.classList.add('btn-primary'); // Highlight success
            }

        } else {
            alert("Failed to generate UPC");
        }
    } catch(e) {
        alert("Error generating UPC: " + e.message);
    }
}

async function handleImportJson() {
    if (!importedJsonPayload) return;

    // Force quantity to 0 to prevent logging
    importedJsonPayload.quantity = 0.0;

    try {
        // API_URL is '/api/v1'. I need '/api/v2/nutrition/log'.
        const v2Url = '/api/v2/nutrition/log';

        // 1. Check for existence
        const checkRes = await fetchWithAuth(`${v2Url}?check_existence=true`, {
             method: 'POST',
             headers: { 'Content-Type': 'application/json' },
             body: JSON.stringify(importedJsonPayload)
        });

        if (checkRes.status === 409) {
             const data = await checkRes.json();
             const name = data.food_name || "This food";
             if (!confirm(`${name} already exists. Update it?`)) {
                 return;
             }
        }

        // 2. Execute (Create or Update)
        const res = await fetchWithAuth(v2Url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(importedJsonPayload)
        });

        if (res.ok) {
            alert("Food Imported / Updated Successfully!");
            closeImportJsonModal();
        } else {
            const err = await res.json();
            alert("Import Failed: " + (err.detail || "Unknown error"));
        }

    } catch (e) {
        alert("Import Error: " + e.message);
    }
}

// --- Manage Food Library ---

function openManageLibrary() {
    const modal = document.getElementById('manage-library-modal');
    modal.classList.remove('hidden');
    // Clear list
    document.getElementById('library-list').innerHTML = 'Loading...';
    // Defaults
    document.getElementById('lib-show-hidden').checked = false;
    document.getElementById('lib-search-input').value = '';
    document.getElementById('edit-library-form-container').classList.add('hidden');
    loadLibraryFoods();
}

function closeManageLibrary() {
    document.getElementById('manage-library-modal').classList.add('hidden');
    document.getElementById('edit-library-form-container').classList.add('hidden');
}

let libSearchDebounce;
function debounceLibrarySearch() {
    clearTimeout(libSearchDebounce);
    libSearchDebounce = setTimeout(loadLibraryFoods, 300);
}

async function loadLibraryFoods() {
    const listDiv = document.getElementById('library-list');
    listDiv.innerHTML = 'Loading...';
    const showHidden = document.getElementById('lib-show-hidden').checked;
    const query = document.getElementById('lib-search-input').value;

    try {
        let url = `${API_URL}/nutrition/list?include_hidden=${showHidden}&limit=100`;
        if (query) {
            url += `&search=${encodeURIComponent(query)}`;
        }
        const res = await fetchWithAuth(url);
        const foods = await res.json();

        if (foods.length === 0) {
            listDiv.innerHTML = '<em>No foods found.</em>';
            return;
        }

        let html = '<ul style="list-style: none; padding: 0; max-height: 400px; overflow-y: auto;">';
        foods.forEach(food => {
             const safeFood = JSON.stringify(food).replace(/"/g, '&quot;');
             const visibility = food.is_user_visible ? '<span style="color: green;">Visible</span>' : '<span style="color: gray;">Hidden</span>';
             const safeName = escapeHtml(food.food_name);
             const safeSource = escapeHtml(food.source);

             html += `
             <li style="border-bottom: 1px solid #eee; padding: 8px 0; display: flex; justify-content: space-between; align-items: center;">
                <span>
                    <strong>${safeName}</strong> <small>(${safeSource})</small><br>
                    <small>${Math.round(food.calories)} kcal | ${visibility}</small>
                </span>
                <div>
                    <button onclick="editLibraryFood(${safeFood})" class="btn-secondary" style="font-size: 0.8em; padding: 2px 5px;">Edit</button>
                    <button onclick="deleteLibraryFood(${food.food_id})" class="btn-warning" style="font-size: 0.8em; padding: 2px 5px; background-color: #dc3545;">Del</button>
                </div>
             </li>
             `;
        });
        html += '</ul>';
        listDiv.innerHTML = html;

    } catch (err) {
        listDiv.innerHTML = 'Error loading library.';
    }
}

function editLibraryFood(food) {
    const container = document.getElementById('edit-library-form-container');
    container.classList.remove('hidden');

    document.getElementById('edit_lib_id').value = food.food_id;
    document.getElementById('edit_lib_name').value = food.food_name;
    document.getElementById('edit_lib_barcode').value = food.barcode || '';
    document.getElementById('edit_lib_cals').value = food.calories;
    document.getElementById('edit_lib_protein').value = food.protein;
    document.getElementById('edit_lib_fat').value = food.fat;
    document.getElementById('edit_lib_carbs').value = food.carbs;
    document.getElementById('edit_lib_fiber').value = food.fiber;
    document.getElementById('edit_lib_sodium').value = food.sodium || 0;

    // Extended
    document.getElementById('edit_lib_brand').value = food.brand || '';
    document.getElementById('edit_lib_serving_unit').value = food.serving_size_unit || '';
    document.getElementById('edit_lib_weight_g').value = food.serving_weight_grams || '';
    document.getElementById('edit_lib_volume_ml').value = food.serving_volume_ml || '';
    document.getElementById('edit_lib_cholesterol').value = food.cholesterol || 0;
    document.getElementById('edit_lib_total_sugars').value = food.total_sugars || 0;
    document.getElementById('edit_lib_added_sugars').value = food.added_sugars || 0;
    document.getElementById('edit_lib_vit_d').value = food.vitamin_d || 0;
    document.getElementById('edit_lib_calcium').value = food.calcium || 0;
    document.getElementById('edit_lib_iron').value = food.iron || 0;
    document.getElementById('edit_lib_potassium').value = food.potassium || 0;
    document.getElementById('edit_lib_score').value = food.health_score || '';
    document.getElementById('edit_lib_insight').value = food.health_insight || '';
    document.getElementById('edit_lib_tip').value = food.pairing_tip || '';

    document.getElementById('edit_lib_visible').checked = food.is_user_visible;
}

document.getElementById('edit-library-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('edit_lib_id').value;
    const data = {
        food_name: document.getElementById('edit_lib_name').value,
        barcode: document.getElementById('edit_lib_barcode').value || null,
        calories: parseFloat(document.getElementById('edit_lib_cals').value),
        protein: parseFloat(document.getElementById('edit_lib_protein').value),
        fat: parseFloat(document.getElementById('edit_lib_fat').value),
        carbs: parseFloat(document.getElementById('edit_lib_carbs').value),
        fiber: parseFloat(document.getElementById('edit_lib_fiber').value),
        sodium: parseFloat(document.getElementById('edit_lib_sodium').value),

        // Extended
        brand: document.getElementById('edit_lib_brand').value || null,
        serving_size_unit: document.getElementById('edit_lib_serving_unit').value || null,
        serving_weight_grams: parseFloat(document.getElementById('edit_lib_weight_g').value) || null,
        serving_volume_ml: parseFloat(document.getElementById('edit_lib_volume_ml').value) || null,
        cholesterol: parseFloat(document.getElementById('edit_lib_cholesterol').value) || 0,
        total_sugars: parseFloat(document.getElementById('edit_lib_total_sugars').value) || 0,
        added_sugars: parseFloat(document.getElementById('edit_lib_added_sugars').value) || 0,
        vitamin_d: parseFloat(document.getElementById('edit_lib_vit_d').value) || 0,
        calcium: parseFloat(document.getElementById('edit_lib_calcium').value) || 0,
        iron: parseFloat(document.getElementById('edit_lib_iron').value) || 0,
        potassium: parseFloat(document.getElementById('edit_lib_potassium').value) || 0,
        health_score: document.getElementById('edit_lib_score').value || null,
        health_insight: document.getElementById('edit_lib_insight').value || null,
        pairing_tip: document.getElementById('edit_lib_tip').value || null,

        is_user_visible: document.getElementById('edit_lib_visible').checked
    };

    try {
        const res = await fetchWithAuth(`${API_URL}/nutrition/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        if(res.ok) {
            alert('Food updated');
            document.getElementById('edit-library-form-container').classList.add('hidden');
            loadLibraryFoods();
        } else {
            alert('Update failed');
        }
    } catch(err) {
        alert('Update failed');
    }
});

async function deleteLibraryFood(id) {
    if(!confirm("Are you sure you want to delete this food? If it is used in logs, this might fail or be restricted.")) return;
    try {
        const res = await fetchWithAuth(`${API_URL}/nutrition/${id}`, {
            method: 'DELETE'
        });
        if(res.ok) {
            alert('Food deleted');
            loadLibraryFoods();
            document.getElementById('edit-library-form-container').classList.add('hidden');
        } else {
            const err = await res.json();
            alert(err.detail || 'Delete failed');
        }
    } catch(err) {
        alert('Delete failed');
    }
}

function deleteLibraryFoodCurrent() {
    const id = document.getElementById('edit_lib_id').value;
    if(id) deleteLibraryFood(id);
}


// --- Manage Food Logs ---

async function openManageFoodModal() {
    const modal = document.getElementById('manage-food-modal');
    modal.classList.remove('hidden');
    loadManageFoodList();
}

function closeManageFoodModal() {
    document.getElementById('manage-food-modal').classList.add('hidden');
    document.getElementById('edit-food-form-container').classList.add('hidden');
    loadSummary();
}

async function loadManageFoodList() {
    const listDiv = document.getElementById('manage-food-list');
    listDiv.innerHTML = 'Loading...';
    try {
        const dateStr = getFormattedDate(currentDashboardDate);
        const res = await fetchWithAuth(`${API_URL}/log/summary?date_str=${dateStr}`);
        const data = await res.json();
        const logs = data.food_logs;

        if (!logs || logs.length === 0) {
            listDiv.innerHTML = '<em>No logs.</em>';
            return;
        }

        let html = '<ul style="list-style: none; padding: 0;">';
        logs.forEach(log => {
             const safeLog = JSON.stringify(log).replace(/"/g, '&quot;');
             html += `
             <li style="border-bottom: 1px solid #eee; padding: 8px 0; display: flex; justify-content: space-between; align-items: center;">
                <span>
                    <strong>${log.name}</strong> (${log.meal})<br>
                    <small>${Math.round(log.calories)} kcal</small>
                </span>
                <div>
                    <button onclick="editFoodLog(${safeLog})" class="btn-secondary" style="font-size: 0.8em; padding: 2px 5px;">Edit</button>
                    <button onclick="deleteFoodLog(${log.log_id})" class="btn-warning" style="font-size: 0.8em; padding: 2px 5px;">Del</button>
                </div>
             </li>
             `;
        });
        html += '</ul>';
        listDiv.innerHTML = html;

    } catch (err) {
        listDiv.innerHTML = 'Error loading logs.';
    }
}

async function deleteFoodLog(id) {
    if(!confirm("Are you sure?")) return;
    try {
        const res = await fetchWithAuth(`${API_URL}/log/food/${id}`, {
            method: 'DELETE'
        });
        if(res.ok) {
            // Refresh logic: check where we are
            if(document.getElementById('manage-food-modal') && !document.getElementById('manage-food-modal').classList.contains('hidden')) {
                loadManageFoodList();
            } else if(document.getElementById('nutrition-view-planner') && !document.getElementById('nutrition-view-planner').classList.contains('hidden')) {
                loadPlanner();
            } else if(document.getElementById('tab-dashboard') && !document.getElementById('tab-dashboard').classList.contains('hidden')) {
                loadSummary();
            }
        }
        else alert("Delete failed");
    } catch(err) { alert("Delete failed"); }
}

function editFoodLog(log) {
    const container = document.getElementById('edit-food-form-container');
    container.classList.remove('hidden');
    document.getElementById('edit_food_log_id').value = log.log_id;
    // Calculate effective quantity (Total Servings)
    const effectiveQty = (log.quantity || 0) * (log.serving_size || 1);
    document.getElementById('edit_food_quantity').value = effectiveQty;
    // Display unit if available
    const unitEl = document.getElementById('edit_food_unit_display');
    if (log.unit) unitEl.innerText = `(${log.unit})`;
    else unitEl.innerText = '(1)';

    document.getElementById('edit_food_meal').value = log.meal;

    // Timestamp handling (Same issue as exercise, need to patch backend)
    if (log.timestamp) {
        const dt = new Date(log.timestamp);
        const localIso = new Date(dt.getTime() - (dt.getTimezoneOffset() * 60000)).toISOString().slice(0, 19);
        document.getElementById('edit_food_time').value = localIso;
    } else {
        const d = new Date(currentDashboardDate);
        d.setHours(12, 0, 0);
        const localIso = new Date(d.getTime() - (d.getTimezoneOffset() * 60000)).toISOString().slice(0, 19);
        document.getElementById('edit_food_time').value = localIso;
    }
}

document.getElementById('edit-food-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = document.getElementById('edit_food_log_id').value;
    const timeVal = document.getElementById('edit_food_time').value;
    const isoStr = new Date(timeVal).toISOString();

    const updates = {
        timestamp: isoStr,
        quantity: parseFloat(document.getElementById('edit_food_quantity').value),
        serving_size: 1.0,
        meal_id: document.getElementById('edit_food_meal').value
    };

    try {
         const res = await fetchWithAuth(`${API_URL}/log/food/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(updates)
        });
        if(res.ok) {
            document.getElementById('edit-food-form-container').classList.add('hidden');
            loadManageFoodList();
        } else alert("Update failed");
    } catch(e) { alert("Update failed"); }
});

// --- Recipes Logic ---

function handleScopeChange(val) {
    currentScope = val;
    const input = document.getElementById('food-search-input');
    if (val === 'recipe') {
        input.placeholder = "Type to search recipes...";
    } else {
        input.placeholder = "Type to search foods...";
    }
    document.getElementById('food-search-results').classList.add('hidden');
    document.getElementById('log-unit-display').innerText = '1';
    input.value = '';
}

function showNutritionView(view, preserveMode = false) {
    document.getElementById('nutrition-view-log').classList.add('hidden');
    document.getElementById('nutrition-view-recipes').classList.add('hidden');
    document.getElementById('nutrition-view-planner').classList.add('hidden');

    if (view === 'log') {
        if (!preserveMode) isPlanningMode = false;
        document.getElementById('nutrition-view-log').classList.remove('hidden');
        updateLogViewUI();
    } else if (view === 'recipes') {
        document.getElementById('nutrition-view-recipes').classList.remove('hidden');
        loadRecipes();
    } else if (view === 'planner') {
        document.getElementById('nutrition-view-planner').classList.remove('hidden');
        loadPlanner();
    }
}

function updateLogViewUI() {
    const btn = document.querySelector('#food-log-form button[type="submit"]');
    const title = document.querySelector('#nutrition-view-log h3');

    if (isPlanningMode) {
        if(btn) btn.innerText = "Add to Plan";
        if(title) title.innerText = "Add to Meal Plan";
        // Maybe highlight the Meal dropdown or lock it?
        // document.getElementById('food-meal').style.border = "2px solid var(--primary-color)";
    } else {
        if(btn) btn.innerText = "Log Food";
        if(title) title.innerText = "Log Food";
    }
}

async function loadRecipes() {
    const div = document.getElementById('recipe-list');
    div.innerHTML = 'Loading...';
    try {
        const res = await fetchWithAuth(`${API_URL}/recipes/`);
        const recipes = await res.json();

        if (recipes.length === 0) {
            div.innerHTML = '<em>No recipes found.</em>';
            return;
        }

        div.innerHTML = '';
        recipes.forEach(r => {
             // Safe JSON for onclick
             const safeR = JSON.stringify(r).replace(/"/g, '&quot;');
             const card = document.createElement('div');
             card.className = 'card';
             card.style.marginBottom = '10px';

             // current_food might be loaded if schema includes it
             const cals = r.current_food ? Math.round(r.current_food.calories) : '?';

             card.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3>${escapeHtml(r.name)}</h3>
                    <div>
                        <button class="btn-secondary" onclick="printRecipe(${r.recipe_id})">Print</button>
                        <button class="btn-secondary" onclick="openRecipeModal(${safeR})">Edit</button>
                        <button class="btn-warning" onclick="deleteRecipe(${r.recipe_id})" style="background-color: #dc3545;">Delete</button>
                    </div>
                </div>
                <p>
                    <strong>Servings:</strong> ${r.total_servings} |
                    <strong>Calories:</strong> ${cals} / serving
                </p>
                <p><em>${escapeHtml(r.instructions) || 'No instructions'}</em></p>
             `;
             div.appendChild(card);
        });

    } catch(e) {
        div.innerHTML = 'Error loading recipes';
        console.error(e);
    }
}

async function deleteRecipe(id) {
    if(!confirm("Are you sure? This will hide the recipe from your list, but history remains.")) return;
    try {
        const res = await fetchWithAuth(`${API_URL}/recipes/${id}`, { method: 'DELETE' });
        if(res.ok) loadRecipes();
        else alert("Delete failed");
    } catch(e) { alert("Delete failed"); }
}

function openRecipeModal(recipe = null) {
    document.getElementById('recipe-modal').classList.remove('hidden');
    const form = document.getElementById('recipe-form');
    form.reset();
    document.getElementById('recipe-ing-results').classList.add('hidden');

    currentRecipeIngredients = [];

    if(recipe) {
        document.getElementById('recipe-modal-title').innerText = 'Edit Recipe';
        document.getElementById('recipe_id').value = recipe.recipe_id;
        document.getElementById('recipe_name').value = recipe.name;
        document.getElementById('recipe_servings').value = recipe.total_servings;
        document.getElementById('recipe_instructions').value = recipe.instructions || '';
        document.getElementById('recipe_prep_time').value = recipe.prep_time_minutes || '';
        document.getElementById('recipe_cook_time').value = recipe.cook_time_minutes || '';

        // Populate overrides from current_food if available
        if(recipe.current_food) {
            document.getElementById('recipe_score').value = recipe.current_food.health_score || '';
            document.getElementById('recipe_insight').value = recipe.current_food.health_insight || '';
            document.getElementById('recipe_tip').value = recipe.current_food.pairing_tip || '';
        }

        // Load Ingredients
        if(recipe.ingredients) {
            recipe.ingredients.forEach(ing => {
                // Flatten for internal use
                currentRecipeIngredients.push({
                    food_id: ing.food.food_id,
                    food_name: ing.food.food_name,
                    calories: ing.food.calories,
                    serving_volume_ml: ing.food.serving_volume_ml, // Need this for conversion
                    quantity: ing.quantity,
                    unit: ing.unit || 'serving'
                });
            });
        }
    } else {
        document.getElementById('recipe-modal-title').innerText = 'Create Recipe';
        document.getElementById('recipe_id').value = '';
        document.getElementById('recipe_servings').value = 1;
    }
    renderRecipeIngredients();
}

function closeRecipeModal() {
    document.getElementById('recipe-modal').classList.add('hidden');
}

async function handleSearchRecipeIngredient(query) {
    const resultsDiv = document.getElementById('recipe-ing-results');
    if (!query || query.length < 2) {
        resultsDiv.classList.add('hidden');
        return;
    }

    try {
        // Always search Scope=Food here (ingredients)
        const res = await fetchWithAuth(`${API_URL}/nutrition/search?query=${encodeURIComponent(query)}&scope=food`);
        const foods = await res.json();

        resultsDiv.innerHTML = '';
        if (foods.length > 0) {
            resultsDiv.classList.remove('hidden');
            // Removed inline styles to allow CSS variables (dark mode) to take effect
            // Re-adding essential structural styles via CSS class or ensuring they are in .search-results
            resultsDiv.style.maxHeight = '200px';
            resultsDiv.style.overflowY = 'auto';
            // Explicitly reset background/border to empty to inherit from CSS class
            resultsDiv.style.backgroundColor = '';
            resultsDiv.style.border = '';

            foods.forEach(food => {
                const div = document.createElement('div');
                div.className = 'search-item'; // reuse class
                div.innerText = `${food.food_name} (${Math.round(food.calories)} kcal)`;
                div.onclick = () => addIngredientToRecipe(food);
                resultsDiv.appendChild(div);
            });
        } else {
            resultsDiv.classList.add('hidden');
        }

    } catch(err) {
        console.error(err);
    }
}

function addIngredientToRecipe(food) {
    // Check if exists? Maybe allow dupes? Let's allow dupes, users might add same item twice.
    currentRecipeIngredients.push({
        food_id: food.food_id,
        food_name: food.food_name,
        calories: food.calories,
        serving_volume_ml: food.serving_volume_ml,
        quantity: 1.0, // Default
        unit: 'serving'
    });

    document.getElementById('recipe-ing-search').value = '';
    document.getElementById('recipe-ing-results').classList.add('hidden');
    renderRecipeIngredients();
}

function removeIngredient(index) {
    currentRecipeIngredients.splice(index, 1);
    renderRecipeIngredients();
}

function updateIngredientQty(index, val) {
    const qty = parseFloat(val) || 0;
    currentRecipeIngredients[index].quantity = qty;
    renderRecipeIngredients(); // Re-calc totals
}

function renderRecipeIngredients() {
    const tbody = document.getElementById('recipe-ing-body');
    tbody.innerHTML = '';

    let totalCals = 0;

    currentRecipeIngredients.forEach((ing, idx) => {
        // Calculate Calories
        let multiplier = ing.quantity;
        if (ing.unit && ing.unit !== 'serving' && UNIT_CONVERSIONS[ing.unit] && ing.serving_volume_ml > 0) {
             const ml = ing.quantity * UNIT_CONVERSIONS[ing.unit];
             multiplier = ml / ing.serving_volume_ml;
        }

        const rowCals = ing.calories * multiplier;
        totalCals += rowCals;

        // Unit Display
        let unitDisplay = ing.unit || 'serving';
        let otherAction = '';
        if (ing.serving_volume_ml && ing.serving_volume_ml > 0) {
            otherAction = `<a href="#" onclick="openUnitSelector(${idx}); return false;" style="margin-left:5px; font-size:0.8em;">[Other]</a>`;
        }

        const row = document.createElement('tr');
        row.innerHTML = `
            <td>${escapeHtml(ing.food_name)}</td>
            <td>
                <div style="display: flex; align-items: center;">
                    <input type="number" step="0.1" value="${ing.quantity}" style="width: 60px; margin-right: 5px;" onchange="updateIngredientQty(${idx}, this.value)">
                    <span style="font-size: 0.9em; margin-right: 5px;">${unitDisplay}</span>
                    ${otherAction}
                </div>
            </td>
            <td>${Math.round(rowCals)}</td>
            <td>
                <button type="button" onclick="removeIngredient(${idx})" style="color: red; border: none; background: none; cursor: pointer;">&times;</button>
            </td>
        `;
        tbody.appendChild(row);
    });

    const servings = parseFloat(document.getElementById('recipe_servings').value) || 1;
    document.getElementById('recipe-total-cals').innerText = Math.round(totalCals);
    document.getElementById('recipe-serving-cals').innerText = Math.round(totalCals / servings);
}

function openUnitSelector(index) {
    currentEditingIngredientIndex = index;
    document.getElementById('unit-selection-modal').classList.remove('hidden');
}

function closeUnitSelector() {
    document.getElementById('unit-selection-modal').classList.add('hidden');
    currentEditingIngredientIndex = -1;
}

function selectUnit(unit) {
    if (currentEditingIngredientIndex === -1) return;
    currentRecipeIngredients[currentEditingIngredientIndex].unit = unit;
    renderRecipeIngredients();
    closeUnitSelector();
}

function calculateRecipeTotals() {
    // Just trigger render to update numbers based on servings change
    renderRecipeIngredients();
}

async function handleSaveRecipe(e) {
    e.preventDefault();

    const id = document.getElementById('recipe_id').value;
    const data = {
        name: document.getElementById('recipe_name').value,
        total_servings: parseFloat(document.getElementById('recipe_servings').value),
        instructions: document.getElementById('recipe_instructions').value,
        prep_time_minutes: parseInt(document.getElementById('recipe_prep_time').value) || null,
        cook_time_minutes: parseInt(document.getElementById('recipe_cook_time').value) || null,

        ingredients: currentRecipeIngredients.map(ing => ({
            food_id: ing.food_id,
            quantity: ing.quantity,
            unit: ing.unit
        })),

        health_score: document.getElementById('recipe_score').value || null,
        health_insight: document.getElementById('recipe_insight').value || null,
        pairing_tip: document.getElementById('recipe_tip').value || null
    };

    if (data.ingredients.length === 0) {
        alert("Please add at least one ingredient.");
        return;
    }

    try {
        let url = `${API_URL}/recipes/`;
        let method = 'POST';
        if (id) {
            url = `${API_URL}/recipes/${id}`;
            method = 'PUT';
        }

        const res = await fetchWithAuth(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        if (res.ok) {
            alert('Recipe saved!');
            closeRecipeModal();
            loadRecipes();
        } else {
            const err = await res.json();
            alert(err.detail || 'Error saving recipe');
        }
    } catch(e) {
        alert('Error saving recipe');
    }
}

async function printRecipe(id) {
    try {
        // Fetch full recipe details (to ensure we have everything, though we might have it in list)
        // But loadRecipes() list items usually have all data.
        // Let's re-fetch to be safe and clean.
        const res = await fetchWithAuth(`${API_URL}/recipes/${id}`);
        if(!res.ok) throw new Error("Failed to load recipe");
        const recipe = await res.json();
        const food = recipe.current_food || {};

        // Open window
        const win = window.open('', '_blank', 'width=800,height=900');

        // Render Nutrition Label (Static HTML generation similar to modal)
        // We'll hardcode the styles for the label to ensure it prints well without dependencies
        const labelHTML = `
            <div style="border: 2px solid black; padding: 10px; font-family: Helvetica, Arial, sans-serif; max-width: 350px; margin: 20px 0;">
                <h1 style="border-bottom: 10px solid black; margin: 0 0 5px 0; font-size: 2em; line-height: 1;">Nutrition Facts</h1>
                <div style="font-size: 1.1em; font-weight: bold; border-bottom: 5px solid black; padding-bottom: 5px;">
                    Serving Size ${food.serving_size_unit || '1 serving'}
                </div>
                <div style="border-bottom: 5px solid black; padding: 5px 0;">
                    <div style="font-weight: bold; font-size: 0.8em;">Amount Per Serving</div>
                    <div style="font-size: 2em; font-weight: 900; line-height: 1;">Calories <span style="float: right;">${Math.round(food.calories)}</span></div>
                </div>
                <div style="border-bottom: 1px solid black; padding: 3px 0;">
                    <strong>Total Fat</strong> ${food.fat}g
                </div>
                <div style="border-bottom: 1px solid black; padding: 3px 0; padding-left: 20px;">
                    Cholesterol ${food.cholesterol || 0}mg
                </div>
                <div style="border-bottom: 1px solid black; padding: 3px 0;">
                    <strong>Sodium</strong> ${food.sodium || 0}mg
                </div>
                <div style="border-bottom: 1px solid black; padding: 3px 0;">
                    <strong>Total Carbohydrate</strong> ${food.carbs}g
                </div>
                <div style="border-bottom: 1px solid black; padding: 3px 0; padding-left: 20px;">
                    Dietary Fiber ${food.fiber}g
                </div>
                <div style="border-bottom: 1px solid black; padding: 3px 0; padding-left: 20px;">
                    Total Sugars ${food.total_sugars || 0}g
                </div>
                <div style="border-bottom: 5px solid black; padding: 3px 0;">
                    <strong>Protein</strong> ${food.protein}g
                </div>
            </div>
        `;

        // Ingredients Table
        let ingTable = `<table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
            <thead><tr style="background: #eee;"><th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Ingredient</th><th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Quantity</th></tr></thead><tbody>`;
        if (recipe.ingredients) {
            recipe.ingredients.forEach(ing => {
                const unit = ing.unit || 'serving';
                ingTable += `<tr><td style="border: 1px solid #ddd; padding: 8px;">${ing.food.food_name}</td><td style="border: 1px solid #ddd; padding: 8px;">${ing.quantity} ${unit}</td></tr>`;
            });
        }
        ingTable += `</tbody></table>`;

        // Page Content
        const content = `
            <!DOCTYPE html>
            <html>
            <head>
                <title>Print Recipe - ${escapeHtml(recipe.name)}</title>
                <style>
                    body { font-family: sans-serif; padding: 40px; color: #333; }
                    h1 { border-bottom: 2px solid #ccc; padding-bottom: 10px; }
                    .meta { margin-bottom: 20px; font-size: 1.1em; color: #555; }
                    .section-title { margin-top: 30px; border-bottom: 1px solid #eee; padding-bottom: 5px; color: var(--primary-color, #007bff); }
                    .instructions { white-space: pre-wrap; line-height: 1.6; }

                    /* Print Button Styling */
                    .print-btn-container { text-align: right; margin-bottom: 20px; }
                    .print-btn { background-color: #007bff; color: white; padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-size: 1em; font-weight: bold; }
                    .print-btn:hover { background-color: #0056b3; }

                    @media print {
                        .no-print { display: none !important; }
                        body { padding: 0; }
                    }
                </style>
            </head>
            <body>
                <div class="print-btn-container no-print">
                    <button class="print-btn" onclick="window.print()">Print this page</button>
                </div>

                <h1>${escapeHtml(recipe.name)}</h1>
                <div class="meta">
                    <strong>Servings:</strong> ${recipe.total_servings} <br>
                    <strong>Prep Time:</strong> ${recipe.prep_time_minutes || '--'} min | <strong>Cook Time:</strong> ${recipe.cook_time_minutes || '--'} min
                </div>

                ${labelHTML}

                <h2 class="section-title">Ingredients</h2>
                ${ingTable}

                <h2 class="section-title">Instructions</h2>
                <div class="instructions">${escapeHtml(recipe.instructions) || 'No instructions provided.'}</div>
            </body>
            </html>
        `;

        win.document.write(content);
        win.document.close();

    } catch(e) {
        alert("Error printing recipe: " + e.message);
    }
}

// --- Mobile Menu ---

function toggleMobileMenu() {
    const overlay = document.getElementById('mobile-menu-overlay');
    overlay.classList.toggle('hidden');
}

function mobileMenuGo(tab) {
    toggleMobileMenu();
    showTab(tab);
}

// --- Meal Planner Logic ---

function changePlannerDate(offset) {
    currentPlannerDate.setDate(currentPlannerDate.getDate() + offset);
    loadPlanner();
}

function updatePlannerDateDisplay() {
    const options = { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' };
    document.getElementById('planner-date-display').innerText = currentPlannerDate.toLocaleDateString(undefined, options);
}

async function loadPlanner() {
    updatePlannerDateDisplay();
    // Use summary endpoint to get food logs
    // Summary endpoint returns { food_logs: [...] }
    // food_logs now include planned_quantity

    try {
        const dateStr = getFormattedDate(currentPlannerDate);
        const res = await fetchWithAuth(`${API_URL}/log/summary?date_str=${dateStr}`);
        const data = await res.json();

        // Store for gauge updates
        plannerLogs = data.food_logs || [];

        // Also need base nutrition info for gauge calculations?
        // summaryData from dashboard has pre-calculated macros for EATEN items.
        // But for Planner, we need to calculate ourselves based on the toggle.
        // food_logs items have: name, calories, meal, serving_size, quantity, planned_quantity, unit.
        // They DON'T have raw macros (protein, fat, etc) in the summary response yet?
        // Wait, 'get_daily_summary' in health.py:
        /*
        food_list.append({
            "log_id": log.item_log_id,
            "name": log.nutrition_info.food_name,
            "calories": (log.nutrition_info.calories or 0) * multiplier,
            "meal": log.meal_id,
            "serving_size": log.serving_size,
            "quantity": log.quantity,
            "planned_quantity": log.planned_quantity,
            "unit": log.nutrition_info.serving_size_unit,
            "timestamp": ts
        })
        */
        // It returns calculated calories, but NOT protein/fat/carbs for individual items.
        // This is a problem for the Gauges if we want to show Macros.
        // The gauges on dashboard use 'macros' object which is pre-summed by backend.
        // But that pre-sum is only for EATEN items.
        // If I want to show Planned Macros, I need the macro data in the list.

        // NOTE: I should have updated the backend to include macros in food_logs list.
        // I missed that in the plan.
        // For now, I can only accurately show Calories in the Planner Gauges unless I fetch more data.
        // Or I can update the backend quickly.
        // The user requirement said "It will show the same gauges featured on the daily summary."
        // So I need macros.

        // I'll stick to rendering the planner list first, and maybe show just calories or 0 for others
        // if I can't fix backend now without going back.
        // Actually, I can use 'read_file' to check if I can easily patch health.py again.
        // Yes, I can. But let's finish app.js first with what we have.
        // I will display Calories Gauge accurately. Others might be 0 or I'll assume standard distribution? No that's bad.
        // I will assume for now we only show Calories or accept that macros might be missing for Planned items unless I fix backend.
        // Let's implement the list rendering.

        renderPlanner();
        updatePlannerGauges();

    } catch(err) {
        console.error("Planner load error", err);
    }
}

function renderPlanner() {
    const meals = ['Breakfast', 'Lunch', 'Dinner', 'Snack'];

    meals.forEach(meal => {
        const listDiv = document.getElementById(`planner-list-${meal}`);
        if(!listDiv) return;

        const items = plannerLogs.filter(l => l.meal === meal);
        if(items.length === 0) {
            listDiv.innerHTML = '<div style="color:#888; font-style:italic; padding:10px;">No items planned.</div>';
            return;
        }

        let html = '<ul style="list-style:none; padding:0; margin:0;">';
        items.forEach(item => {
            const isEaten = item.quantity > 0;
            const isPlanned = item.quantity === 0 && item.planned_quantity > 0;

            // If neither (both 0), maybe deleted or weird state. Skip.
            if(!isEaten && !isPlanned) return;

            // Display Logic
            // If Eaten: Show "Quantity: X (Eaten)"
            // If Planned: Show "Planned: Y" and a [Log] button/checkbox.

            // Calculate Calories to show
            // item.calories is calculated based on quantity * serving_size in backend.
            // But if quantity is 0, backend calculated 0 calories.
            // We need to calc calories for planned item?
            // Problem: Backend returned 'calories' = (log.nutrition_info.calories) * multiplier.
            // If multiplier (quantity) is 0, calories is 0.
            // So for Planned items, I don't have the calorie count!
            // I need to update backend to send per-serving calories or something.
            // Wait, I can't do the gauges OR the list display properly without this.

            // CRITICAL: I must update backend 'get_daily_summary' to return 'calories_per_serving' or similar.
            // Or calc it if I have unit info? No.

            // WORKAROUND: In backend 'get_daily_summary', I can modify the calculation logic?
            // No, better to expose 'calories_per_serving' in the response.
            // Or 'nutrition_info' object.

            let displayCals = Math.round(item.calories);
            // If planned and not eaten, item.calories is 0.
            // We can't show it.

            html += `<li style="padding: 10px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>${escapeHtml(item.name)}</strong>
                    <br>
                    ${renderPlannerItemDetails(item)}
                </div>
                <div>
                    ${renderPlannerItemActions(item)}
                </div>
            </li>`;
        });
        html += '</ul>';
        listDiv.innerHTML = html;
    });
}

function renderPlannerItemDetails(item) {
    if (item.quantity > 0) {
        return `<span style="color:green;">Eaten: ${item.quantity} ${item.unit || ''} (${Math.round(item.calories)} kcal)</span>`;
    } else {
        // Backend now returns calories for planned items too
        return `<span style="color:#d35400;">Planned: ${item.planned_quantity} ${item.unit || ''} (${Math.round(item.calories)} kcal)</span>`;
    }
}

function renderPlannerItemActions(item) {
    if (item.quantity === 0 && item.planned_quantity > 0) {
        return `
            <button class="btn-primary" style="font-size:0.8em; padding: 4px 8px;" onclick="commitPlanItem(${item.log_id})">Log</button>
            <button class="btn-warning" style="font-size:0.8em; padding: 4px 8px; margin-left: 5px; background-color: #dc3545;" onclick="deleteFoodLog(${item.log_id})">Del</button>
        `;
    }
    return ''; // Already eaten
}

function openPlannerAdd(meal) {
    isPlanningMode = true;
    // We pass true to preserveMode to avoid flickering
    showNutritionView('log', true);

    document.getElementById('food-meal').value = meal;

    // Ensure UI is updated (though showNutritionView calls it, we force isPlanningMode first)
    // Actually showNutritionView handles it.
    updateLogViewUI();
}

async function commitPlanItem(logId, quantityOverride = null) {
    // Try to find item in plannerLogs first, if not try summaryData (dashboard context)
    let item = plannerLogs.find(l => l.log_id === logId);
    if (!item && summaryData && summaryData.food_logs) {
        item = summaryData.food_logs.find(l => l.log_id === logId);
    }

    let quantity = quantityOverride;
    if (quantity === null && item) {
        // Fallback to existing quantity if override not present (though normally passed by confirmLogFood)
        quantity = item.quantity > 0 ? item.quantity : item.planned_quantity;
    }

    if (quantity === null) {
        alert("Cannot determine quantity to log.");
        return;
    }

    const updates = {
        quantity: quantity
        // timestamp: depends on context
    };

    // If it was purely a planned item (quantity=0), we update timestamp to NOW (logging it as eaten now).
    // If it was already eaten (quantity > 0), we preserve timestamp (editing an old entry).
    // If we can't determine (no item found), we assume it's a new log/plan commit => update timestamp.
    if (!item || item.quantity === 0) {
        updates.timestamp = new Date().toISOString();
    }

    try {
        const res = await fetchWithAuth(`${API_URL}/log/food/${logId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updates)
        });
        if(res.ok) {
            // Refresh wherever we are
            if(document.getElementById('nutrition-view-planner') && !document.getElementById('nutrition-view-planner').classList.contains('hidden')) {
                loadPlanner();
            }
        } else {
            alert("Failed to log item");
        }
    } catch(e) {
        alert("Failed to log item");
    }
}

function updatePlannerGauges() {
    // Determine mode
    const mode = document.querySelector('input[name="planner_mode"]:checked').value;

    // Calculate Totals
    const totals = { calories: 0, protein: 0, fat: 0, carbs: 0, fiber: 0, sodium: 0 };

    if (plannerLogs) {
        plannerLogs.forEach(item => {
            const isEaten = item.quantity > 0;
            const isPlanned = item.quantity === 0 && item.planned_quantity > 0;

            let include = false;
            if (mode === 'today') {
                include = true;
            } else if (mode === 'future') {
                include = isPlanned;
            }

            if (include) {
                totals.calories += item.calories || 0;
                totals.protein += item.protein || 0;
                totals.fat += item.fat || 0;
                totals.carbs += item.carbs || 0;
                totals.fiber += item.fiber || 0;
                totals.sodium += item.sodium || 0;
            }
        });
    }

    const gaugeData = {
        calories_consumed: totals.calories,
        macros: {
            protein: totals.protein,
            fat: totals.fat,
            carbs: totals.carbs,
            fiber: totals.fiber,
            sodium: totals.sodium
        }
    };

    renderGauges(gaugeData, calculateTargets(), 'planner-gauges-container');
}
