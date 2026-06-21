// ==========================================================================
// Web App JavaScript: FTE Payroll & Productivity Dashboard
// Supports Summarize Dashboard, Detail Explorer, and Supabase Integration
// ==========================================================================

// Global state
let dbConfig = { url: 'https://etdwppqkjloghkcyifpq.supabase.co', anonKey: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV0ZHdwcHFramxvZ2hrY3lpZnBxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjAyMDgzOSwiZXhwIjoyMDk3NTk2ODM5fQ.ckMi3USy2J22gy7amqojMA7dEtsYjer_TC6lI59rl6g' };
let isConnected = true;
let monthlySummaries = []; // Stores monthly summary records
let activeView = 'dashboard'; // 'dashboard', 'detail', 'config'
let globalLatestDate = '2026-06-20'; // Latest date in raw dataset for incomplete month projections

// Chart instances
let monthlyVolChart = null;
let monthlyFteChart = null;
let monthlyProdChart = null;
let dailyVolChart = null;
let dailyFteChart = null;
let dailyProdChart = null;

// DOM Elements
const views = {
    dashboard: document.getElementById('view-dashboard'),
    detail: document.getElementById('view-data'),
    config: document.getElementById('view-config')
};
const navItems = {
    dashboard: document.getElementById('btn-dash'),
    detail: document.getElementById('btn-data'),
    config: document.getElementById('btn-config')
};
const pageTitle = document.getElementById('page-title');
const pageSubtitle = document.getElementById('page-subtitle');
const dbStatus = document.getElementById('db-status');
const dbStatusText = dbStatus.querySelector('.status-text');

// Initialize application
document.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    setupNavigation();
    setupConfigForm();
    setupFilterListeners();
    
    // Load initial data
    refreshData();
});

// ==========================================
// 1. Navigation Setup
// ==========================================
function setupNavigation() {
    navItems.dashboard.addEventListener('click', (e) => {
        e.preventDefault();
        switchView('dashboard');
    });
    navItems.detail.addEventListener('click', (e) => {
        e.preventDefault();
        switchView('detail');
    });
    navItems.config.addEventListener('click', (e) => {
        e.preventDefault();
        switchView('config');
    });
    
    document.getElementById('btn-refresh').addEventListener('click', () => {
        refreshData();
    });
}

function switchView(viewName) {
    activeView = viewName;
    
    // Update active tab buttons
    Object.keys(navItems).forEach(key => {
        if (key === viewName) {
            navItems[key].classList.add('active');
        } else {
            navItems[key].classList.remove('active');
        }
    });
    
    // Update view visibility
    Object.keys(views).forEach(key => {
        if (key === viewName) {
            views[key].classList.add('active');
        } else {
            views[key].classList.remove('active');
        }
    });
    
    // Update titles and load data if needed
    if (viewName === 'dashboard') {
        pageTitle.textContent = "บอร์ดสรุปประสิทธิภาพภาพรวม (Summarize Dashboard)";
        pageSubtitle.textContent = "เปรียบเทียบชั่วโมงทำงาน FTE และปริมาณผลผลิตจำแนกตามแผนกและศูนย์ต้นทุน";
        renderSummarizeDashboard();
    } else if (viewName === 'detail') {
        pageTitle.textContent = "เจาะลึกรายละเอียดรายศูนย์ต้นทุน (Detail Explorer)";
        pageSubtitle.textContent = "วิเคราะห์เจาะลึกข้อมูล FTE รายวัน ปริมาณงาน และอัตราประสิทธิภาพรายวัน";
        updateDetailExplorer();
    } else if (viewName === 'config') {
        pageTitle.textContent = "การตั้งค่าการเชื่อมต่อ (Credentials Setup)";
        pageSubtitle.textContent = "กำหนดข้อมูลสิทธิ์การเชื่อมต่อเพื่อดึงข้อมูลสดจาก Supabase Project ของคุณ";
    }
}

// ==========================================
// 2. Credentials Configuration
// ==========================================
const DEFAULT_SUPABASE_URL = 'https://etdwppqkjloghkcyifpq.supabase.co';
const DEFAULT_SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV0ZHdwcHFramxvZ2hrY3lpZnBxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4MjAyMDgzOSwiZXhwIjoyMDk3NTk2ODM5fQ.ckMi3USy2J22gy7amqojMA7dEtsYjer_TC6lI59rl6g';

function loadConfig() {
    let savedUrl = localStorage.getItem('supabase_url') || DEFAULT_SUPABASE_URL;
    let savedKey = localStorage.getItem('supabase_anon_key') || DEFAULT_SUPABASE_KEY;
    
    if (savedUrl && savedKey) {
        dbConfig.url = savedUrl;
        dbConfig.anonKey = savedKey;
        
        document.getElementById('supabase-url').value = savedUrl;
        document.getElementById('supabase-anon-key').value = savedKey;
        setConnectionStatus(true);
    } else {
        document.getElementById('supabase-url').value = savedUrl;
        setConnectionStatus(false);
    }
}

function setConnectionStatus(connected) {
    isConnected = connected;
    if (connected) {
        dbStatus.classList.add('connected');
        dbStatusText.textContent = "Supabase Connected";
    } else {
        dbStatus.classList.remove('connected');
        dbStatusText.textContent = "Running Mock Mode";
    }
}

