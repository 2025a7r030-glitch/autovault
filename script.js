// State Management
let logs = JSON.parse(localStorage.getItem('vehicleLogs')) || [];

// DOM Elements
const form = document.getElementById('tracker-form');
const dateInput = document.getElementById('date');
const odometerInput = document.getElementById('odometer');
const fuelAmountInput = document.getElementById('fuel-amount');
const fuelPriceInput = document.getElementById('fuel-price');
const clearBtn = document.getElementById('clear-btn');
const clearAllBtn = document.getElementById('clear-all-btn');
const historyBody = document.getElementById('history-body');
const emptyState = document.getElementById('empty-state');

// Warning & Chart Elements
const warningAlert = document.getElementById('mileage-warning');
const closeAlertBtn = document.getElementById('close-alert-btn');
const alertMileageVal = document.getElementById('alert-mileage-val');

const expenseWarning = document.getElementById('expense-warning');
const closeExpenseBtn = document.getElementById('close-expense-btn');
const alertExpenseVal = document.getElementById('alert-expense-val');

let consumptionChart = null;

// Thresholds
const LOW_MILEAGE_WARNING_THRESHOLD = 27;
const HIGH_EXPENSE_THRESHOLD = 4500;

// Stats Elements
const totalDistanceEl = document.getElementById('total-distance');
const totalExpenseEl = document.getElementById('total-expense');
const avgMileageEl = document.getElementById('avg-mileage');

// Set today's date as default
dateInput.valueAsDate = new Date();

// Initialize App
function init() {
    // Sort logs by odometer descending (newest first)
    logs.sort((a, b) => b.odometer - a.odometer);
    renderHistory();
    updateStats();
}

// Generate unique ID
function generateId() {
    return Math.random().toString(36).substring(2, 9);
}

// Add a new log
function addLog(e) {
    e.preventDefault();

    const date = dateInput.value;
    const odometer = parseFloat(odometerInput.value);
    const fuelAmount = parseFloat(fuelAmountInput.value);
    const fuelPrice = parseFloat(fuelPriceInput.value);

    // Validation
    if (!date || isNaN(odometer) || isNaN(fuelAmount) || isNaN(fuelPrice)) {
        alert("Please fill in all fields with valid numbers.");
        return;
    }

    if (logs.length > 0) {
        // check if new odometer is less than highest previous
        const highestOdo = Math.max(...logs.map(log => log.odometer));
        /* Allow backfilling but typical use case assumes incremental. We'll allow it anyway
           but we calculate mileage based on sorted odometer readings */
    }

    const totalCost = fuelAmount * fuelPrice;

    const newLog = {
        id: generateId(),
        date,
        odometer,
        fuelAmount,
        fuelPrice,
        totalCost,
        timestamp: Date.now()
    };

    logs.push(newLog);
    // Sort logs by odometer descending (newest at index 0)
    logs.sort((a, b) => b.odometer - a.odometer);

    updateLocalStorage();
    renderHistory();
    updateStats();
    
    // Clear inputs except date
    odometerInput.value = '';
    fuelAmountInput.value = '';
    fuelPriceInput.value = '';
    odometerInput.focus();
}

// Calculate mileage for a specific log
// Mileage is calculated as (Current Odo - Previous Odo) / Current Fuel
function calculateMileageForLog(logIndex) {
    if (logIndex >= logs.length - 1) return null; // Can't calculate for oldest record
    
    const currentLog = logs[logIndex];
    const previousLog = logs[logIndex + 1]; // Reminder: array is sorted descending by odometer
    
    const distance = currentLog.odometer - previousLog.odometer;
    if (currentLog.fuelAmount <= 0) return null;
    
    const mileage = distance / currentLog.fuelAmount;
    return mileage;
}

