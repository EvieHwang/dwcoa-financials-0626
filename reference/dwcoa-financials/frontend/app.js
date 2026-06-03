/**
 * DWCOA Financial Dashboard Application
 */

// Configuration
const API_BASE = '/api';  // Relative path, works with CloudFront

// State
let authToken = null;
let userRole = null;
let categories = [];
let budgetChart = null;
let cashflowChart = null;
let historicalDisclaimerShown = false;  // Session flag for historical data disclaimer
let dashboardBudgetLocked = false;  // Budget lock status for the current dashboard view year
let dashboardYear = new Date().getFullYear();  // Year being displayed in dashboard

// Utility functions
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount || 0);
}

function formatPercent(value) {
    return (value * 100).toFixed(1) + '%';
}

function formatDate(dateStr) {
    if (!dateStr) return 'Never';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'America/Los_Angeles'
    }) + ' PT';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Chart colors
const CHART_COLORS = {
    budget: 'rgba(37, 99, 235, 0.8)',      // Blue
    actual: 'rgba(22, 163, 74, 0.8)',       // Green
    income: 'rgba(22, 163, 74, 0.8)',       // Green
    expenses: 'rgba(220, 38, 38, 0.8)',     // Red
    budgetBorder: 'rgba(37, 99, 235, 1)',
    actualBorder: 'rgba(22, 163, 74, 1)',
    incomeBorder: 'rgba(22, 163, 74, 1)',
    expensesBorder: 'rgba(220, 38, 38, 1)'
};

const MONTH_LABELS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

// Chart functions
function renderBudgetChart(data) {
    const ctx = document.getElementById('budget-chart');
    if (!ctx) return;

    // Calculate totals for income
    // Use income_summary.annual_budget (total operating budget) for the budget display
    const incomeBudget = data.income_summary.annual_budget;
    const incomeActual = data.dues_status.reduce((sum, u) => sum + u.paid_ytd, 0);

    // Get expense totals
    const expenseBudget = data.expense_summary.annual_budget;
    const expenseActual = data.expense_summary.ytd_actual;

    const chartData = {
        labels: ['Income & Dues', 'Operating Expenses'],
        datasets: [
            {
                label: 'Annual Budget',
                data: [incomeBudget, expenseBudget],
                backgroundColor: CHART_COLORS.budget,
                borderColor: CHART_COLORS.budgetBorder,
                borderWidth: 1
            },
            {
                label: 'Actual (YTD)',
                data: [incomeActual, expenseActual],
                backgroundColor: CHART_COLORS.actual,
                borderColor: CHART_COLORS.actualBorder,
                borderWidth: 1
            }
        ]
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom'
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        return context.dataset.label + ': ' + formatCurrency(context.raw);
                    }
                }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    callback: function(value) {
                        return '$' + value.toLocaleString();
                    }
                }
            }
        }
    };

    if (budgetChart) {
        budgetChart.data = chartData;
        budgetChart.update();
    } else {
        budgetChart = new Chart(ctx, {
            type: 'bar',
            data: chartData,
            options: options
        });
    }
}

function renderCashflowChart(data) {
    const ctx = document.getElementById('cashflow-chart');
    if (!ctx) return;

    const monthlyData = data.monthly_cashflow || [];

    // Get labels for months that have data
    const labels = monthlyData.map(m => MONTH_LABELS[m.month - 1]);
    const incomeData = monthlyData.map(m => m.income);
    const expenseData = monthlyData.map(m => m.expenses);

    const chartData = {
        labels: labels,
        datasets: [
            {
                label: 'Income',
                data: incomeData,
                borderColor: CHART_COLORS.incomeBorder,
                backgroundColor: CHART_COLORS.income,
                tension: 0.1,
                fill: false
            },
            {
                label: 'Expenses',
                data: expenseData,
                borderColor: CHART_COLORS.expensesBorder,
                backgroundColor: CHART_COLORS.expenses,
                tension: 0.1,
                fill: false
            }
        ]
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'bottom'
            },
            tooltip: {
                callbacks: {
                    label: function(context) {
                        return context.dataset.label + ': ' + formatCurrency(context.raw);
                    }
                }
            }
        },
        scales: {
            y: {
                beginAtZero: true,
                ticks: {
                    callback: function(value) {
                        return '$' + value.toLocaleString();
                    }
                }
            }
        }
    };

    if (cashflowChart) {
        cashflowChart.data = chartData;
        cashflowChart.update();
    } else {
        cashflowChart = new Chart(ctx, {
            type: 'line',
            data: chartData,
            options: options
        });
    }
}

function renderCharts(data) {
    if (typeof Chart === 'undefined') {
        console.error('Chart.js not loaded');
        return;
    }
    renderBudgetChart(data);
    renderCashflowChart(data);
}

// API functions
async function apiRequest(endpoint, options = {}) {
    const url = API_BASE + endpoint;
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }

    const response = await fetch(url, {
        ...options,
        headers
    });

    if (response.status === 401) {
        logout();
        throw new Error('Session expired');
    }

    return response;
}

async function login(password) {
    const response = await fetch(API_BASE + '/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password })
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Login failed');
    }

    const data = await response.json();
    authToken = data.token;
    userRole = data.role;

    // Store in localStorage
    localStorage.setItem('dwcoa_token', authToken);
    localStorage.setItem('dwcoa_role', userRole);

    return data;
}

function logout() {
    authToken = null;
    userRole = null;
    localStorage.removeItem('dwcoa_token');
    localStorage.removeItem('dwcoa_role');

    document.getElementById('dashboard').classList.add('hidden');
    document.getElementById('login-modal').classList.remove('hidden');
}

async function checkAuth() {
    const token = localStorage.getItem('dwcoa_token');
    const role = localStorage.getItem('dwcoa_role');

    if (!token) return false;

    try {
        const response = await fetch(API_BASE + '/auth/verify', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            authToken = token;
            userRole = role;
            return true;
        }
    } catch (e) {
        console.error('Auth check failed:', e);
    }

    localStorage.removeItem('dwcoa_token');
    localStorage.removeItem('dwcoa_role');
    return false;
}

// Loading overlay functions
function showLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.classList.remove('hidden');
}

function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.classList.add('hidden');
}

// Dashboard functions
async function loadDashboard(asOfDate = null) {
    showLoading();
    try {
        let url = '/dashboard';
        if (asOfDate) {
            url += `?as_of_date=${asOfDate}`;
        }
        const response = await apiRequest(url);
        const data = await response.json();

        renderDashboard(data);
    } catch (e) {
        console.error('Failed to load dashboard:', e);
        alert('Failed to load dashboard: ' + e.message);
    } finally {
        hideLoading();
    }
}

function getTodayString() {
    return new Date().toISOString().split('T')[0];
}

function checkHistoricalDate(dateString) {
    // Show disclaimer for dates before January 1, 2025
    // Only show once per session
    if (historicalDisclaimerShown) return;

    const selectedDate = new Date(dateString + 'T00:00:00');
    const cutoffDate = new Date('2025-01-01T00:00:00');

    if (selectedDate < cutoffDate) {
        const modal = document.getElementById('historical-modal');
        if (modal) modal.classList.remove('hidden');
    }
}