function setupConfigForm() {
    const form = document.getElementById('config-form');
    const btnClear = document.getElementById('btn-clear-config');
    
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const url = document.getElementById('supabase-url').value.trim();
        const key = document.getElementById('supabase-anon-key').value.trim();
        
        localStorage.setItem('supabase_url', url);
        localStorage.setItem('supabase_anon_key', key);
        
        dbConfig.url = url;
        dbConfig.anonKey = key;
        
        setConnectionStatus(true);
        alert("บันทึกข้อมูลการเชื่อมต่อเรียบร้อย!");
        refreshData();
        switchView('dashboard');
    });
    
    btnClear.addEventListener('click', () => {
        if (confirm("คุณต้องการล้างข้อมูลการเชื่อมต่อและกลับไปใช้ Mock Mode หรือไม่?")) {
            localStorage.removeItem('supabase_url');
            localStorage.removeItem('supabase_anon_key');
            dbConfig = { url: '', anonKey: '' };
            document.getElementById('supabase-url').value = '';
            document.getElementById('supabase-anon-key').value = '';
            setConnectionStatus(false);
            refreshData();
            switchView('dashboard');
        }
    });
}

// ==========================================
// 3. Filter Change Listeners
// ==========================================
function setupFilterListeners() {
    // Dashboard Filters
    document.getElementById('dash-filter-dept').addEventListener('change', () => {
        renderSummarizeDashboard();
    });
    document.getElementById('dash-filter-month').addEventListener('change', () => {
        renderSummarizeDashboard();
    });
    
    // Detail Filters
    document.getElementById('detail-filter-cc').addEventListener('change', () => {
        updateDetailExplorer();
    });
    document.getElementById('detail-filter-month').addEventListener('change', () => {
        updateDetailExplorer();
    });
}

