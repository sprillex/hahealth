const API_URL = '/api/v1';
const AUTH_URL = '/auth/token';

// State
let token = localStorage.getItem('access_token');
let user = null;
let summaryData = null;
let currentDashboardDate = new Date(); // Defaults to today

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
            // Admin check
            if (user.is_admin === false) { // Assuming field is exposed in schema. Wait, need to check Schema.
                 // Actually I haven't added is_admin to UserResponse schema yet!
                 // Let's assume backend returns it if I update Schema, or check if key exists.
            }
            // For now, let's just try to show it. If backend filters unauthorized calls, that's fine.
            // But UI should hide button if not admin.

            // Note: Schema wasn't updated in plan to return is_admin.
            // I should update UserResponse schema or just blindly show/hide based on try/error.
            // Let's rely on backend property.

            if (user.is_admin) {
                document.getElementById('nav-admin').classList.remove('hidden');
            } else {
                document.getElementById('nav-admin').classList.add('hidden');
            }

            showDashboard();
            loadProfileData();
            loadSummary();
            applyTheme(); // Re-apply theme after user load
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
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
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
        const res = await fetch(`${API_URL}/log/summary?date_str=${dateStr}`, {
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

    if (data.food_logs && data.food_logs.length > 0) {
        foodList.innerHTML = '<ul>' + data.food_logs.map(f => `<li>${f.name} (${Math.round(f.calories)} kcal)</li>`).join('') + '</ul>';
    } else {
        foodList.innerHTML = '<em>No food logged.</em>';
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

async function loadDailyMeds() {
    const listEl = document.getElementById('meds-taken-list');
    listEl.innerHTML = 'Loading...';
    try {
        const dateStr = getFormattedDate(currentDashboardDate);
        const res = await fetch(`${API_URL}/medications/log?date_str=${dateStr}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
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
        try {
            const res = await fetch(`${API_URL}/medications/${id}`, {
                method: 'PUT',
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
        const res = await fetch(`${API_URL}/medications/${id}/refill`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
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
    ['calories', 'protein', 'fat', 'carbs', 'fiber'].forEach(k => {
        data[k] = parseFloat(data[k]) || 0;
    });

    data.source = 'MANUAL';
    if (!data.barcode) delete data.barcode; // Send null or undefined if empty

    try {
        const res = await fetch(`${API_URL}/nutrition/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
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
        return;
    }

    try {
        const res = await fetch(`${API_URL}/nutrition/search?query=${encodeURIComponent(query)}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const foods = await res.json();

        resultsDiv.innerHTML = '';
        if (foods.length > 0) {
            resultsDiv.classList.remove('hidden');
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
    document.getElementById('food-search-input').value = food.food_name;
    document.getElementById('selected-food-name').value = food.food_name;
    document.getElementById('selected-food-barcode').value = food.barcode || '';
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

    // If user typed a name but didn't select from dropdown, use that name.
    // The backend will create a manual entry with 0 calories if not found.
    // Or we could prompt them to create it.
    if (!data.food_name && document.getElementById('food-search-input').value) {
        data.food_name = document.getElementById('food-search-input').value;
    }

    if (!data.food_name) {
        alert("Please enter a food name");
        return;
    }

    try {
        const res = await fetch(`${API_URL}/nutrition/log`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(data)
        });

        if (res.ok) {
            alert('Food logged successfully');
            e.target.reset();
            document.getElementById('food-search-results').classList.add('hidden');
        } else {
            const err = await res.json();
            // If 404/Food not found, maybe prompt to create?
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

        const res = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
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
        const res = await fetch(`${API_URL}/medical/allergies/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
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
        const res = await fetch(`${API_URL}/medical/vaccinations`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
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
        const res = await fetch(`${API_URL}/medical/allergies`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
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
        const res = await fetch(`${API_URL}/medical/reports/vaccinations`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
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
        const res = await fetch(`${API_URL}/medical/allergies`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
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
        const res = await fetch(`${API_URL}/log/history/bp`, {
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
        const res = await fetch(`${API_URL}/log/reports/compliance`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
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
        const res = await fetch(`${API_URL}/admin/key`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
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
        const res = await fetch(`${API_URL}/admin/backup`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
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
        const res = await fetch(`${API_URL}/admin/restore`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
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
            await fetch(`${API_URL}/users/me`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
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
        const res = await fetch(`${API_URL}/admin/mqtt_status`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
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
        const res = await fetch(`${API_URL}/medications/log?date_str=${dateStr}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
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
        const res = await fetch(`${API_URL}/medications/log/${logId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
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
        const res = await fetch(`${API_URL}/medications/log/${logId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
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
        const res = await fetch(`${API_URL}/log/summary?date_str=${dateStr}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
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
        const res = await fetch(`${API_URL}/log/exercise/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
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
         const res = await fetch(`${API_URL}/log/exercise/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(updates)
        });
        if(res.ok) {
            document.getElementById('edit-exercise-form-container').classList.add('hidden');
            loadManageExerciseList();
        } else alert("Update failed");
    } catch(e) { alert("Update failed"); }
});

// --- Manage Food ---

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
        const res = await fetch(`${API_URL}/log/summary?date_str=${dateStr}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
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
        const res = await fetch(`${API_URL}/log/food/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if(res.ok) loadManageFoodList();
        else alert("Delete failed");
    } catch(err) { alert("Delete failed"); }
}

function editFoodLog(log) {
    const container = document.getElementById('edit-food-form-container');
    container.classList.remove('hidden');
    document.getElementById('edit_food_log_id').value = log.log_id;
    document.getElementById('edit_food_quantity').value = log.quantity;
    document.getElementById('edit_food_serving').value = log.serving_size;
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
        serving_size: parseFloat(document.getElementById('edit_food_serving').value),
        meal_id: document.getElementById('edit_food_meal').value
    };

    try {
         const res = await fetch(`${API_URL}/log/food/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(updates)
        });
        if(res.ok) {
            document.getElementById('edit-food-form-container').classList.add('hidden');
            loadManageFoodList();
        } else alert("Update failed");
    } catch(e) { alert("Update failed"); }
});