function renderDashboard(data) {
    // Store dashboard-level budget lock state for use by other sections
    dashboardBudgetLocked = data.budget_locked || false;
    dashboardYear = data.year || new Date().getFullYear();

    // Last updated
    document.getElementById('last-updated').textContent =
        data.last_updated ? `Last updated: ${formatDate(data.last_updated)}` : 'No data uploaded';

    // Update date picker and snapshot label
    const snapshotDate = data.as_of_date || getTodayString();
    const datePickerEl = document.getElementById('snapshot-date');
    const snapshotLabelEl = document.getElementById('snapshot-label');

    if (datePickerEl) {
        datePickerEl.value = snapshotDate;
    }

    if (snapshotLabelEl) {
        const today = getTodayString();
        if (snapshotDate === today) {
            snapshotLabelEl.textContent = '(Current)';
        } else {
            const d = new Date(snapshotDate + 'T00:00:00');
            const formatted = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
            snapshotLabelEl.textContent = `Showing ${data.year} data through ${formatted}`;
        }
    }

    // Update section date indicators
    const indicatorDate = new Date(snapshotDate + 'T00:00:00');
    const indicatorFormatted = indicatorDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    document.querySelectorAll('.section-date-indicator').forEach(el => {
        el.textContent = `As of ${indicatorFormatted}`;
    });

    // User role - show badge and control admin visibility
    const roleEl = document.getElementById('user-role');
    roleEl.textContent = userRole === 'admin' ? 'Admin' : 'Homeowner';

    // Show/hide admin controls based on role
    if (userRole === 'admin') {
        document.querySelectorAll('.admin-only').forEach(el => el.classList.remove('hidden'));
    } else {
        document.querySelectorAll('.admin-only').forEach(el => el.classList.add('hidden'));
    }

    // Account balances table - render each account with starting, current, and change
    const accountsTableBody = document.getElementById('accounts-table-body');
    const accountOrder = ['Checking', 'Savings', 'Reserve Fund'];

    let totalStarting = 0;
    let totalCurrent = 0;

    // Build table rows
    accountsTableBody.innerHTML = accountOrder.map(name => {
        const acc = data.accounts.find(a => a.name === name);
        const starting = acc ? (acc.starting_balance || 0) : 0;
        const current = acc ? (acc.balance || 0) : 0;
        const change = current - starting;

        totalStarting += starting;
        totalCurrent += current;

        const changeClass = change >= 0 ? 'positive' : 'negative';
        const changePrefix = change >= 0 ? '+' : '';

        return `
            <tr>
                <td>${name}</td>
                <td>${formatCurrency(starting)}</td>
                <td>${formatCurrency(current)}</td>
                <td class="${changeClass}">${changePrefix}${formatCurrency(change)}</td>
            </tr>
        `;
    }).join('');

    // Update totals row
    const totalChange = totalCurrent - totalStarting;
    const totalChangeClass = totalChange >= 0 ? 'positive' : 'negative';
    const totalChangePrefix = totalChange >= 0 ? '+' : '';

    document.getElementById('total-starting').textContent = formatCurrency(totalStarting);
    document.getElementById('total-current').textContent = formatCurrency(totalCurrent);
    const totalChangeEl = document.getElementById('total-change');
    totalChangeEl.textContent = `${totalChangePrefix}${formatCurrency(totalChange)}`;
    totalChangeEl.className = totalChangeClass;

    // Reserve Fund Goal summary box
    // Find Reserve Fund account change (already calculated above)
    const reserveAcc = data.accounts.find(a => a.name === 'Reserve Fund');
    const reserveStarting = reserveAcc ? (reserveAcc.starting_balance || 0) : 0;
    const reserveCurrent = reserveAcc ? (reserveAcc.balance || 0) : 0;
    const reserveChange = reserveCurrent - reserveStarting;

    // Find Reserve Fund goal from expense categories (look for "Reserve Fund" or "Reserve Contribution")
    const reserveCategory = data.expense_summary.categories.find(cat => {
        const name = cat.category.toLowerCase();
        return name === 'reserve fund' || name === 'reserve contribution';
    });
    const reserveGoal = reserveCategory ? reserveCategory.annual_budget : 0;
    const reserveDifference = reserveChange - reserveGoal;

    document.getElementById('reserve-goal').textContent = formatCurrency(reserveGoal);
    const reserveActualChangeEl = document.getElementById('reserve-actual-change');
    const reserveChangePrefix = reserveChange >= 0 ? '+' : '';
    reserveActualChangeEl.textContent = `${reserveChangePrefix}${formatCurrency(reserveChange)}`;
    reserveActualChangeEl.className = reserveChange >= 0 ? 'positive' : 'negative';

    const reserveDiffEl = document.getElementById('reserve-difference');
    const reserveDiffPrefix = reserveDifference >= 0 ? '+' : '';
    reserveDiffEl.textContent = `${reserveDiffPrefix}${formatCurrency(reserveDifference)}`;
    reserveDiffEl.className = reserveDifference >= 0 ? 'positive' : 'negative';

    // Net Income summary box
    const incomeActual = data.income_summary.ytd_actual || 0;
    const expenseActual = data.expense_summary.ytd_actual || 0;
    const netIncome = incomeActual - expenseActual;

    document.getElementById('net-income-value').textContent = formatCurrency(incomeActual);
    document.getElementById('net-expenses-value').textContent = formatCurrency(expenseActual);
    const netTotalEl = document.getElementById('net-total');
    const netPrefix = netIncome >= 0 ? '+' : '';
    netTotalEl.textContent = `${netPrefix}${formatCurrency(netIncome)}`;
    netTotalEl.className = netIncome >= 0 ? 'positive' : 'negative';

    // Income & Dues summary
    // Find Interest category from income categories
    const interestCategory = data.income_summary.categories.find(cat =>
        cat.category.toLowerCase().includes('interest')
    );
    const interestBudget = interestCategory ? interestCategory.annual_budget : 0;
    const interestActual = interestCategory ? interestCategory.ytd_actual : 0;
    const interestRemaining = interestBudget - interestActual;

    // Total income = dues + interest
    const duesOnlyActual = data.dues_status.reduce((sum, u) => sum + u.paid_ytd, 0);
    const incomeBudget = data.income_summary.annual_budget;
    const incomeActualTotal = duesOnlyActual + interestActual;
    const incomeRemaining = incomeBudget - incomeActualTotal;

    document.getElementById('dues-budget').textContent = formatCurrency(incomeBudget);
    document.getElementById('dues-actual').textContent = formatCurrency(incomeActualTotal);
    const duesRemainingEl = document.getElementById('dues-remaining');
    // Invert sign: surplus (negative remaining) shows as positive, deficit shows as negative
    const displayIncomeRemaining = -incomeRemaining;
    duesRemainingEl.textContent = formatCurrency(displayIncomeRemaining);
    duesRemainingEl.className = displayIncomeRemaining >= 0 ? 'positive' : 'negative';

    // Dues table (compact) - unit rows
    const duesTable = document.querySelector('#dues-table tbody');

    // Calculate totals for the totals row
    let totalPastDue = 0;
    let totalBudget = 0;
    let totalActual = 0;
    let totalRemaining = 0;

    let duesRows = data.dues_status.map(unit => {
        totalPastDue += unit.past_due_balance || 0;
        totalBudget += unit.annual_budget || 0;
        totalActual += unit.paid_ytd || 0;
        totalRemaining += unit.outstanding || 0;
        // Remaining: negative outstanding = surplus (green), positive = deficit (red)
        // Display inverted so minus sign appears on deficit
        const displayRemaining = -unit.outstanding;
        return `
        <tr>
            <td>${unit.unit}</td>
            <td>${formatPercent(unit.ownership_pct)}</td>
            <td class="${unit.past_due_balance < 0 ? 'positive' : ''}">${unit.past_due_balance !== 0 ? formatCurrency(unit.past_due_balance) : '-'}</td>
            <td>${formatCurrency(unit.annual_budget)}</td>
            <td>${formatCurrency(unit.paid_ytd)}</td>
            <td class="${displayRemaining >= 0 ? 'positive' : 'negative'}">${formatCurrency(displayRemaining)}</td>
        </tr>
    `}).join('');

    // Add Interest row after unit rows (0.1% share)
    totalBudget += interestBudget;
    totalActual += interestActual;
    totalRemaining += interestRemaining;
    const displayInterestRemaining = -interestRemaining;
    duesRows += `
        <tr class="interest-row">
            <td>Interest</td>
            <td>${formatPercent(0.001)}</td>
            <td>-</td>
            <td>${formatCurrency(interestBudget)}</td>
            <td>${formatCurrency(interestActual)}</td>
            <td class="${displayInterestRemaining >= 0 ? 'positive' : 'negative'}">${formatCurrency(displayInterestRemaining)}</td>
        </tr>
    `;

    // Add totals row (100% total share)
    const displayTotalRemaining = -totalRemaining;
    duesRows += `
        <tr class="totals-row">
            <td>Total</td>
            <td>100.0%</td>
            <td>${totalPastDue > 0 ? formatCurrency(totalPastDue) : '-'}</td>
            <td>${formatCurrency(totalBudget)}</td>
            <td>${formatCurrency(totalActual)}</td>
            <td class="${displayTotalRemaining >= 0 ? 'positive' : 'negative'}">${formatCurrency(displayTotalRemaining)}</td>
        </tr>
    `;
    duesTable.innerHTML = duesRows;

    // Expense summary
    const expense = data.expense_summary;
    document.getElementById('expense-budget').textContent = formatCurrency(expense.annual_budget);
    document.getElementById('expense-actual').textContent = formatCurrency(expense.ytd_actual);
    const expenseRemainingEl = document.getElementById('expense-remaining');
    expenseRemainingEl.textContent = formatCurrency(expense.remaining);
    expenseRemainingEl.className = expense.remaining >= 0 ? 'positive' : 'negative';

    const expenseTable = document.querySelector('#expense-table tbody');
    let expenseRows = expense.categories.map(cat => `
        <tr>
            <td>${cat.category}</td>
            <td>${formatCurrency(cat.annual_budget)}</td>
            <td>${formatCurrency(cat.ytd_actual)}</td>
            <td class="${cat.remaining >= 0 ? 'positive' : 'negative'}">${formatCurrency(cat.remaining)}</td>
        </tr>
    `).join('');

    // Add totals row
    expenseRows += `
        <tr class="totals-row">
            <td>Total</td>
            <td>${formatCurrency(expense.annual_budget)}</td>
            <td>${formatCurrency(expense.ytd_actual)}</td>
            <td class="${expense.remaining >= 0 ? 'positive' : 'negative'}">${formatCurrency(expense.remaining)}</td>
        </tr>
    `;
    expenseTable.innerHTML = expenseRows;

    // Show budget lock notice for expenses section
    const expenseBudgetNotice = document.getElementById('expense-budget-notice');
    if (expenseBudgetNotice) {
        if (!data.budget_locked) {
            expenseBudgetNotice.textContent = `Budget for ${data.year} is pending approval. Amounts shown are preliminary.`;
            expenseBudgetNotice.classList.remove('hidden');
        } else {
            expenseBudgetNotice.classList.add('hidden');
        }
    }

    // Review button - show count and gray out if zero
    const reviewBtn = document.getElementById('review-btn');
    if (reviewBtn) {
        reviewBtn.textContent = `Review Transactions (${data.review_count})`;
        if (data.review_count === 0) {
            reviewBtn.classList.add('grayed');
        } else {
            reviewBtn.classList.remove('grayed');
        }
    }

    // Render charts
    renderCharts(data);
}

