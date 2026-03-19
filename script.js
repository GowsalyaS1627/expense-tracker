// 1. Storage Keys
const STORAGE_KEY = 'sw_user_email'; // Unga HTML-la irukira key
const DATA_KEY = 'sw_data';
const USER_DB = 'sw_accounts';

// Global variables
let currentUser = localStorage.getItem(STORAGE_KEY);
let allTxs = JSON.parse(localStorage.getItem(DATA_KEY)) || [];
let users = JSON.parse(localStorage.getItem(USER_DB)) || {};
let currentFilter = 'all';
let currentPeriod = new Date();

// 2. Navigation Guard
window.onload = () => {
    if (currentUser && users[currentUser]) {
        showPage('dashboard-page');
    } else {
        showPage('auth-page');
    }
    // Date-ai inaiku date-ku set panroam
    const dateInput = document.getElementById('date-input');
    if(dateInput) dateInput.valueAsDate = new Date();
};

// 3. Page Switcher
function showPage(id) {
    document.querySelectorAll('section').forEach(s => s.classList.add('hidden'));
    const target = document.getElementById(id);
    if (target) target.classList.remove('hidden');
    
    if (id === 'dashboard-page') {
        refreshDashboard();
    }
}

// 4. Save Entry to Python Backend (And LocalStorage)
async function saveEntry() {
    // Unga HTML-la irukira sariyaana IDs
    const note = document.getElementById('note-input').value;
    const amt = document.getElementById('amt-input').value;
    const cat = document.getElementById('cat-input').value;
    const date = document.getElementById('date-input').value;

    if (!amt || !date) return alert("Please fill amount and date!");

    const payload = {
        user: currentUser,
        note: note || "No description",
        amt: parseFloat(amt),
        cat: cat,
        date: date
    };

    try {
        // Python Backend-ku data anupuroam
        const response = await fetch('/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            // Local storage backup
            allTxs.push(payload);
            localStorage.setItem(DATA_KEY, JSON.stringify(allTxs));
            
            alert("Saved to Database! ✅");
            showPage('dashboard-page');
        } else {
            alert("Server rejected the data.");
        }
    } catch (err) {
        console.error("Connection error:", err);
        alert("Server (app.py) run aagala!");
    }
}

// 5. Download CSV Logic
function downloadCSV() {
    if (!currentUser) return alert("Please login first!");
    
    // app.py-la ulla /download/<email> route-ai koopiduroam
    window.location.href = `/download/${currentUser}`;
}
async function refreshDashboard() {
    if (!currentUser) return;

    try {
        const response = await fetch(`/get_all/${currentUser}`);
        const transactions = await response.json();
        
        // 1. Current View Month & Year
        const vMonth = currentPeriod.getMonth(); 
        const vYear = currentPeriod.getFullYear();

        let monthlyIncome = 0;
        let cumulativeExpenses = 0;

        // Current week boundaries (for expense filtering)
        const startOfWeek = new Date(currentPeriod);
        startOfWeek.setDate(currentPeriod.getDate() - currentPeriod.getDay());
        startOfWeek.setHours(0, 0, 0, 0);

        const endOfWeek = new Date(startOfWeek);
        endOfWeek.setDate(startOfWeek.getDate() + 6);
        endOfWeek.setHours(23, 59, 59, 999);

        transactions.forEach(t => {
            const txDate = new Date(t.date);
            const tMonth = txDate.getMonth();
            const tYear = txDate.getFullYear();

            // FIX: Income calculation - Filter logic illama current month income-ai sum pannum
            if (t.cat === 'Income' && tMonth === vMonth && tYear === vYear) {
                monthlyIncome += t.amt;
            }

            // Expense calculation - Filter (Week/Month) poruthu maarum
            if (t.cat !== 'Income') {
                if (currentFilter === 'week') {
                    // Intha varathula ulla expenses mattum
                    if (txDate >= startOfWeek && txDate <= endOfWeek) {
                        cumulativeExpenses += t.amt;
                    }
                } else {
                    // Intha maasathula ulla expenses mattum
                    if (tMonth === vMonth && tYear === vYear) {
                        cumulativeExpenses += t.amt;
                    }
                }
            }
        });

        // 4. CALCULATION
        const finalBalance = monthlyIncome - cumulativeExpenses;
        
        // 5. UI UPDATES
        const balanceEl = document.getElementById('total-balance');
        const incomeEl = document.getElementById('dash-income');
        const expenseEl = document.getElementById('dash-expense');

        if(balanceEl) balanceEl.innerText = `₹${finalBalance.toFixed(2)}`;
        // Fix: Variable name mismatch correct panniyachu
        if(incomeEl) incomeEl.innerText = `₹${monthlyIncome.toFixed(2)}`; 
        if(expenseEl) expenseEl.innerText = `₹${cumulativeExpenses.toFixed(2)}`;
        
        const userLabel = document.getElementById('user-display-name');
        if(userLabel) userLabel.innerText = users[currentUser]?.name || "User";

    } catch (err) {
        console.error("Dashboard calculation error:", err);
    }
}
// 7. Logout

function logout() {

    localStorage.removeItem(STORAGE_KEY);

    location.reload();

}



// 8. Change Filter

function changeFilter(filter) {

    currentFilter = filter;

    document.querySelectorAll('.toggle-btn').forEach(btn => btn.classList.remove('active'));

    document.getElementById(filter + '-btn').classList.add('active');

    const periodNav = document.getElementById('period-nav');

    const periodLabel = document.getElementById('period-label');

    if (filter === 'all') {

        periodNav.classList.add('hidden');

    } else {

        periodNav.classList.remove('hidden');

        updatePeriodLabel();

    }

    refreshDashboard();

}



// 9. Navigate Period

function navigatePeriod(direction) {

    if (currentFilter === 'week') {

        currentPeriod.setDate(currentPeriod.getDate() + direction * 7);

    } else if (currentFilter === 'month') {

        currentPeriod.setMonth(currentPeriod.getMonth() + direction);

    }

    updatePeriodLabel();

    refreshDashboard();

}



// 10. Update Period Label

function updatePeriodLabel() {

    const periodLabel = document.getElementById('period-label');

    if (currentFilter === 'week') {

        const startOfWeek = new Date(currentPeriod);

        startOfWeek.setDate(currentPeriod.getDate() - currentPeriod.getDay());

        const endOfWeek = new Date(startOfWeek);

        endOfWeek.setDate(startOfWeek.getDate() + 6);

        periodLabel.textContent = `${startOfWeek.toLocaleDateString()} - ${endOfWeek.toLocaleDateString()}`;

    } else if (currentFilter === 'month') {

        periodLabel.textContent = currentPeriod.toLocaleDateString('en-US', { year: 'numeric', month: 'long' });

    }

}