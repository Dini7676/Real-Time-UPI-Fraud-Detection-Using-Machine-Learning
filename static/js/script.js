// --- TAB LOGIC (For Index/Login)
function switchLoginTab(type) {
    const tabUser = document.getElementById('tab-user');
    const tabAdmin = document.getElementById('tab-admin');
    const formUser = document.getElementById('form-user');
    const formAdmin = document.getElementById('form-admin');
    const avatar = document.getElementById('login-avatar');
    const title = document.getElementById('login-title');
    const icon = avatar ? avatar.querySelector('i') : null;

    if (type === 'user') {
        if (tabUser) tabUser.classList.add('active');
        if (tabAdmin) tabAdmin.classList.remove('active');
        if (formUser) formUser.classList.remove('hidden');
        if (formAdmin) formAdmin.classList.add('hidden');
        if (avatar) { avatar.classList.remove('admin'); avatar.classList.add('user'); }
        if (icon) icon.className = 'fa-solid fa-user';
        if (title) title.innerText = "User Verification";
    } else {
        if (tabAdmin) tabAdmin.classList.add('active');
        if (tabUser) tabUser.classList.remove('active');
        if (formAdmin) formAdmin.classList.remove('hidden');
        if (formUser) formUser.classList.add('hidden');
        if (avatar) { avatar.classList.remove('user'); avatar.classList.add('admin'); }
        if (icon) icon.className = 'fa-solid fa-user-tie';
        if (title) title.innerText = "Admin Portal";
    }
}

// --- NAVIGATION LOGIC (standalone pages)
function navigateTo(page) { window.location.href = page; }

// --- OTP LOGIC (standalone demo)
function sendOtp() {
    const vLogin = document.getElementById('view-login');
    const vOtp = document.getElementById('view-otp');
    const container = document.querySelector('.glass-container');
    const avatar = document.getElementById('login-avatar');
    const otpIcon = document.getElementById('otp-icon');
    if (vLogin) vLogin.classList.add('hidden');
    if (vOtp) vOtp.classList.remove('hidden');
    if (container) container.style.background = 'linear-gradient(135deg, #662d8c 0%, #ed1e79 100%)';
    if (avatar) avatar.style.display = 'none';
    if (otpIcon) otpIcon.classList.remove('hidden');
}

function cancelOtp() {
    const vLogin = document.getElementById('view-login');
    const vOtp = document.getElementById('view-otp');
    const container = document.querySelector('.glass-container');
    const avatar = document.getElementById('login-avatar');
    const otpIcon = document.getElementById('otp-icon');
    if (vOtp) vOtp.classList.add('hidden');
    if (vLogin) vLogin.classList.remove('hidden');
    if (container) container.style.background = 'var(--glass-bg)';
    if (avatar) avatar.style.display = 'flex';
    if (otpIcon) otpIcon.classList.add('hidden');
}

// --- MOCK DATABASE (Simulating Admin-Created Data)
const mockDatabase = {
    "9957000001": {
        fullName: "Dinesh Naik",
        mobile: "9957000001",
        email: "scihub888@gmail.com",
        dob: "1992-06-02",
        location: "Ram Apartment, Chennai -44",
        state: "Tamil Nadu",
        zip: "49879",
        created: "2025-07-23 12:00"
    }
};

// --- LOGIN & SAVE DATA ---
function verifyOtpAndLogin() {
    // In a real app, take mobile from input; here we simulate
    const mobileNumber = "9957000001";
    if (mockDatabase[mobileNumber]) {
        localStorage.setItem('currentUser', JSON.stringify(mockDatabase[mobileNumber]));
        localStorage.setItem('currentUserName', mockDatabase[mobileNumber].fullName);
        window.location.href = "/user/dashboard";
    } else {
        alert("User not found! Please ask Admin to create account.");
    }
}

// --- LOAD DASHBOARD NAME ---
function loadDashboard() {
    const userStr = localStorage.getItem('currentUser');
    let name = 'User';
    if (userStr) {
        try { name = JSON.parse(userStr).fullName || name; } catch {}
    } else {
        const n = localStorage.getItem('currentUserName');
        if (n) name = n;
    }
    const el = document.getElementById('welcome-msg');
    if (el) el.innerText = "Welcome, " + name;
}

// --- AUTO-FETCH PROFILE DATA ---
function loadProfilePage() {
    const userStr = localStorage.getItem('currentUser');
    if (userStr) {
        const user = JSON.parse(userStr);
        const set = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };
        set('disp-name', user.fullName);
        set('disp-mobile', user.mobile);
        set('disp-email', user.email);
        set('disp-dob', user.dob);
        set('disp-loc', user.location);
        set('disp-state', user.state);
        set('disp-zip', user.zip);
        set('disp-created', user.created);
    } else {
        window.location.href = "/login";
    }
}

// --- UTILS ---
function logout() {
    localStorage.removeItem('currentUser');
    localStorage.removeItem('currentUserName');
    window.location.href = "/login";
}