// Upload functions
async function uploadCSV(file, replaceAll = false) {
    // Read file as text for JSON body
    const text = await file.text();

    const response = await apiRequest('/transactions/upload', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ file: text, replace_all: replaceAll })
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Upload failed');
    }

    return await response.json();
}

// Download functions
async function downloadCSV() {
    const response = await apiRequest('/transactions/download');
    const blob = await response.blob();

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'dwcoa_transactions.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

async function downloadPDF() {
    // Get the selected date from the date picker
    const snapshotDateEl = document.getElementById('snapshot-date');
    const asOfDate = snapshotDateEl ? snapshotDateEl.value : getTodayString();

    const response = await apiRequest(`/reports/pdf?as_of_date=${asOfDate}`);
    const blob = await response.blob();

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `DWCOA_Report_${asOfDate}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
}

// Review functions
async function loadReviewQueue() {
    const response = await apiRequest('/review');
    const data = await response.json();

    // Load categories for dropdown
    const catResponse = await apiRequest('/categories');
    const catData = await catResponse.json();
    categories = catData.categories;

    renderReviewQueue(data.transactions);
}

function renderReviewQueue(transactions) {
    const reviewList = document.getElementById('review-list');

    if (transactions.length === 0) {
        reviewList.innerHTML = '<p>No transactions need review.</p>';
        return;
    }

    const categoryOptions = categories
        .filter(c => c.active)
        .map(c => `<option value="${c.id}">${c.name}</option>`)
        .join('');

    reviewList.innerHTML = transactions.map(txn => `
        <div class="review-item" data-id="${txn.id}" data-description="${escapeHtml(txn.description)}">
            <div>
                <div class="description">${escapeHtml(txn.description)}</div>
                <div class="meta">${txn.account_name} | ${txn.post_date} | ${formatCurrency(txn.credit || txn.debit)}</div>
            </div>
            <select class="category-select">
                <option value="">Select category...</option>
                ${categoryOptions}
            </select>
            <div class="review-actions">
                <button class="btn-primary save-category-btn">Save</button>
                <button class="btn-secondary create-rule-btn">Create Rule</button>
            </div>
        </div>
    `).join('');

    // Add event listeners for Save button
    reviewList.querySelectorAll('.save-category-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const item = e.target.closest('.review-item');
            const txnId = item.dataset.id;
            const categoryId = item.querySelector('.category-select').value;

            if (!categoryId) {
                alert('Please select a category');
                return;
            }

            try {
                await apiRequest(`/transactions/${txnId}`, {
                    method: 'PATCH',
                    body: JSON.stringify({
                        category_id: parseInt(categoryId),
                        needs_review: false
                    })
                });

                item.remove();

                // Check if queue is empty
                if (reviewList.children.length === 0) {
                    reviewList.innerHTML = '<p>All transactions reviewed!</p>';
                }
            } catch (e) {
                alert('Failed to save: ' + e.message);
            }
        });
    });

    // Add event listeners for Create Rule button
    reviewList.querySelectorAll('.create-rule-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const item = e.target.closest('.review-item');
            const description = item.dataset.description;
            const categorySelect = item.querySelector('.category-select');
            const selectedCategoryId = categorySelect.value;

            // Check if a category is selected
            if (!selectedCategoryId) {
                alert('Please select a category first');
                return;
            }

            // Check if form already exists
            if (item.querySelector('.create-rule-form')) {
                return;
            }

            // Create inline form
            const form = document.createElement('div');
            form.className = 'create-rule-form';
            form.innerHTML = `
                <input type="text" class="rule-pattern-input" value="${escapeHtml(description)}" placeholder="Match string...">
                <select class="rule-category-select">
                    ${categoryOptions}
                </select>
                <button class="btn-primary save-rule-btn">Save Rule</button>
                <button class="btn-secondary cancel-rule-btn">Cancel</button>
            `;

            // Set selected category
            form.querySelector('.rule-category-select').value = selectedCategoryId;

            item.appendChild(form);

            // Focus pattern input
            form.querySelector('.rule-pattern-input').focus();

            // Save rule handler
            form.querySelector('.save-rule-btn').addEventListener('click', async () => {
                const pattern = form.querySelector('.rule-pattern-input').value.trim();
                const categoryId = parseInt(form.querySelector('.rule-category-select').value);

                if (!pattern) {
                    alert('Pattern cannot be empty');
                    return;
                }

                try {
                    // Create the rule
                    await createRule(pattern, categoryId);

                    // Also categorize the current transaction
                    await apiRequest(`/transactions/${item.dataset.id}`, {
                        method: 'PATCH',
                        body: JSON.stringify({
                            category_id: categoryId,
                            needs_review: false
                        })
                    });

                    // Remove item from queue
                    item.remove();

                    // Check if queue is empty
                    if (reviewList.children.length === 0) {
                        reviewList.innerHTML = '<p>All transactions reviewed!</p>';
                    }
                } catch (e) {
                    alert('Error: ' + e.message);
                }
            });

            // Cancel handler
            form.querySelector('.cancel-rule-btn').addEventListener('click', () => {
                form.remove();
            });
        });
    });
}

// Budget management functions
const CALCULATED_DUES_START_YEAR = 2025;  // Cutoff year for calculated dues
let currentBudgetLocked = false;

async function loadBudgets(year) {
    try {
        const response = await apiRequest(`/budgets?year=${year}`);
        const data = await response.json();

        // Store lock status
        currentBudgetLocked = data.locked || false;

        // Update lock checkbox
        const lockCheckbox = document.getElementById('budget-locked');
        if (lockCheckbox) {
            lockCheckbox.checked = currentBudgetLocked;
        }

        // Show lock indicator
        const lockIndicator = document.getElementById('budget-lock-indicator');
        if (lockIndicator) {
            if (currentBudgetLocked) {
                lockIndicator.classList.remove('hidden');
                if (data.locked_at) {
                    lockIndicator.textContent = `Budget locked on ${formatDate(data.locked_at)}`;
                } else {
                    lockIndicator.textContent = 'Budget is locked';
                }
            } else {
                lockIndicator.classList.add('hidden');
            }
        }

        renderBudgetTable(data.budgets, year, currentBudgetLocked);
    } catch (e) {
        showBudgetStatus('Error loading budgets: ' + e.message, 'error');
    }
}

function renderBudgetTable(budgets, year, isLocked = false) {
    const tbody = document.getElementById('budget-edit-body');

    if (!budgets || budgets.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5">No budgets found for ${year}. Copy from a previous year or add categories.</td></tr>`;
        return;
    }

    // Filter out Dues and Interest categories for 2025+ (they're calculated from operating budget)
    let filteredBudgets = budgets;
    if (year >= CALCULATED_DUES_START_YEAR) {
        filteredBudgets = budgets.filter(b =>
            !b.category_name.startsWith('Dues ') && b.category_name !== 'Interest'
        );
    }

    if (filteredBudgets.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5">No budgets found for ${year}. Copy from a previous year or add categories.</td></tr>`;
        return;
    }

    tbody.innerHTML = filteredBudgets.map(b => `
        <tr data-category-id="${b.category_id}" data-year="${year}" data-txn-count="${b.transaction_count || 0}">
            <td>
                <input type="text" class="name-input" value="${b.category_name}" placeholder="Category name" ${isLocked ? 'disabled' : ''}>
            </td>
            <td>
                <span class="type-text">${b.category_type}</span>
            </td>
            <td>
                <select class="timing-select" ${isLocked ? 'disabled' : ''}>
                    <option value="monthly" ${b.effective_timing === 'monthly' ? 'selected' : ''}>Monthly</option>
                    <option value="quarterly" ${b.effective_timing === 'quarterly' ? 'selected' : ''}>Quarterly</option>
                    <option value="annual" ${b.effective_timing === 'annual' ? 'selected' : ''}>Annual</option>
                </select>
            </td>
            <td>
                <input type="number" class="amount-input" value="${b.annual_amount || 0}" step="0.01" min="0" ${isLocked ? 'disabled' : ''}>
            </td>
            <td class="action-buttons">
                ${isLocked ? '' : '<button class="btn-primary save-budget-btn">Save</button>'}
                ${isLocked ? '' : '<button class="btn-secondary retire-btn">Retire</button>'}
            </td>
        </tr>
    `).join('');

    // Add save handlers
    tbody.querySelectorAll('.save-budget-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const row = e.target.closest('tr');
            const categoryId = parseInt(row.dataset.categoryId);
            const year = parseInt(row.dataset.year);
            const name = row.querySelector('.name-input').value.trim();
            const amount = parseFloat(row.querySelector('.amount-input').value);
            const timing = row.querySelector('.timing-select').value;

            if (!name) {
                showBudgetStatus('Category name is required', 'error');
                return;
            }

            try {
                // Update category name (type is fixed for existing categories)
                await apiRequest(`/categories/${categoryId}`, {
                    method: 'PATCH',
                    body: JSON.stringify({ name })
                });

                // Update budget
                await apiRequest('/budgets', {
                    method: 'POST',
                    body: JSON.stringify({
                        year: year,
                        category_id: categoryId,
                        annual_amount: amount,
                        timing: timing
                    })
                });
                showBudgetStatus('Budget saved!', 'success');
            } catch (e) {
                showBudgetStatus('Error saving: ' + e.message, 'error');
            }
        });
    });

    // Add retire handlers
    tbody.querySelectorAll('.retire-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const row = e.target.closest('tr');
            const categoryId = parseInt(row.dataset.categoryId);
            const txnCount = parseInt(row.dataset.txnCount) || 0;
            const name = row.querySelector('.name-input').value;

            let message = `Retire category "${name}"?`;
            if (txnCount > 0) {
                message = `Category "${name}" has ${txnCount} transaction(s). Retiring will hide it from dropdowns but preserve historical data. Continue?`;
            }

            if (!confirm(message)) {
                return;
            }

            try {
                await apiRequest(`/categories/${categoryId}`, {
                    method: 'PATCH',
                    body: JSON.stringify({ active: false })
                });
                showBudgetStatus(`Category "${name}" retired`, 'success');
                // Reload budgets to reflect change
                const year = parseInt(row.dataset.year);
                await loadBudgets(year);
            } catch (e) {
                showBudgetStatus('Error retiring: ' + e.message, 'error');
            }
        });
    });
}