// Update Dashboard Statistics
function updateStats() {
    if (logs.length === 0) {
        totalDistanceEl.innerHTML = `0 <span class="unit">km</span>`;
        totalExpenseEl.innerHTML = `<span class="currency">₹</span>0.00`;
        avgMileageEl.innerHTML = `0 <span class="unit">km/L</span>`;
        return;
    }

    // Total Expense
    const totalEx = logs.reduce((acc, log) => acc + log.totalCost, 0);
    totalExpenseEl.innerHTML = `<span class="currency">₹</span>${totalEx.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;

    // Total Distance & Avg Mileage
    if (logs.length > 1) {
        // array is sorted desc, so idx 0 is highest, idx length-1 is lowest
        const highestOdo = logs[0].odometer;
        const lowestOdo = logs[logs.length - 1].odometer;
        const distance = highestOdo - lowestOdo;
        
        totalDistanceEl.innerHTML = `${distance.toLocaleString()} <span class="unit">km</span>`;

        // Avg Mileage = Total Distance / Total Fuel Used (excluding the oldest record's fuel as it filled the tank for the *next* trip usually, but let's just sum all but the oldest record)
        let totalFuelUsed = 0;
        for (let i = 0; i < logs.length - 1; i++) {
            totalFuelUsed += logs[i].fuelAmount;
        }

        if (totalFuelUsed > 0 && distance > 0) {
            const avgMil = distance / totalFuelUsed;
            avgMileageEl.innerHTML = `${avgMil.toFixed(2)} <span class="unit">km/L</span>`;
        } else {
            avgMileageEl.innerHTML = `0 <span class="unit">km/L</span>`;
        }
    } else {
        totalDistanceEl.innerHTML = `0 <span class="unit">km</span>`;
        avgMileageEl.innerHTML = `0 <span class="unit">km/L</span>`;
    }
    
    updateChart();
    checkWarning();
}

// Check Warning Logic
function checkWarning() {
    let showMileageWarning = false;
    let showExpenseWarning = false;

    if (logs.length >= 2) {
        // Check the most recent calculated mileage
        const recentMileage = calculateMileageForLog(0);
        if (recentMileage !== null && recentMileage < LOW_MILEAGE_WARNING_THRESHOLD) {
            alertMileageVal.textContent = recentMileage.toFixed(2);
            showMileageWarning = true;
        }
    }

    if (logs.length > 0) {
        // Check current month expense
        const currentMonth = new Date().getMonth();
        const currentYear = new Date().getFullYear();
        let monthlyExpense = 0;

        for (const log of logs) {
            const logDate = new Date(log.date);
            if (logDate.getMonth() === currentMonth && logDate.getFullYear() === currentYear) {
                monthlyExpense += log.totalCost;
            }
        }

        if (monthlyExpense > HIGH_EXPENSE_THRESHOLD) {
            alertExpenseVal.textContent = monthlyExpense.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
            showExpenseWarning = true;
        }
    }

    warningAlert.style.display = showMileageWarning ? 'flex' : 'none';
    expenseWarning.style.display = showExpenseWarning ? 'flex' : 'none';
}

// Update Chart Logic
function updateChart() {
    const ctx = document.getElementById('consumption-chart');
    if (!ctx) return;
    
    // Categorize mileage across all recorded trips
    let optimal = 0; // >= 30 km/l
    let average = 0; // 25 - 29.9 km/l
    let highConsumption = 0; // < 25 km/l
    
    for (let i = 0; i < logs.length - 1; i++) {
        const mileage = calculateMileageForLog(i);
        if (mileage !== null) {
            if (mileage >= 30) optimal++;
            else if (mileage >= 25) average++;
            else highConsumption++;
        }
    }
    
    const hasData = (optimal + average + highConsumption) > 0;
    const chartData = hasData ? [optimal, average, highConsumption] : [1, 1, 1];
    const bgColors = hasData 
        ? ['#10b981', '#f59e0b', '#ef4444'] 
        : ['rgba(255,255,255,0.05)', 'rgba(255,255,255,0.05)', 'rgba(255,255,255,0.05)'];
    
    if (consumptionChart) {
        consumptionChart.data.labels = hasData ? ['Optimal (>=30 km/l)', 'Average (25-29.9)', 'High (<25)'] : ['No Data', 'No Data', 'No Data'];
        consumptionChart.data.datasets[0].data = chartData;
        consumptionChart.data.datasets[0].backgroundColor = bgColors;
        consumptionChart.options.plugins.tooltip.enabled = hasData;
        consumptionChart.update();
    } else {
        consumptionChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: hasData ? ['Optimal (>=30 km/l)', 'Average (25-29.9)', 'High (<25)'] : ['No Data', 'No Data', 'No Data'],
                datasets: [{
                    data: chartData,
                    backgroundColor: bgColors,
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#94a3b8', font: { family: "'Inter', sans-serif" } }
                    },
                    tooltip: {
                        enabled: hasData,
                        callbacks: {
                            label: function(context) {
                                return ` ${context.label}: ${context.raw} log(s)`;
                            }
                        }
                    }
                },
                cutout: '70%'
            }
        });
    }
}

// Render History Table
function renderHistory() {
    historyBody.innerHTML = '';
    
    if (logs.length === 0) {
        document.getElementById('history-table').style.display = 'none';
        emptyState.classList.add('active');
        return;
    }

    document.getElementById('history-table').style.display = 'table';
    emptyState.classList.remove('active');

    logs.forEach((log, index) => {
        const tr = document.createElement('tr');
        
        // Format date
        const dateObj = new Date(log.date);
        const formattedDate = dateObj.toLocaleDateString(undefined, { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });

        const mileage = calculateMileageForLog(index);
        const mileageHtml = mileage 
            ? `<span class="badge">${mileage.toFixed(2)} km/l</span>` 
            : `<span class="badge badge-na">N/A</span>`;

        tr.innerHTML = `
            <td>${formattedDate}</td>
            <td class="col-num">${log.odometer.toLocaleString()} km</td>
            <td class="col-num">${log.fuelAmount.toFixed(2)} L</td>
            <td class="col-num">₹${log.fuelPrice.toFixed(2)}</td>
            <td class="col-num" style="font-weight: 600; color: var(--accent-primary);">₹${log.totalCost.toFixed(2)}</td>
            <td>${mileageHtml}</td>
            <td>
                <button class="btn btn-icon" onclick="deleteLog('${log.id}')" title="Delete record">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/></svg>
                </button>
            </td>
        `;
        
        historyBody.appendChild(tr);
    });
}

// Delete Log
function deleteLog(id) {
    if (confirm('Are you sure you want to delete this log?')) {
        logs = logs.filter(log => log.id !== id);
        updateLocalStorage();
        init();
    }
}

// Clear all logs
function clearAllLogs() {
    if (logs.length > 0 && confirm('Are you sure you want to delete ALL logs? This cannot be undone.')) {
        logs = [];
        updateLocalStorage();
        init();
    }
}

// Update Local Storage
function updateLocalStorage() {
    localStorage.setItem('vehicleLogs', JSON.stringify(logs));
}

// Event Listeners
if (closeAlertBtn) {
    closeAlertBtn.addEventListener('click', () => {
        warningAlert.style.display = 'none';
    });
}
if (closeExpenseBtn) {
    closeExpenseBtn.addEventListener('click', () => {
        expenseWarning.style.display = 'none';
    });
}

form.addEventListener('submit', addLog);
clearBtn.addEventListener('click', () => {
    odometerInput.value = '';
    fuelAmountInput.value = '';
    fuelPriceInput.value = '';
});
clearAllBtn.addEventListener('click', clearAllLogs);

// Initialize on load
init();