// ==========================================
// 4. Data Retrieval & Projections
// ==========================================
async function refreshData() {
    const refreshBtn = document.getElementById('btn-refresh');
    refreshBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> กำลังโหลด...`;
    refreshBtn.disabled = true;

    if (isConnected) {
        try {
            console.log("Fetching summaries from Supabase...");
            const queryUrl = `${dbConfig.url}/rest/v1/monthly_productivity_summary?select=*&order=month.desc,cost_center.asc`;
            
            const response = await fetch(queryUrl, {
                method: 'GET',
                headers: {
                    'apikey': dbConfig.anonKey,
                    'Authorization': `Bearer ${dbConfig.anonKey}`
                }
            });
            
            if (!response.ok) throw new Error("Supabase request failed");
            
            monthlySummaries = await response.json();
            console.log(`Successfully fetched ${monthlySummaries.length} summaries`);
            
            // Query latest work date in Supabase
            try {
                const maxDateUrl = `${dbConfig.url}/rest/v1/productivity_report?select=work_date&order=work_date.desc&limit=1`;
                const maxDateRes = await fetch(maxDateUrl, {
                    method: 'GET',
                    headers: {
                        'apikey': dbConfig.anonKey,
                        'Authorization': `Bearer ${dbConfig.anonKey}`
                    }
                });
                if (maxDateRes.ok) {
                    const maxDateData = await maxDateRes.json();
                    if (maxDateData && maxDateData.length > 0) {
                        globalLatestDate = maxDateData[0].work_date;
                        console.log("Latest date in database:", globalLatestDate);
                    }
                }
            } catch (err) {
                console.error("Failed to query latest date in Supabase:", err);
            }
            
            // Render dashboard
            renderSummarizeDashboard();
        } catch (error) {
            console.error("Supabase fetch failed, falling back to mock mode:", error);
            alert("ไม่สามารถดึงข้อมูลจาก Supabase ได้ ระบบจะเปิดใช้งานโหมดจำลอง (Mock Mode)");
            setConnectionStatus(false);
            loadFallbackMockData();
        }
    } else {
        loadFallbackMockData();
    }
    
    setTimeout(() => {
        refreshBtn.innerHTML = `<i class="fa-solid fa-arrows-rotate"></i> ดึงข้อมูลล่าสุด`;
        refreshBtn.disabled = false;
    }, 600);
}

function loadFallbackMockData() {
    console.log("Loading summaries from local mock_data.js");
    if (typeof MOCK_MONTHLY_SUMMARIES !== 'undefined') {
        monthlySummaries = MOCK_MONTHLY_SUMMARIES;
    } else {
        console.warn("MOCK_MONTHLY_SUMMARIES not loaded! Generating fallback structure.");
        monthlySummaries = [];
    }
    // Dynamically find latest date in mock data daily records
    if (typeof MOCK_DAILY_RECORDS !== 'undefined' && MOCK_DAILY_RECORDS.length > 0) {
        const juneRecs = MOCK_DAILY_RECORDS.filter(r => r.work_date.startsWith('2026-06') && parseFloat(r.volume || 0) > 0);
        if (juneRecs.length > 0) {
            globalLatestDate = juneRecs.map(r => r.work_date).sort().pop();
            console.log("Latest date in mock data:", globalLatestDate);
        }
    }
    renderSummarizeDashboard();
}

// ==========================================
// 5. Page 1: Render Summarize Dashboard
// ==========================================
function renderSummarizeDashboard() {
    const dept = document.getElementById('dash-filter-dept').value;
    const month = document.getElementById('dash-filter-month').value;
    
    // Filter records
    const deptSummaries = monthlySummaries.filter(s => s.group_type === dept && s.month === month);
    
    // Find bottom line row (cc = '99999') and individual rows
    const bottomLineRow = deptSummaries.find(s => s.cost_center === '99999');
    const individualRows = deptSummaries.filter(s => s.cost_center !== '99999');
    
    const tableBody = document.getElementById('summary-table-body');
    const badgeArea = document.getElementById('projection-badge-area');
    
    if (deptSummaries.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="16" class="empty-state">ไม่มีข้อมูลในรอบเดือนและแผนกนี้...</td></tr>`;
        badgeArea.innerHTML = '';
        updateKPIStats(0, 0, 0, 0);
        return;
    }
    
    // Determine calendar days and check if projection applies (e.g. latest month June 2026)
    const daysInMonth = (month === '2026-05') ? 31 : 30; // June is 30, May is 31
    const daysWithVol = bottomLineRow ? (bottomLineRow.days_with_volume || 0) : 0;
    const isJune = (month === '2026-06');
    const isJuneIncomplete = isJune && (daysWithVol < daysInMonth);
    
    // Scale factor for Landing FTEs and Volume based on working day calendars
    let scaleNormal = 1.0;
    let scaleOS = 1.0;
    if (isJuneIncomplete) {
        const year = 2026;
        const monthIdx = 5; // June is 5
        let endDay = 20; // fallback
        if (globalLatestDate && globalLatestDate.startsWith(month)) {
            endDay = parseInt(globalLatestDate.substring(8, 10));
        }
        
        const totalNormalWd = getWorkingDays(year, monthIdx, 'normal');
        const elapsedNormalWd = getWorkingDays(year, monthIdx, 'normal', endDay);
        scaleNormal = elapsedNormalWd > 0 ? (totalNormalWd / elapsedNormalWd) : 1.0;
        
        const totalOSWd = getWorkingDays(year, monthIdx, 'os');
        const elapsedOSWd = getWorkingDays(year, monthIdx, 'os', endDay);
        scaleOS = elapsedOSWd > 0 ? (totalOSWd / elapsedOSWd) : 1.0;
    }
    
    // Render projection status badge
    if (isJuneIncomplete) {
        let displayDate = "20/06/2026";
        if (globalLatestDate) {
            const parts = globalLatestDate.split('-');
            if (parts.length === 3) {
                displayDate = `${parts[2]}/${parts[1]}/${parts[0]}`;
            }
        }
        badgeArea.innerHTML = `
            <div class="projection-alert">
                <i class="fa-solid fa-triangle-exclamation"></i>
                กำลังประมาณการยอดปลายเดือน: ข้อมูล ณ วันที่ ${displayDate} (มีปริมาณงาน ${daysWithVol} วันจาก ${daysInMonth} วันปฏิทิน)
            </div>
        `;
    } else {
        badgeArea.innerHTML = `
            <div class="year-badge" style="background: rgba(62, 207, 142, 0.1); border-color: rgba(62, 207, 142, 0.2); color: var(--accent-color);">
                <i class="fa-solid fa-circle-check"></i> ข้อมูลเสร็จสมบูรณ์ (${daysWithVol}/${daysInMonth} วัน)
            </div>
        `;
    }
    
    // Helper to format values (rounded to whole integers)
    const formatFTE = (v) => Math.round(parseFloat(v || 0)).toLocaleString('th-TH');
    const formatVol = (v) => Math.round(parseFloat(v || 0)).toLocaleString('th-TH');
    const formatProd = (v) => Math.round(parseFloat(v || 0)).toLocaleString('th-TH');
    
    // Calculate total net FTE (Actual vs Landing)
    let actNetFte = bottomLineRow ? parseFloat(bottomLineRow.net_total_fte) : 0;
    
    // Calculate Landing values for bottom line
    let landingNetFte = actNetFte;
    if (isJuneIncomplete && bottomLineRow) {
        // Recalculate Landing Net FTE by scaling hourly components
        const fte_norm = parseFloat(bottomLineRow.fte_normal || 0);
        const fte_ot_l = parseFloat(bottomLineRow.fte_ot || 0) * scaleNormal;
        const dep_norm_l = parseFloat(bottomLineRow.adjust_norm_minus || 0) * scaleNormal;
        const dep_ot_l = parseFloat(bottomLineRow.adjust_ot_minus || 0) * scaleNormal;
        const dest_norm_l = parseFloat(bottomLineRow.adjust_norm_plus || 0) * scaleNormal;
        const dest_ot_l = parseFloat(bottomLineRow.adjust_ot_plus || 0) * scaleNormal;
        const os_norm_l = parseFloat(bottomLineRow.os_norm || 0) * scaleOS;
        const os_ot_l = parseFloat(bottomLineRow.os_ot || 0) * scaleOS;
        
        landingNetFte = (fte_norm - dep_norm_l + dest_norm_l + os_norm_l) + (fte_ot_l - dep_ot_l + dest_ot_l + os_ot_l);
    }
    
    const actVol = bottomLineRow ? parseFloat(bottomLineRow.volume) : 0;
    let landingVol = actVol;
    if (isJuneIncomplete) {
        landingVol = actVol * scaleNormal;
    }
    
    const landingProd = landingNetFte > 0 ? (landingVol / landingNetFte) : 0;
    
    // Update top KPI cards on Page 1 (FTE shows Landing version if incomplete)
    const actProd = actNetFte > 0 ? (actVol / actNetFte) : 0;
    updateKPIStats(isJuneIncomplete ? landingNetFte : actNetFte, actVol, landingVol, actProd, landingProd);
    
    // Populate summary table
    let tableRowsHtml = "";
    
    // Render individual cost center rows
    individualRows.forEach(row => {
        const ccNetFte = parseFloat(row.net_total_fte || 0);
        const ccActVol = parseFloat(row.volume || 0);
        
        let ccLandingVol = ccActVol;
        let ccLandingNetFte = ccNetFte;
        
        // Scale FTE components if June is incomplete
        let fte_ot_disp = parseFloat(row.fte_ot || 0);
        let dep_norm_disp = parseFloat(row.adjust_norm_minus || 0);
        let dep_ot_disp = parseFloat(row.adjust_ot_minus || 0);
        let dest_norm_disp = parseFloat(row.adjust_norm_plus || 0);
        let dest_ot_disp = parseFloat(row.adjust_ot_plus || 0);
        let os_norm_disp = parseFloat(row.os_norm || 0);
        let os_ot_disp = parseFloat(row.os_ot || 0);
        
        if (isJuneIncomplete) {
            ccLandingVol = ccActVol * scaleNormal;
            
            fte_ot_disp *= scaleNormal;
            dep_norm_disp *= scaleNormal;
            dep_ot_disp *= scaleNormal;
            dest_norm_disp *= scaleNormal;
            dest_ot_disp *= scaleNormal;
            os_norm_disp *= scaleOS;
            os_ot_disp *= scaleOS;
            
            ccLandingNetFte = (parseFloat(row.fte_normal || 0) - dep_norm_disp + dest_norm_disp + os_norm_disp) + 
                               (fte_ot_disp - dep_ot_disp + dest_ot_disp + os_ot_disp);
        }
        
        const ccActProd = ccNetFte > 0 ? (ccActVol / ccNetFte) : 0;
        const ccLandingProd = ccLandingNetFte > 0 ? (ccLandingVol / ccLandingNetFte) : 0;
        
        tableRowsHtml += `
            <tr onclick="drillDownToCC('${row.cost_center}', '${month}')">
                <td>${row.month}</td>
                <td><strong style="color: var(--info); text-decoration: underline;">${row.cost_center}</strong></td>
                <td>${row.cost_center_name || 'Unknown'}</td>
                <td class="highlight-col">${formatFTE(isJuneIncomplete ? ccLandingNetFte : ccNetFte)}</td>
                <td>${formatVol(ccActVol)}</td>
                <td>${formatVol(ccLandingVol)}</td>
                <td>${formatProd(ccActProd)}</td>
                <td>${formatProd(ccLandingProd)}</td>
                <td>${Math.round(parseFloat(row.fte_normal || 0)).toLocaleString('th-TH')}</td>
                <td>${formatFTE(fte_ot_disp)}</td>
                <td>${formatFTE(dep_norm_disp)}</td>
                <td>${formatFTE(dep_ot_disp)}</td>
                <td>${formatFTE(dest_norm_disp)}</td>
                <td>${formatFTE(dest_ot_disp)}</td>
                <td>${formatFTE(os_norm_disp)}</td>
                <td>${formatFTE(os_ot_disp)}</td>
            </tr>
        `;
    });
    
    // Render bottom line row with renamed Cost Center label
    if (bottomLineRow) {
        let fte_ot_disp = parseFloat(bottomLineRow.fte_ot || 0);
        let dep_norm_disp = parseFloat(bottomLineRow.adjust_norm_minus || 0);
        let dep_ot_disp = parseFloat(bottomLineRow.adjust_ot_minus || 0);
        let dest_norm_disp = parseFloat(bottomLineRow.adjust_norm_plus || 0);
        let dest_ot_disp = parseFloat(bottomLineRow.adjust_ot_plus || 0);
        let os_norm_disp = parseFloat(bottomLineRow.os_norm || 0);
        let os_ot_disp = parseFloat(bottomLineRow.os_ot || 0);
        
        if (isJuneIncomplete) {
            fte_ot_disp *= scaleNormal;
            dep_norm_disp *= scaleNormal;
            dep_ot_disp *= scaleNormal;
            dest_norm_disp *= scaleNormal;
            dest_ot_disp *= scaleNormal;
            os_norm_disp *= scaleOS;
            os_ot_disp *= scaleOS;
        }
        
        const actProd = actNetFte > 0 ? (actVol / actNetFte) : 0;
        
        // Use functional name for "99999" row
        const functionLabel = bottomLineRow.cost_center_name || 'Total Summary';
        
        tableRowsHtml += `
            <tr class="bottom-line-row">
                <td>${bottomLineRow.month}</td>
                <td><strong style="color: var(--accent-color);">${functionLabel}</strong></td>
                <td>(Bottom Line Summary)</td>
                <td class="highlight-col" style="color: var(--accent-color) !important;">${formatFTE(isJuneIncomplete ? landingNetFte : actNetFte)}</td>
                <td>${formatVol(actVol)}</td>
                <td>${formatVol(landingVol)}</td>
                <td>${formatProd(actProd)}</td>
                <td>${formatProd(landingProd)}</td>
                <td>${Math.round(parseFloat(bottomLineRow.fte_normal || 0)).toLocaleString('th-TH')}</td>
                <td>${formatFTE(fte_ot_disp)}</td>
                <td>${formatFTE(dep_norm_disp)}</td>
                <td>${formatFTE(dep_ot_disp)}</td>
                <td>${formatFTE(dest_norm_disp)}</td>
                <td>${formatFTE(dest_ot_disp)}</td>
                <td>${formatFTE(os_norm_disp)}</td>
                <td>${formatFTE(os_ot_disp)}</td>
            </tr>
        `;
    }
    
    tableBody.innerHTML = tableRowsHtml;
    
    // Get unique list of cost centers for the department
    const deptCcs = individualRows.map(r => r.cost_center);
    
    // Auto populate Detail page dropdown options with cost centers from this department
    populateDetailCCSelector(deptCcs, dept);
}