async function copyBudgets(fromYear, toYear) {
    try {
        const response = await apiRequest('/budgets/copy', {
            method: 'POST',
            body: JSON.stringify({
                from_year: fromYear,
                to_year: toYear
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Copy failed');
        }

        const data = await response.json();
        showBudgetStatus(data.message, 'success');

        // Reload the target year
        document.getElementById('budget-year').value = toYear;
        await loadBudgets(toYear);
    } catch (e) {
        showBudgetStatus('Error copying budgets: ' + e.message, 'error');
    }
}

function showBudgetStatus(message, type) {
    const statusEl = document.getElementById('budget-status');
    statusEl.textContent = message;
    statusEl.className = `status-message ${type}`;
    statusEl.classList.remove('hidden');

    // Auto-hide after 3 seconds
    setTimeout(() => {
        statusEl.classList.add('hidden');
    }, 3000);
}

async function toggleBudgetLock(year, locked) {
    // Confirm unlock
    if (!locked) {
        if (!confirm('Unlocking allows budget changes. Are you sure?')) {
            // Restore checkbox state
            const lockCheckbox = document.getElementById('budget-locked');
            if (lockCheckbox) lockCheckbox.checked = true;
            return;
        }
    }

    try {
        const response = await apiRequest(`/budgets/lock/${year}`, {
            method: 'POST',
            body: JSON.stringify({ locked })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.message || 'Failed to update lock status');
        }

        showBudgetStatus(locked ? 'Budget locked' : 'Budget unlocked', 'success');

        // Refresh UI
        await loadBudgets(year);
    } catch (e) {
        showBudgetStatus('Error: ' + e.message, 'error');
        // Restore checkbox state
        const lockCheckbox = document.getElementById('budget-locked');
        if (lockCheckbox) lockCheckbox.checked = !locked;
    }
}

// Event handlers
document.addEventListener('DOMContentLoaded', async () => {
    // Check existing auth
    const isAuthenticated = await checkAuth();

    if (isAuthenticated) {
        document.getElementById('login-modal').classList.add('hidden');
        document.getElementById('dashboard').classList.remove('hidden');
        await loadDashboard();
        await initTransactionsTable();
    }

    // Login form
    document.getElementById('login-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const password = document.getElementById('password').value;
        const errorEl = document.getElementById('login-error');

        try {
            await login(password);
            document.getElementById('login-modal').classList.add('hidden');
            document.getElementById('dashboard').classList.remove('hidden');
            await loadDashboard();
            await initTransactionsTable();
        } catch (e) {
            errorEl.textContent = e.message;
            errorEl.classList.remove('hidden');
        }
    });

    // Logout
    document.getElementById('logout-btn').addEventListener('click', logout);

    // Date picker - initialize with today and auto-load on change
    const snapshotDateEl = document.getElementById('snapshot-date');
    const resetTodayBtn = document.getElementById('reset-today-btn');

    if (snapshotDateEl) {
        snapshotDateEl.value = getTodayString();

        // Auto-load when date changes
        snapshotDateEl.addEventListener('change', async () => {
            checkHistoricalDate(snapshotDateEl.value);
            await loadDashboard(snapshotDateEl.value);
        });
    }

    // Reset to Today button
    if (resetTodayBtn) {
        resetTodayBtn.addEventListener('click', async () => {
            if (snapshotDateEl) {
                snapshotDateEl.value = getTodayString();
            }
            await loadDashboard();
        });
    }

    // File chooser and upload
    const fileInput = document.getElementById('csv-file');
    const chooseFileBtn = document.getElementById('choose-file-btn');
    const uploadBtn = document.getElementById('upload-btn');
    const statusEl = document.getElementById('upload-status');

    if (chooseFileBtn && fileInput) {
        chooseFileBtn.addEventListener('click', () => {
            fileInput.click();
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length > 0) {
                uploadBtn.disabled = false;
                chooseFileBtn.textContent = fileInput.files[0].name;
            } else {
                uploadBtn.disabled = true;
                chooseFileBtn.textContent = 'Choose File';
            }
        });
    }

    if (uploadBtn) {
        uploadBtn.addEventListener('click', async () => {
            if (!fileInput || !fileInput.files.length) return;

            // Check if replace all is requested
            const replaceAllCheckbox = document.getElementById('replace-all-checkbox');
            const replaceAll = replaceAllCheckbox && replaceAllCheckbox.checked;

            // Confirm if replacing all data
            if (replaceAll) {
                if (!confirm('This will delete all existing transactions and their categories. Are you sure?')) {
                    return;
                }
            }

            try {
                if (statusEl) statusEl.textContent = 'Uploading...';
                uploadBtn.disabled = true;
                const result = await uploadCSV(fileInput.files[0], replaceAll);

                // Update status with new format
                if (statusEl) {
                    const msg = `Added ${result.stats.added} new, skipped ${result.stats.skipped} duplicates`;
                    statusEl.textContent = result.stats.needs_review > 0
                        ? `${msg} (${result.stats.needs_review} need review)`
                        : msg;
                }

                fileInput.value = '';
                chooseFileBtn.textContent = 'Choose File';
                if (replaceAllCheckbox) replaceAllCheckbox.checked = false;
                await loadDashboard();
                // Refresh transactions table
                if (transactionsTable) {
                    const transactions = await loadTransactions();
                    transactionsTable.setData(transactions);
                }
            } catch (e) {
                if (statusEl) statusEl.textContent = 'Error: ' + e.message;
                uploadBtn.disabled = false;
            }
        });
    }

    // Downloads
    const downloadCsvBtn = document.getElementById('download-csv-btn');
    const downloadPdfBtn = document.getElementById('download-pdf-btn');
    const printBtn = document.getElementById('print-btn');

    if (downloadCsvBtn) downloadCsvBtn.addEventListener('click', downloadCSV);
    if (downloadPdfBtn) downloadPdfBtn.addEventListener('click', downloadPDF);
    if (printBtn) printBtn.addEventListener('click', () => window.print());

    // Transaction Viewer export
    const exportTransactionsBtn = document.getElementById('export-transactions-btn');
    if (exportTransactionsBtn) {
        exportTransactionsBtn.addEventListener('click', exportFilteredTransactions);
    }

    // Review
    const reviewBtn = document.getElementById('review-btn');
    if (reviewBtn) {
        reviewBtn.addEventListener('click', async () => {
            await loadReviewQueue();
            const reviewModal = document.getElementById('review-modal');
            if (reviewModal) reviewModal.classList.remove('hidden');
        });
    }

    const closeReviewBtn = document.getElementById('close-review-btn');
    if (closeReviewBtn) {
        closeReviewBtn.addEventListener('click', () => {
            document.getElementById('review-modal').classList.add('hidden');
            loadDashboard();  // Refresh counts
        });
    }

    // Budget management
    const manageBudgetsBtn = document.getElementById('manage-budgets-btn');
    const copyBudgetsBtn = document.getElementById('copy-budgets-btn');
    const closeBudgetBtn = document.getElementById('close-budget-btn');
    const budgetYearEl = document.getElementById('budget-year');

    if (manageBudgetsBtn && budgetYearEl) {
        manageBudgetsBtn.addEventListener('click', async () => {
            const year = parseInt(budgetYearEl.value);
            await loadBudgets(year);
            document.getElementById('budget-modal').classList.remove('hidden');
        });

        // Auto-load when year selection changes
        budgetYearEl.addEventListener('change', async () => {
            const year = parseInt(budgetYearEl.value);
            await loadBudgets(year);
        });
    }

    // Budget lock toggle
    const budgetLockedCheckbox = document.getElementById('budget-locked');
    if (budgetLockedCheckbox) {
        budgetLockedCheckbox.addEventListener('change', async (e) => {
            const year = parseInt(budgetYearEl.value);
            await toggleBudgetLock(year, e.target.checked);
        });
    }

    if (copyBudgetsBtn) {
        copyBudgetsBtn.addEventListener('click', async () => {
            const copyFromEl = document.getElementById('copy-from-year');
            const copyToEl = document.getElementById('copy-to-year');
            if (!copyFromEl || !copyToEl) return;

            const fromYear = parseInt(copyFromEl.value);
            const toYear = parseInt(copyToEl.value);

            if (fromYear === toYear) {
                showBudgetStatus('From and To years must be different', 'error');
                return;
            }

            if (!confirm(`Copy all budgets from ${fromYear} to ${toYear}? This will overwrite existing ${toYear} budgets.`)) {
                return;
            }

            await copyBudgets(fromYear, toYear);
        });
    }

    if (closeBudgetBtn) {
        closeBudgetBtn.addEventListener('click', () => {
            document.getElementById('budget-modal').classList.add('hidden');
            loadDashboard();  // Refresh dashboard with any changes
        });
    }

    // Add Category button
    const addCategoryBtn = document.getElementById('add-category-btn');
    if (addCategoryBtn) {
        addCategoryBtn.addEventListener('click', () => {
            addNewCategoryRow();
        });
    }

    // Rules management
    const manageRulesBtn = document.getElementById('manage-rules-btn');
    const closeRulesBtn = document.getElementById('close-rules-btn');
    const addRuleBtn = document.getElementById('add-rule-btn');

    if (manageRulesBtn) {
        manageRulesBtn.addEventListener('click', async () => {
            // Load categories first if not loaded
            if (categories.length === 0) {
                const catResponse = await apiRequest('/categories');
                const catData = await catResponse.json();
                categories = catData.categories;
            }
            await loadRules();
            document.getElementById('rules-modal').classList.remove('hidden');
        });
    }

    if (closeRulesBtn) {
        closeRulesBtn.addEventListener('click', () => {
            document.getElementById('rules-modal').classList.add('hidden');
            loadDashboard();  // Refresh dashboard (review count may have changed)
        });
    }

    // Historical data disclaimer modal
    const historicalOkBtn = document.getElementById('historical-ok-btn');
    if (historicalOkBtn) {
        historicalOkBtn.addEventListener('click', () => {
            historicalDisclaimerShown = true;
            document.getElementById('historical-modal').classList.add('hidden');
        });
    }

    // Unit selector for My Account section
    initUnitSelector();

    if (addRuleBtn) {
        addRuleBtn.addEventListener('click', async () => {
            const patternInput = document.getElementById('new-rule-pattern');
            const categorySelect = document.getElementById('new-rule-category');

            const pattern = patternInput.value.trim();
            const categoryId = parseInt(categorySelect.value);

            if (!pattern) {
                showRulesStatus('Please enter a match string', 'error');
                return;
            }

            try {
                await createRule(pattern, categoryId);
                showRulesStatus('Rule created!', 'success');
                patternInput.value = '';
                await loadRules();  // Refresh the table
            } catch (e) {
                showRulesStatus('Error: ' + e.message, 'error');
            }
        });
    }
});

// Add new category row to the budget table
function addNewCategoryRow() {
    const tbody = document.getElementById('budget-edit-body');
    const year = parseInt(document.getElementById('budget-year').value);

    // Check if there's already a new row being added
    if (tbody.querySelector('tr.new-category-row')) {
        showBudgetStatus('Please save or cancel the current new category first', 'error');
        return;
    }

    const newRow = document.createElement('tr');
    newRow.className = 'new-category-row';
    newRow.dataset.year = year;
    newRow.innerHTML = `
        <td>
            <input type="text" class="name-input" placeholder="Category name" autofocus>
        </td>
        <td>
            <select class="type-select">
                <option value="Expense">Expense</option>
                <option value="Income">Income</option>
                <option value="Transfer">Transfer</option>
            </select>
        </td>
        <td>
            <select class="timing-select">
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="annual">Annual</option>
            </select>
        </td>
        <td>
            <input type="number" class="amount-input" value="0" step="0.01" min="0">
        </td>
        <td class="action-buttons">
            <button class="btn-primary create-category-btn">Create</button>
            <button class="btn-secondary cancel-category-btn">Cancel</button>
        </td>
    `;

    tbody.appendChild(newRow);

    // Focus the name input
    newRow.querySelector('.name-input').focus();

    // Create button handler
    newRow.querySelector('.create-category-btn').addEventListener('click', async () => {
        const name = newRow.querySelector('.name-input').value.trim();
        const type = newRow.querySelector('.type-select').value;
        const timing = newRow.querySelector('.timing-select').value;
        const amount = parseFloat(newRow.querySelector('.amount-input').value) || 0;

        if (!name) {
            showBudgetStatus('Category name is required', 'error');
            return;
        }

        try {
            // Create the category
            const catResponse = await apiRequest('/categories', {
                method: 'POST',
                body: JSON.stringify({ name, type, timing })
            });

            if (!catResponse.ok) {
                const error = await catResponse.json();
                throw new Error(error.message || 'Failed to create category');
            }

            const category = await catResponse.json();

            // Create budget for this category
            await apiRequest('/budgets', {
                method: 'POST',
                body: JSON.stringify({
                    year: year,
                    category_id: category.id,
                    annual_amount: amount,
                    timing: timing
                })
            });

            showBudgetStatus(`Category "${name}" created!`, 'success');

            // Reload budgets to show new category in proper order
            await loadBudgets(year);
        } catch (e) {
            showBudgetStatus('Error: ' + e.message, 'error');
        }
    });

    // Cancel button handler
    newRow.querySelector('.cancel-category-btn').addEventListener('click', () => {
        newRow.remove();
    });
}

// Transaction Viewer - Tabulator
let transactionsTable = null;

async function loadTransactions() {
    try {
        // Get all transactions (no pagination from server, let Tabulator handle it)
        // Admin sees all transactions including transfers; homeowners see only income/expenses
        const includeAll = userRole === 'admin' ? '&include_all=true' : '';
        const response = await apiRequest(`/transactions?limit=10000${includeAll}`);

        if (!response.ok) {
            return [];
        }

        const data = await response.json();
        return data.transactions || [];
    } catch (e) {
        console.error('Failed to load transactions:', e);
        return [];
    }
}

async function initTransactionsTable() {
    const tableEl = document.getElementById('transactions-table');
    if (!tableEl) {
        console.error('Transactions table element not found');
        return;
    }

    // Check if user is admin for inline editing
    const isAdmin = userRole === 'admin';

    // Show loading state
    tableEl.innerHTML = '<p style="padding: 1rem; color: #666;">Loading transactions...</p>';

    try {
        const transactions = await loadTransactions();

        if (typeof Tabulator === 'undefined') {
            tableEl.innerHTML = '<p class="error">Error: Tabulator library not loaded. Check browser console.</p>';
            return;
        }

        if (!transactions || transactions.length === 0) {
            tableEl.innerHTML = '<p style="padding: 1rem; color: #666;">No transactions found. Upload a CSV file to see transaction history.</p>';
            return;
        }

        // Load categories if not already loaded (for admin inline editing)
        if (isAdmin && categories.length === 0) {
            const catResponse = await apiRequest('/categories');
            const catData = await catResponse.json();
            categories = catData.categories;
        }

        // Build category options for dropdown editor (admin only)
        const categoryEditorParams = {
            values: categories
                .filter(c => c.active)
                .reduce((acc, c) => {
                    acc[c.name] = c.name;
                    return acc;
                }, { '': '(Uncategorized)' })
        };

        transactionsTable = new Tabulator("#transactions-table", {
        data: transactions,
        layout: "fitColumns",
        responsiveLayout: "collapse",
        pagination: true,
        paginationSize: 25,
        paginationSizeSelector: [25, 50, 100],
        initialSort: [{ column: "post_date", dir: "desc" }],
        placeholder: "No transactions uploaded",
        columns: [
            {
                title: "Post Date",
                field: "post_date",
                sorter: function(a, b) {
                    // Simple string comparison works for YYYY-MM-DD format
                    return a.localeCompare(b);
                },
                headerFilter: "input",
                width: 120
            },
            {
                title: "Account",
                field: "account_name",
                sorter: "string",
                headerFilter: "input",
                width: 120
            },
            {
                title: "Category",
                field: "category",
                sorter: "string",
                headerFilter: "input",
                formatter: function(cell) {
                    const val = cell.getValue();
                    if (!val) return '<span class="uncategorized">Uncategorized</span>';
                    return isAdmin ? `<span class="editable-cell">${escapeHtml(val)}</span>` : escapeHtml(val);
                },
                editor: isAdmin ? "list" : false,
                editorParams: isAdmin ? categoryEditorParams : {},
                cellEdited: isAdmin ? async function(cell) {
                    const row = cell.getRow();
                    const txnId = row.getData().id;
                    const newCategory = cell.getValue();

                    // Find category ID from name
                    const category = categories.find(c => c.name === newCategory);
                    const categoryId = category ? category.id : null;

                    try {
                        await apiRequest(`/transactions/${txnId}`, {
                            method: 'PATCH',
                            body: JSON.stringify({ category_id: categoryId, needs_review: false })
                        });

                        // Flash row green to confirm save
                        const rowEl = row.getElement();
                        rowEl.classList.add('row-saved');
                        setTimeout(() => rowEl.classList.remove('row-saved'), 1000);
                    } catch (e) {
                        alert('Failed to save: ' + e.message);
                        // Revert to old value
                        cell.restoreOldValue();
                    }
                } : undefined
            },
            {
                title: "Description",
                field: "description",
                sorter: "string",
                headerFilter: "input",
                formatter: function(cell) {
                    const val = cell.getValue();
                    return isAdmin ? `<span class="editable-cell">${escapeHtml(val || '')}</span>` : escapeHtml(val || '');
                },
                editor: isAdmin ? "input" : false,
                cellEdited: isAdmin ? async function(cell) {
                    const row = cell.getRow();
                    const txnId = row.getData().id;
                    const newDescription = cell.getValue();

                    try {
                        await apiRequest(`/transactions/${txnId}`, {
                            method: 'PATCH',
                            body: JSON.stringify({ description: newDescription })
                        });

                        // Flash row green to confirm save
                        const rowEl = row.getElement();
                        rowEl.classList.add('row-saved');
                        setTimeout(() => rowEl.classList.remove('row-saved'), 1000);
                    } catch (e) {
                        alert('Failed to save: ' + e.message);
                        cell.restoreOldValue();
                    }
                } : undefined
            },
            {
                title: "Debit",
                field: "debit",
                sorter: "number",
                hozAlign: "right",
                formatter: function(cell) {
                    const val = cell.getValue();
                    if (val === null || val === undefined || val === '' || val === 0) return '';
                    return formatCurrency(val);
                },
                width: 110
            },
            {
                title: "Credit",
                field: "credit",
                sorter: "number",
                hozAlign: "right",
                formatter: function(cell) {
                    const val = cell.getValue();
                    if (val === null || val === undefined || val === '' || val === 0) return '';
                    return formatCurrency(val);
                },
                width: 110
            }
        ]
    });
    } catch (e) {
        console.error('Error initializing transactions table:', e);
        tableEl.innerHTML = `<p class="error">Error loading transactions: ${e.message}</p>`;
    }
}

function exportFilteredTransactions() {
    if (transactionsTable) {
        transactionsTable.download("csv", "dwcoa_transactions_filtered.csv");
    }
}

// Rules Management
async function loadRules() {
    try {
        const response = await apiRequest('/rules');
        const data = await response.json();
        renderRulesTable(data.rules);

        // Populate category dropdown for new rules
        const catResponse = await apiRequest('/categories');
        const catData = await catResponse.json();
        const categorySelect = document.getElementById('new-rule-category');
        if (categorySelect) {
            categorySelect.innerHTML = categories
                .filter(c => c.active)
                .map(c => `<option value="${c.id}">${c.name}</option>`)
                .join('');
        }
    } catch (e) {
        showRulesStatus('Error loading rules: ' + e.message, 'error');
    }
}

function renderRulesTable(rules) {
    const tbody = document.getElementById('rules-body');

    if (!rules || rules.length === 0) {
        tbody.innerHTML = '<tr><td colspan="3">No rules configured. Add rules to auto-categorize transactions.</td></tr>';
        return;
    }

    // Build category options
    const categoryOptions = categories
        .filter(c => c.active)
        .map(c => `<option value="${c.id}">${c.name}</option>`)
        .join('');

    tbody.innerHTML = rules.map(rule => `
        <tr data-rule-id="${rule.id}">
            <td>
                <input type="text" class="pattern-input" value="${escapeHtml(rule.pattern)}">
            </td>
            <td>
                <select class="category-select">
                    ${categoryOptions}
                </select>
            </td>
            <td class="action-buttons">
                <button class="btn-primary save-rule-btn">Save</button>
                <button class="btn-secondary delete-rule-btn">Delete</button>
            </td>
        </tr>
    `).join('');

    // Set selected category for each rule
    rules.forEach(rule => {
        const row = tbody.querySelector(`tr[data-rule-id="${rule.id}"]`);
        if (row) {
            const select = row.querySelector('.category-select');
            if (select) select.value = rule.category_id;
        }
    });

    // Add save handlers
    tbody.querySelectorAll('.save-rule-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const row = e.target.closest('tr');
            const ruleId = parseInt(row.dataset.ruleId);
            const pattern = row.querySelector('.pattern-input').value.trim();
            const categoryId = parseInt(row.querySelector('.category-select').value);

            if (!pattern) {
                showRulesStatus('Pattern cannot be empty', 'error');
                return;
            }

            try {
                await apiRequest(`/rules/${ruleId}`, {
                    method: 'PATCH',
                    body: JSON.stringify({ pattern, category_id: categoryId })
                });
                showRulesStatus('Rule saved!', 'success');
            } catch (e) {
                showRulesStatus('Error saving: ' + e.message, 'error');
            }
        });
    });

    // Add delete handlers
    tbody.querySelectorAll('.delete-rule-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const row = e.target.closest('tr');
            const ruleId = parseInt(row.dataset.ruleId);
            const pattern = row.querySelector('.pattern-input').value;

            if (!confirm(`Delete rule "${pattern}"? Transactions using this category will be flagged for review.`)) {
                return;
            }

            try {
                const response = await apiRequest(`/rules/${ruleId}`, {
                    method: 'DELETE'
                });
                const data = await response.json();
                showRulesStatus(`Rule deleted. ${data.affected_transactions} transactions flagged for review.`, 'success');
                row.remove();

                // Check if table is empty
                if (tbody.children.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="3">No rules configured.</td></tr>';
                }
            } catch (e) {
                showRulesStatus('Error deleting: ' + e.message, 'error');
            }
        });
    });
}