// --- MERCHANT FLOW ---
// 1. SAVE MERCHANT DATA (Triggered from merchant_setup.html)
function completeMerchantSetup() {
    const upi = document.getElementById('m-upi') ? document.getElementById('m-upi').value : '';
    const category = document.getElementById('m-category') ? document.getElementById('m-category').value : '';

    let currentUser = {};
    try {
        currentUser = JSON.parse(localStorage.getItem('currentUser')) || {};
    } catch (e) { currentUser = {}; }
    if (!currentUser.fullName) {
        currentUser = { fullName: "User", mobile: "0000000000", email: "user@example.com" };
    }

    if (!upi || upi.trim() === "") {
        alert("Please enter a UPI ID");
        return;
    }

    const merchantData = {
        name: currentUser.fullName,
        mobile: currentUser.mobile,
        email: currentUser.email,
        upi: upi,
        category: category,
        joined: new Date().toISOString().split('T')[0]
    };

    try {
        localStorage.setItem('currentMerchant', JSON.stringify(merchantData));
    } catch (e) {
        alert('Unable to save merchant data.');
        return;
    }

    // Redirect to Merchant Dashboard route
    window.location.href = "/merchant/dashboard";
}

// 2. LOAD MERCHANT DASHBOARD (Triggered on merchant_dashboard.html)
function loadMerchantDashboard() {
    let merchant = null;
    try { merchant = JSON.parse(localStorage.getItem('currentMerchant')); } catch {}
    if (merchant && document.getElementById('merchant-name-display')) {
        document.getElementById('merchant-name-display').innerText = "Merchant Panel: " + (merchant.name || 'User');
    }
}