function updateKPIStats(netFte, actVol, landingVol, actProd, landingProd) {
    document.getElementById('stat-net-fte').textContent = Math.round(netFte).toLocaleString('th-TH');
    document.getElementById('stat-vol-actual').textContent = Math.round(actVol).toLocaleString('th-TH');
    document.getElementById('stat-vol-landing').textContent = Math.round(landingVol).toLocaleString('th-TH');
    document.getElementById('stat-prod-actual').textContent = Math.round(actProd).toLocaleString('th-TH');
    document.getElementById('stat-prod-landing').textContent = Math.round(landingProd).toLocaleString('th-TH');
}

function populateDetailCCSelector(ccs, dept) {
    const ccSelect = document.getElementById('detail-filter-cc');
    const prevVal = ccSelect.value;
    
    let optionsHtml = '<option value="">-- กรุณาเลือกศูนย์ต้นทุน --</option>';
    
    // Add bottom line summary option
    let grpLabel = "XD Productivity";
    if (dept === "WH_NO_CMG") grpLabel = "WH Productivity (ไม่รวม CMG/GG)";
    if (dept === "WH_YES_CMG") grpLabel = "WH Productivity (รวม CMG/GG)";
    if (dept === "Online") grpLabel = "Online Warehouse Productivity";
    optionsHtml += `<option value="99999">99999 - ${grpLabel}</option>`;
    
    // Add individual cost centers
    ccs.forEach(cc => {
        let ccName = "";
        const match = monthlySummaries.find(s => s.cost_center === cc);
        if (match) ccName = ` - ${match.cost_center_name}`;
        optionsHtml += `<option value="${cc}">${cc}${ccName}</option>`;
    });
    
    ccSelect.innerHTML = optionsHtml;
    
    // Preserve selected option if valid
    if (ccs.includes(prevVal) || prevVal === '99999') {
        ccSelect.value = prevVal;
    }
}