async function createRule(pattern, categoryId) {
    const response = await apiRequest('/rules', {
        method: 'POST',
        body: JSON.stringify({ pattern, category_id: categoryId })
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.message || 'Failed to create rule');
    }

    return await response.json();
}

function showRulesStatus(message, type) {
    const statusEl = document.getElementById('rules-status');
    statusEl.textContent = message;
    statusEl.className = `status-message ${type}`;
    statusEl.classList.remove('hidden');

    setTimeout(() => {
        statusEl.classList.add('hidden');
    }, 3000);
}

// =============================================================================
// My Account / Unit Statement Functions
// =============================================================================

let selectedUnit = null;
let paymentHistoryTable = null;
let statementRequestId = 0;  // Tracks current request to prevent race conditions

function initUnitSelector() {
    const selector = document.getElementById('unit-selector');
    if (!selector) return;

    // Restore saved selection from localStorage
    const savedUnit = localStorage.getItem('dwcoa_selected_unit');
    if (savedUnit) {
        selector.value = savedUnit;
        selectedUnit = savedUnit;
        loadStatement(savedUnit);
    }

    // Handle unit selection change
    selector.addEventListener('change', async () => {
        const unit = selector.value;
        if (unit) {
            selectedUnit = unit;
            localStorage.setItem('dwcoa_selected_unit', unit);
            await loadStatement(unit);
        } else {
            selectedUnit = null;
            localStorage.removeItem('dwcoa_selected_unit');
            hideMyAccountSection();
        }
    });
}