// 3. LOAD MERCHANT PROFILE & QR (Triggered on merchant_profile.html)
function loadMerchantProfile() {
    let merchant = null;
    try { merchant = JSON.parse(localStorage.getItem('currentMerchant')); } catch {}

    if (!merchant) {
        // If no merchant, go back to setup
        window.location.href = "/merchant/setup";
        return;
    }

    const set = (id, val) => { const el = document.getElementById(id); if (el) el.innerText = val; };
    set('m-disp-name', merchant.name);
    set('m-disp-mobile', merchant.mobile);
    set('m-disp-email', merchant.email);
    set('m-disp-upi', merchant.upi);
    set('m-disp-cat', merchant.category);
    set('m-disp-date', merchant.joined);

    const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(merchant.upi)}`;
    const img = document.getElementById('qr-image');
    if (img) img.src = qrUrl;
}

// 4. SHARE QR CODE (Downloads the Image)
async function shareQRCode() {
    const qrImage = document.getElementById('qr-image');
    if (!qrImage || !qrImage.src) {
        alert('QR code not ready yet.');
        return;
    }
    const qrUrl = qrImage.src;
    try {
        const response = await fetch(qrUrl);
        const blob = await response.blob();
        const downloadLink = document.createElement('a');
        downloadLink.href = URL.createObjectURL(blob);
        downloadLink.download = 'merchant-qr-code.png';
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
        alert('QR Code downloaded successfully!');
    } catch (error) {
        console.error('Download failed:', error);
        alert("To share, please right-click the QR code and select 'Save Image As'.");
    }
}

/* --- NOTIFICATION + PAYMENT/ FRAUD LOGIC --- */
// --- NOTIFICATION SYSTEM ---
function showNotification(message, type = 'success') {
    const area = document.getElementById('notification-area');
    if (!area) return alert(message); // fallback if area missing
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    let icon = 'fa-check-circle';
    if (type === 'error') icon = 'fa-triangle-exclamation';
    if (type === 'warning') icon = 'fa-circle-exclamation';

    toast.innerHTML = `<i class="fa-solid ${icon}"></i> ${message}`;
    area.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 500);
    }, 4000);
}

// FRAUD DETECTION RULES (SIMULATED)
function detectFraud(amount, recipientId) {
    if (amount > 50000) {
        return "Security Alert: Transaction amount exceeds daily limit of ₹50,000. Payment blocked.";
    }
    const blacklistedAccounts = ['FRAUD123', 'HACKER99', 'SCAMUPI@YBL'];
    if (recipientId && blacklistedAccounts.includes(String(recipientId).toUpperCase())) {
        return "Security Alert: Recipient account is flagged for suspicious activity. Payment blocked.";
    }
    return null;
}

function processPayment() {
    const rNameEl = document.getElementById('pay-name');
    const rIdEl = document.getElementById('pay-id');
    const amountEl = document.getElementById('pay-amount');
    const rName = rNameEl ? rNameEl.value : '';
    const rId = rIdEl ? rIdEl.value : '';
    const amountStr = amountEl ? amountEl.value : '';
    const amount = parseFloat(amountStr);

    if (!rName || !rId || !amountStr) {
        showNotification("Please fill in all fields.", "warning");
        return;
    }
    if (isNaN(amount) || amount <= 0) {
        showNotification("Please enter a valid amount.", "warning");
        return;
    }

    const fraudWarning = detectFraud(amount, rId);
    if (fraudWarning) {
        showNotification(fraudWarning, "error");
        return;
    }

    showNotification(`Successfully paid ₹${amount} to ${rName}!`, "success");
    if (amountEl) amountEl.value = '';
}

/* --- PAYMENT LOGIC FOR VIBRANT UI --- */
function processPaymentLogic() {
    const upiEl = document.getElementById('pay-upi');
    const amtEl = document.getElementById('pay-amount');
    const upi = upiEl ? upiEl.value : '';
    const amount = amtEl ? parseFloat(amtEl.value) : NaN;

    const viewForm = document.getElementById('payment-form');
    const viewSuccess = document.getElementById('payment-success');
    const viewFraud = document.getElementById('payment-fraud');

    if (!upi || isNaN(amount)) { alert('Please enter UPI and Amount'); return; }

    if (amount > 50000 || String(upi).toUpperCase().includes('FRAUD')) {
        if (viewForm) viewForm.classList.add('hidden');
        if (viewFraud) viewFraud.classList.remove('hidden');
    } else {
        if (viewForm) viewForm.classList.add('hidden');
        if (viewSuccess) viewSuccess.classList.remove('hidden');
    }
}

function resetPayment() {
    const viewForm = document.getElementById('payment-form');
    const viewSuccess = document.getElementById('payment-success');
    const viewFraud = document.getElementById('payment-fraud');
    if (viewForm) viewForm.classList.remove('hidden');
    if (viewSuccess) viewSuccess.classList.add('hidden');
    if (viewFraud) viewFraud.classList.add('hidden');
    const upiEl = document.getElementById('pay-upi');
    const amtEl = document.getElementById('pay-amount');
    if (upiEl) upiEl.value = '';
    if (amtEl) amtEl.value = '';
}

/* --- ADD TO SCRIPT.JS --- */

// --- 1. QR SCAN SIMULATION ---
function triggerQRInput() {
    const el = document.getElementById('qr-file-input');
    if (el) el.click();
}

function simulateQRScan() {
    const fileInput = document.getElementById('qr-file-input');
    if (fileInput && fileInput.files && fileInput.files[0]) {
        showNotification("Scanning QR Code...", "info");
        setTimeout(() => {
            const mockQRData = { name: "Starbucks Coffee", upi: "starbucks@bankupi" };
            const nameEl = document.getElementById('pay-name');
            const upiEl = document.getElementById('pay-upi');
            if (nameEl) nameEl.value = mockQRData.name;
            if (upiEl) upiEl.value = mockQRData.upi;
            showNotification("QR Scanned Successfully!", "success");
        }, 1500);
    }
}

// --- 2. PAYMENT & FRAUD DETECTION LOGIC ---
function validateAndPay() {
    const name = (document.getElementById('pay-name') || {}).value;
    const upi = (document.getElementById('pay-upi') || {}).value;
    const amountStr = (document.getElementById('pay-amount') || {}).value;
    const amount = parseFloat(amountStr);

    if (!name || !upi || !amount || amount <= 0) {
        showNotification("Please fill all fields correctly.", "warning");
        return;
    }

    let fraudDetected = false;
    let fraudReason = "";
    if (amount > 50000) {
        fraudDetected = true;
        fraudReason = "High value transaction limit exceeded (₹50,000).";
    }
    const blackList = ['fraud', 'scam', 'hacker', 'testfail'];
    if (String(upi).toLowerCase() && blackList.some(keyword => String(upi).toLowerCase().includes(keyword))) {
        fraudDetected = true;
        fraudReason = "Recipient account flagged for suspicious activity.";
    }

    const viewInitial = document.getElementById('view-initial');
    const viewSuccess = document.getElementById('view-success');
    const viewFraud = document.getElementById('view-fraud');
    if (viewInitial) viewInitial.classList.add('hidden');

    // Always submit to backend; server decides final status and records txn
    const form = document.querySelector('.glass-payment-card form');
    if (form) form.submit();
}

// Helper to save transaction to local storage
function updateTransactionHistory(name, upi, amount) {
    let history = [];
    try { history = JSON.parse(localStorage.getItem('userTransactions')) || []; } catch {}
    const newTxn = {
        id: "TXN" + Math.floor(Math.random() * 900000),
        to: name,
        upi: upi,
        amount: amount,
        date: new Date().toLocaleDateString(),
        status: "Success"
    };
    history.unshift(newTxn);
    localStorage.setItem('userTransactions', JSON.stringify(history));
}

// Helper to reset view
function resetPaymentView() {
    const vi = document.getElementById('view-initial');
    const vf = document.getElementById('view-fraud');
    if (vi) vi.classList.remove('hidden');
    if (vf) vf.classList.add('hidden');
    const amtEl = document.getElementById('pay-amount');
    const upiEl = document.getElementById('pay-upi');
    const nameEl = document.getElementById('pay-name');
    if (amtEl) amtEl.value = '';
    if (upiEl) upiEl.value = '';
    if (nameEl) nameEl.value = '';
}