// ==========================================
// 6. Drill-Down Action: Click summary row to view details
// ==========================================
function drillDownToCC(costCenter, month) {
    document.getElementById('detail-filter-cc').value = costCenter;
    document.getElementById('detail-filter-month').value = month;
    switchView('detail');
}

// ==========================================
// 7. Page 2: Render Detail Explorer (Daily charts & tables)
// ==========================================
async function updateDetailExplorer() {
    const cc = document.getElementById('detail-filter-cc').value;
    const month = document.getElementById('detail-filter-month').value;
    const ccInfoDiv = document.getElementById('detail-cc-info');
    const tableBody = document.getElementById('daily-table-body');
    
    if (!cc) {
        ccInfoDiv.textContent = "กรุณาเลือกศูนย์ต้นทุนหลัก";
        tableBody.innerHTML = `<tr><td colspan="12" class="empty-state">กรุณาเลือกศูนย์ต้นทุนด้านบนเพื่อโหลดรายละเอียด...</td></tr>`;
        destroyAllCharts();
        return;
    }
    
    // Fetch Name
    const dept = document.getElementById('dash-filter-dept').value;
    const summaryMatch = monthlySummaries.find(s => s.cost_center === cc && s.month === month && s.group_type === dept);
    const ccName = summaryMatch ? summaryMatch.cost_center_name : (cc === '99999' ? 'Summary Department' : 'Unknown');
    ccInfoDiv.innerHTML = `<i class="fa-solid fa-industry"></i> ศูนย์ต้นทุน: <strong>${cc} - ${ccName}</strong>`;
    
    tableBody.innerHTML = `<tr><td colspan="12" class="empty-state"><i class="fa-solid fa-spinner fa-spin"></i> กำลังดึงข้อมูลและเตรียมรายละเอียดรายวัน...</td></tr>`;
    
    let dailyRecords = [];
    
    if (isConnected) {
        try {
            console.log(`Fetching daily details for CC ${cc} in month ${month}...`);
            const queryUrl = `${dbConfig.url}/rest/v1/daily_details_report?cost_center=eq.${cc}&work_date=like.${month}*&order=work_date.asc`;
            const response = await fetch(queryUrl, {
                method: 'GET',
                headers: {
                    'apikey': dbConfig.anonKey,
                    'Authorization': `Bearer ${dbConfig.anonKey}`
                }
            });
            if (response.ok) {
                dailyRecords = await response.json();
            } else {
                dailyRecords = filterLocalDailyMock(cc, month, dept);
            }
        } catch (error) {
            console.error("Failed to query Supabase daily details, fallback to mock data:", error);
            dailyRecords = filterLocalDailyMock(cc, month, dept);
        }
    } else {
        dailyRecords = filterLocalDailyMock(cc, month, dept);
    }
    
    // Update Detail explorer cards and render daily/monthly charts
    renderDetailExplorerData(dailyRecords, cc, month, dept);
}