function hideMyAccountSection() {
    const section = document.getElementById('my-account-section');
    if (section) section.classList.add('hidden');
}

async function loadStatement(unit) {
    if (!unit) {
        hideMyAccountSection();
        return;
    }

    // Track this request to handle race conditions
    const requestId = ++statementRequestId;

    try {
        // Fetch both statement data and full payment history in parallel
        const [statementResponse, paymentsResponse] = await Promise.all([
            apiRequest(`/statement/${unit}`),
            apiRequest(`/statement/${unit}/payments`)
        ]);

        // Check if this request is still current (user may have changed selection)
        if (requestId !== statementRequestId) {
            return;  // A newer request was made, ignore this stale result
        }

        if (!statementResponse.ok) {
            const error = await statementResponse.json();
            console.error('Failed to load statement:', error);
            return;
        }

        const statementData = await statementResponse.json();
        const paymentsData = paymentsResponse.ok ? await paymentsResponse.json() : { payments: [] };

        renderMyAccount(statementData, paymentsData.payments || []);
    } catch (e) {
        // Only log error if this was the current request
        if (requestId === statementRequestId) {
            console.error('Failed to load statement:', e);
        }
    }
}

function renderMyAccount(data, payments) {
    const section = document.getElementById('my-account-section');
    if (!section) return;

    // Show the section
    section.classList.remove('hidden');

    // ==========================================================================
    // Budget lock notice - uses dashboard's budget lock status for consistency
    // with the selected snapshot date year
    // ==========================================================================
    const noticeEl = document.getElementById('my-account-notice');
    if (noticeEl) {
        if (!dashboardBudgetLocked) {
            noticeEl.textContent = `Budget for ${dashboardYear} is pending approval. Amounts shown are preliminary.`;
            noticeEl.classList.remove('hidden');
        } else {
            noticeEl.classList.add('hidden');
        }
    }

    // ==========================================================================
    // Summary Table (2025 and 2026 rows)
    // ==========================================================================
    const summaryBody = document.getElementById('statement-summary-body');
    let tableRows = '';

    // 2025 row (prior year)
    if (data.prior_year) {
        // Calculate starting balance for 2025: balance_carried_forward - budgeted + paid = historical debt
        const startingBalance2025 = data.prior_year.balance_carried_forward - data.prior_year.annual_dues_budgeted + data.prior_year.total_paid;
        const currentBalance2025 = data.prior_year.balance_carried_forward;

        tableRows += `
            <tr>
                <td>${data.prior_year.year}</td>
                <td>${formatCurrency(startingBalance2025)}</td>
                <td>${formatCurrency(data.prior_year.annual_dues_budgeted)}</td>
                <td>${formatCurrency(data.prior_year.total_paid)}</td>
                <td class="${currentBalance2025 > 0 ? 'negative' : currentBalance2025 < 0 ? 'positive' : ''}">${formatCurrency(currentBalance2025)}</td>
            </tr>
        `;
    }

    // 2026 row (current year)
    const startingBalance2026 = data.current_year.carryover_balance;
    const currentBalance2026 = data.current_year.remaining_balance;

    tableRows += `
        <tr>
            <td>${data.current_year.year}</td>
            <td>${formatCurrency(startingBalance2026)}</td>
            <td>${formatCurrency(data.current_year.annual_dues)}</td>
            <td>${formatCurrency(data.current_year.paid_ytd)}</td>
            <td class="${currentBalance2026 > 0 ? 'negative' : currentBalance2026 < 0 ? 'positive' : ''}">${formatCurrency(currentBalance2026)}</td>
        </tr>
    `;

    summaryBody.innerHTML = tableRows;

    // ==========================================================================
    // Payment Info (consolidated row)
    // ==========================================================================
    const remaining = data.current_year.remaining_balance;
    const paidInFullMsg = document.getElementById('paid-in-full-message');
    const creditBalanceMsg = document.getElementById('credit-balance-message');
    const monthsEl = document.getElementById('months-remaining');
    const originalMonthlyEl = document.getElementById('original-monthly');
    const suggestedEl = document.getElementById('suggested-monthly');

    // Always show original monthly (annual / 12)
    originalMonthlyEl.textContent = formatCurrency(data.current_year.original_monthly || 0);

    // Get the info items that show payment amounts (not unit selector)
    const paymentInfoItems = document.querySelectorAll('#payment-info-section .info-item:not(:first-child)');

    if (remaining <= 0) {
        // Hide the payment guidance items (months, original, suggested)
        paymentInfoItems.forEach(item => item.classList.add('hidden'));

        if (remaining < 0) {
            // Credit balance
            creditBalanceMsg.classList.remove('hidden');
            paidInFullMsg.classList.add('hidden');
            document.getElementById('credit-amount').textContent = formatCurrency(Math.abs(remaining));
        } else {
            // Exactly zero - paid in full
            paidInFullMsg.classList.remove('hidden');
            creditBalanceMsg.classList.add('hidden');
        }
    } else {
        // Show the payment info items
        paymentInfoItems.forEach(item => item.classList.remove('hidden'));
        paidInFullMsg.classList.add('hidden');
        creditBalanceMsg.classList.add('hidden');

        const monthsRemaining = data.current_year.months_remaining;

        if (monthsRemaining <= 1) {
            // December or past year end
            monthsEl.textContent = `Due by Dec 31`;
        } else {
            monthsEl.textContent = monthsRemaining;
        }

        suggestedEl.textContent = formatCurrency(data.current_year.suggested_monthly);
    }

    // ==========================================================================
    // Payment History (Tabulator)
    // ==========================================================================
    initPaymentHistoryTable(payments);
}