function filterLocalDailyMock(cc, month, dept) {
    if (typeof MOCK_DAILY_RECORDS === 'undefined') return [];
    return MOCK_DAILY_RECORDS.filter(r => r.cost_center === cc && r.work_date.startsWith(month) && r.group_type === dept);
}

function renderDetailExplorerData(dailyRecords, cc, selectedMonth, dept) {
    const tableBody = document.getElementById('daily-table-body');
    if (dailyRecords.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="12" class="empty-state">ไม่พบข้อมูลรายวันในเดือนนี้...</td></tr>`;
        destroyAllCharts();
        return;
    }
    
    // Sort daily records chronologically
    dailyRecords.sort((a, b) => new Date(a.work_date) - new Date(b.work_date));
    
    // ------------------------------------------
    // A. Update Detail KPI Cards (Actual vs Landing)
    // ------------------------------------------
    const summaryMatch = monthlySummaries.find(s => s.cost_center === cc && s.month === selectedMonth && s.group_type === dept);
    
    let actVol = 0, landingVol = 0;
    let actFte = 0, landingFte = 0;
    let actProd = 0, landingProd = 0;
    
    const daysInMonth = (selectedMonth === '2026-05') ? 31 : 30;
    const isJune = (selectedMonth === '2026-06');
    
    // Scale factor for Landing FTEs and Volume based on working day calendars
    let scaleNormal = 1.0;
    let scaleOS = 1.0;
    if (isJune) {
        const year = 2026;
        const monthIdx = 5; // June is 5
        let endDay = 20; // fallback
        if (globalLatestDate && globalLatestDate.startsWith(selectedMonth)) {
            endDay = parseInt(globalLatestDate.substring(8, 10));
        }
        
        const totalNormalWd = getWorkingDays(year, monthIdx, 'normal');
        const elapsedNormalWd = getWorkingDays(year, monthIdx, 'normal', endDay);
        scaleNormal = elapsedNormalWd > 0 ? (totalNormalWd / elapsedNormalWd) : 1.0;
        
        const totalOSWd = getWorkingDays(year, monthIdx, 'os');
        const elapsedOSWd = getWorkingDays(year, monthIdx, 'os', endDay);
        scaleOS = elapsedOSWd > 0 ? (totalOSWd / elapsedOSWd) : 1.0;
    }
    
    if (summaryMatch) {
        actVol = parseFloat(summaryMatch.volume || 0);
        actFte = parseFloat(summaryMatch.net_total_fte || 0);
        actProd = actFte > 0 ? (actVol / actFte) : 0.0;
        
        const daysWithVol = parseInt(summaryMatch.days_with_volume || 0);
        
        if (isJune && daysWithVol < daysInMonth && daysWithVol > 0) {
            // Volume
            landingVol = actVol * scaleNormal;
            
            // Recalculate Landing Net FTE
            const fte_norm = parseFloat(summaryMatch.fte_normal || 0);
            const fte_ot_l = parseFloat(summaryMatch.fte_ot || 0) * scaleNormal;
            const dep_norm_l = parseFloat(summaryMatch.adjust_norm_minus || 0) * scaleNormal;
            const dep_ot_l = parseFloat(summaryMatch.adjust_ot_minus || 0) * scaleNormal;
            const dest_norm_l = parseFloat(summaryMatch.adjust_norm_plus || 0) * scaleNormal;
            const dest_ot_l = parseFloat(summaryMatch.adjust_ot_plus || 0) * scaleNormal;
            const os_norm_l = parseFloat(summaryMatch.os_norm || 0) * scaleOS;
            const os_ot_l = parseFloat(summaryMatch.os_ot || 0) * scaleOS;
            
            landingFte = (fte_norm - dep_norm_l + dest_norm_l + os_norm_l) + (fte_ot_l - dep_ot_l + dest_ot_l + os_ot_l);
            landingProd = landingFte > 0 ? (landingVol / landingFte) : 0.0;
        } else {
            landingVol = actVol;
            landingFte = actFte;
            landingProd = actProd;
        }
    }
    
    // Render Stats values (rounded to whole integers)
    const formatFTE = (v) => Math.round(parseFloat(v || 0)).toLocaleString('th-TH');
    const formatVol = (v) => Math.round(parseFloat(v || 0)).toLocaleString('th-TH');
    const formatProd = (v) => Math.round(parseFloat(v || 0)).toLocaleString('th-TH');
    
    if (isJune) {
        document.getElementById('detail-stat-vol').textContent = `${formatVol(actVol)} / ${formatVol(landingVol)}`;
        document.getElementById('detail-stat-fte').textContent = `${formatFTE(actFte)} / ${formatFTE(landingFte)}`;
        document.getElementById('detail-stat-prod').textContent = `${formatProd(actProd)} / ${formatProd(landingProd)}`;
    } else {
        document.getElementById('detail-stat-vol').textContent = formatVol(actVol);
        document.getElementById('detail-stat-fte').textContent = formatFTE(actFte);
        document.getElementById('detail-stat-prod').textContent = formatProd(actProd);
    }
    
    // ------------------------------------------
    // B. Render Daily Breakdown Table
    // ------------------------------------------
    let tableHtml = "";
    
    const dailyDates = [];
    const dailyVolumes = [];
    const dailyFteNormals = [];
    const dailyFteOts = [];
    const dailyProductivities = [];
    
    dailyRecords.forEach(row => {
        const netFte = parseFloat(row.net_total_fte || 0);
        const vol = parseFloat(row.volume || 0);
        const prod = parseFloat(row.productivity || 0);
        
        // Dim row if day has no volume or FTE
        const isInactive = (vol === 0 && netFte === 0) ? 'class="inactive-day"' : '';
        
        tableHtml += `
            <tr ${isInactive}>
                <td><strong>${row.work_date}</strong></td>
                <td class="highlight-col">${formatFTE(netFte)}</td>
                <td>${formatVol(vol)}</td>
                <td><strong>${formatProd(prod)}</strong></td>
                <td>${Math.round(parseFloat(row.fte_normal || 0)).toLocaleString('th-TH')}</td>
                <td>${formatFTE(row.fte_ot)}</td>
                <td>${formatFTE(row.adjust_norm_minus)}</td>
                <td>${formatFTE(row.adjust_ot_minus)}</td>
                <td>${formatFTE(row.adjust_norm_plus)}</td>
                <td>${formatFTE(row.adjust_ot_plus)}</td>
                <td>${formatFTE(row.os_norm)}</td>
                <td>${formatFTE(row.os_ot)}</td>
            </tr>
        `;
        
        // Add to daily chart arrays
        dailyDates.push(row.work_date.substring(8, 10)); // Day number
        dailyVolumes.push(vol);
        
        // Calculate daily values safely
        const netNormFte = parseFloat(row.fte_normal || 0) - parseFloat(row.adjust_norm_minus || 0) + parseFloat(row.adjust_norm_plus || 0) + parseFloat(row.os_norm || 0);
        const netOtFte = parseFloat(row.fte_ot || 0) - parseFloat(row.adjust_ot_minus || 0) + parseFloat(row.adjust_ot_plus || 0) + parseFloat(row.os_ot || 0);
        
        dailyFteNormals.push(netNormFte);
        dailyFteOts.push(netOtFte);
        dailyProductivities.push(prod);
    });
    
    tableBody.innerHTML = tableHtml;
    
    // ------------------------------------------
    // C. Render Monthly Trend Charts (April, May, June)
    // ------------------------------------------
    const ccSummaries = monthlySummaries.filter(s => s.cost_center === cc && s.group_type === dept);
    // Sort months chronologically
    ccSummaries.sort((a, b) => a.month.localeCompare(b.month));
    
    const monthlyMonths = [];
    const monthlyVolumes = [];
    const monthlyFtes = [];
    const monthlyProductivities = [];
    
    ccSummaries.forEach(mRow => {
        const isJuneMonth = (mRow.month === '2026-06');
        const mDaysWithVol = parseInt(mRow.days_with_volume || 0);
        
        monthlyMonths.push(mRow.month);
        
        // Use Landing (Projected) values for incomplete month to preserve trend comparability
        let vol_val = parseFloat(mRow.volume || 0);
        let fte_val = parseFloat(mRow.net_total_fte || 0);
        
        if (isJuneMonth && mDaysWithVol < 30 && mDaysWithVol > 0) {
            vol_val *= scaleNormal;
            
            // Recalculate Landing FTE
            const fte_norm = parseFloat(mRow.fte_normal || 0);
            const fte_ot_l = parseFloat(mRow.fte_ot || 0) * scaleNormal;
            const dep_norm_l = parseFloat(mRow.adjust_norm_minus || 0) * scaleNormal;
            const dep_ot_l = parseFloat(mRow.adjust_ot_minus || 0) * scaleNormal;
            const dest_norm_l = parseFloat(mRow.adjust_norm_plus || 0) * scaleNormal;
            const dest_ot_l = parseFloat(mRow.adjust_ot_plus || 0) * scaleNormal;
            const os_norm_l = parseFloat(mRow.os_norm || 0) * scaleOS;
            const os_ot_l = parseFloat(mRow.os_ot || 0) * scaleOS;
            fte_val = (fte_norm - dep_norm_l + dest_norm_l + os_norm_l) + (fte_ot_l - dep_ot_l + dest_ot_l + os_ot_l);
        }
        
        monthlyVolumes.push(vol_val);
        monthlyFtes.push(fte_val);
        monthlyProductivities.push(fte_val > 0 ? (vol_val / fte_val) : 0.0);
    });
    
    // Render 6 charts
    renderChartsData(
        monthlyMonths, monthlyVolumes, monthlyFtes, monthlyProductivities,
        dailyDates, dailyVolumes, dailyFteNormals, dailyFteOts, dailyProductivities
    );
}

function renderChartsData(
    monthlyMonths, monthlyVolumes, monthlyFtes, monthlyProductivities,
    dailyDates, dailyVolumes, dailyFteNormals, dailyFteOts, dailyProductivities
) {
    destroyAllCharts();
    
    // Helper colors
    const primaryBlue = '#3b82f6';
    const primaryGreen = '#3ecf8e';
    const primaryYellow = '#f59e0b';
    
    // ------------------------------------------
    // ROW 1: Monthly Charts
    // ------------------------------------------
    // 1. Monthly Volume Bar Chart
    const ctxMVol = document.getElementById('monthlyVolChart').getContext('2d');
    monthlyVolChart = new Chart(ctxMVol, {
        type: 'bar',
        data: {
            labels: monthlyMonths,
            datasets: [{
                label: 'Throughput Volume (Landing/Actual)',
                data: monthlyVolumes,
                backgroundColor: 'rgba(59, 130, 246, 0.7)',
                borderColor: primaryBlue,
                borderWidth: 1
            }]
        },
        options: getChartOptions('Throughput (หน่วย)', true)
    });
    
    // 2. Monthly FTE Line Chart
    const ctxMFte = document.getElementById('monthlyFteChart').getContext('2d');
    monthlyFteChart = new Chart(ctxMFte, {
        type: 'line',
        data: {
            labels: monthlyMonths,
            datasets: [{
                label: 'Monthly Net Total FTE',
                data: monthlyFtes,
                borderColor: primaryYellow,
                backgroundColor: 'rgba(245, 158, 11, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.3,
                pointBackgroundColor: primaryYellow
            }]
        },
        options: getChartOptions('Net FTE (คน)', false)
    });
    
    // 3. Monthly Productivity Line Chart
    const ctxMProd = document.getElementById('monthlyProdChart').getContext('2d');
    monthlyProdChart = new Chart(ctxMProd, {
        type: 'line',
        data: {
            labels: monthlyMonths,
            datasets: [{
                label: 'Monthly Productivity (Vol/FTE)',
                data: monthlyProductivities,
                borderColor: primaryGreen,
                backgroundColor: 'rgba(62, 207, 142, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.3,
                pointBackgroundColor: primaryGreen
            }]
        },
        options: getChartOptions('Productivity (หน่วย/FTE)', false)
    });
    
    // ------------------------------------------
    // ROW 2: Daily Charts
    // ------------------------------------------
    // 4. Daily Volume Bar Chart
    const ctxDVol = document.getElementById('dailyVolChart').getContext('2d');
    dailyVolChart = new Chart(ctxDVol, {
        type: 'bar',
        data: {
            labels: dailyDates,
            datasets: [{
                label: 'Daily Volume',
                data: dailyVolumes,
                backgroundColor: 'rgba(59, 130, 246, 0.6)',
                borderColor: primaryBlue,
                borderWidth: 1
            }]
        },
        options: getChartOptions('Daily Volume', true)
    });
    
    // 5. Daily FTE Stacked Bar Chart
    const ctxDFte = document.getElementById('dailyFteChart').getContext('2d');
    dailyFteChart = new Chart(ctxDFte, {
        type: 'bar',
        data: {
            labels: dailyDates,
            datasets: [
                {
                    label: 'Net Normal FTE',
                    data: dailyFteNormals,
                    backgroundColor: 'rgba(59, 130, 246, 0.7)',
                    borderColor: primaryBlue,
                    borderWidth: 1
                },
                {
                    label: 'Net OT FTE',
                    data: dailyFteOts,
                    backgroundColor: 'rgba(245, 158, 11, 0.7)',
                    borderColor: primaryYellow,
                    borderWidth: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { color: '#f3f4f6', font: { family: 'Outfit', size: 10 } }
                }
            },
            scales: {
                x: {
                    stacked: true,
                    grid: { display: false },
                    ticks: { color: '#9ca3af', font: { size: 9 } }
                },
                y: {
                    stacked: true,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#9ca3af', font: { size: 9 } }
                }
            }
        }
    });
    
    // 6. Daily Productivity Line Chart
    const ctxDProd = document.getElementById('dailyProdChart').getContext('2d');
    dailyProdChart = new Chart(ctxDProd, {
        type: 'line',
        data: {
            labels: dailyDates,
            datasets: [{
                label: 'Daily Productivity',
                data: dailyProductivities,
                borderColor: primaryGreen,
                backgroundColor: 'rgba(62, 207, 142, 0.1)',
                borderWidth: 3,
                fill: true,
                tension: 0.3,
                pointBackgroundColor: primaryGreen
            }]
        },
        options: getChartOptions('Daily Productivity', false)
    });
}

function getChartOptions(labelName, isBar) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false }
        },
        scales: {
            x: {
                grid: { display: false },
                ticks: { color: '#9ca3af', font: { size: 9 } }
            },
            y: {
                grid: { color: 'rgba(255, 255, 255, 0.05)' },
                ticks: { color: '#9ca3af', font: { size: 9 } }
            }
        }
    };
}

function destroyAllCharts() {
    if (monthlyVolChart) monthlyVolChart.destroy();
    if (monthlyFteChart) monthlyFteChart.destroy();
    if (monthlyProdChart) monthlyProdChart.destroy();
    if (dailyVolChart) dailyVolChart.destroy();
    if (dailyFteChart) dailyFteChart.destroy();
    if (dailyProdChart) dailyProdChart.destroy();
}

// Helper to calculate working days in a month (either full month or elapsed up to a date)
function getWorkingDays(year, monthZeroIndexed, type, endDay = null) {
    const totalDays = new Date(year, monthZeroIndexed + 1, 0).getDate();
    const limit = endDay ? Math.min(endDay, totalDays) : totalDays;
    let count = 0;
    for (let d = 1; d <= limit; d++) {
        const date = new Date(year, monthZeroIndexed, d);
        const dayOfWeek = date.getDay(); // 0 = Sunday, 1 = Monday, ..., 6 = Saturday
        if (type === 'normal') {
            if (dayOfWeek >= 1 && dayOfWeek <= 5) { // Mon-Fri
                count++;
            }
        } else if (type === 'os') {
            if (dayOfWeek >= 1 && dayOfWeek <= 6) { // Mon-Sat
                count++;
            }
        }
    }
    return count;
}