// Payment History Tabulator
function initPaymentHistoryTable(payments) {
    const tableEl = document.getElementById('payment-history-table');
    if (!tableEl) return;

    // Destroy existing table if it exists
    if (paymentHistoryTable) {
        paymentHistoryTable.destroy();
        paymentHistoryTable = null;
    }

    if (!payments || payments.length === 0) {
        tableEl.innerHTML = '<p class="no-data">No payments recorded.</p>';
        return;
    }

    if (typeof Tabulator === 'undefined') {
        tableEl.innerHTML = '<p class="error">Error: Tabulator library not loaded.</p>';
        return;
    }

    paymentHistoryTable = new Tabulator("#payment-history-table", {
        data: payments,
        layout: "fitColumns",
        responsiveLayout: "collapse",
        pagination: true,
        paginationSize: 10,
        paginationSizeSelector: [10, 25, 50],
        initialSort: [{ column: "date", dir: "desc" }],
        placeholder: "No payments recorded",
        columns: [
            {
                title: "Post Date",
                field: "date",
                sorter: function(a, b) {
                    return a.localeCompare(b);
                },
                width: 120
            },
            {
                title: "Description",
                field: "description",
                sorter: "string"
            },
            {
                title: "Amount",
                field: "amount",
                sorter: "number",
                hozAlign: "right",
                formatter: function(cell) {
                    const val = cell.getValue();
                    return formatCurrency(val);
                },
                width: 120
            }
        ]
    });
}
