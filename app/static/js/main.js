// app/static/js/main.js

document.addEventListener('DOMContentLoaded', function () {

    /* ============================================================
       SIDEBAR LOGIC
       ============================================================ */
    const sidebar         = document.getElementById('sidebar');
    const mainWrapper     = document.getElementById('mainWrapper');
    const overlay         = document.getElementById('sidebarOverlay');
    const collapseBtn     = document.getElementById('sidebarCollapseBtn');
    const toggleBtn       = document.getElementById('sidebarToggleBtn');
    const closeBtn        = document.getElementById('sidebarCloseBtn');
    const collapseIcon    = document.getElementById('collapseIcon');

    if (!sidebar) return; // not authenticated, skip

    const STORAGE_KEY = 'farmPayroll_sidebarCollapsed';
    const isDesktop   = () => window.innerWidth >= 992;

    // ---- Restore desktop collapsed state ----
    if (isDesktop() && localStorage.getItem(STORAGE_KEY) === 'true') {
        sidebar.classList.add('collapsed');
        mainWrapper.classList.add('sidebar-collapsed');
    }

    // ---- Desktop: collapse / expand ----
    if (collapseBtn) {
        collapseBtn.addEventListener('click', function () {
            const isCollapsed = sidebar.classList.toggle('collapsed');
            mainWrapper.classList.toggle('sidebar-collapsed', isCollapsed);
            localStorage.setItem(STORAGE_KEY, isCollapsed);
        });
    }

    // ---- Mobile: open sidebar ----
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function () {
            if (isDesktop()) {
                // On desktop the toggle button also collapses
                const isCollapsed = sidebar.classList.toggle('collapsed');
                mainWrapper.classList.toggle('sidebar-collapsed', isCollapsed);
                localStorage.setItem(STORAGE_KEY, isCollapsed);
            } else {
                openMobileSidebar();
            }
        });
    }

    // ---- Mobile: close via X button ----
    if (closeBtn) {
        closeBtn.addEventListener('click', closeMobileSidebar);
    }

    // ---- Mobile: close via overlay ----
    if (overlay) {
        overlay.addEventListener('click', closeMobileSidebar);
    }

    function openMobileSidebar() {
        sidebar.classList.add('mobile-open');
        overlay.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeMobileSidebar() {
        sidebar.classList.remove('mobile-open');
        overlay.classList.remove('active');
        document.body.style.overflow = '';
    }

    // ---- Close mobile sidebar on resize to desktop ----
    window.addEventListener('resize', function () {
        if (isDesktop()) {
            closeMobileSidebar();
            // Re-apply desktop collapsed state
            const collapsed = localStorage.getItem(STORAGE_KEY) === 'true';
            sidebar.classList.toggle('collapsed', collapsed);
            mainWrapper.classList.toggle('sidebar-collapsed', collapsed);
        }
    });

    // ---- Submenu dropdowns ----
    document.querySelectorAll('.sidebar-link-toggle').forEach(function (link) {
        link.addEventListener('click', function (e) {
            e.preventDefault();
            // Don't open submenus when sidebar is collapsed on desktop
            if (isDesktop() && sidebar.classList.contains('collapsed')) return;

            const parentItem = this.closest('.sidebar-item-dropdown');
            const isOpen = parentItem.classList.contains('open');

            // Close all other open submenus
            document.querySelectorAll('.sidebar-item-dropdown.open').forEach(function (item) {
                if (item !== parentItem) item.classList.remove('open');
            });

            parentItem.classList.toggle('open', !isOpen);
        });
    });

    // ---- Add data-tooltip attributes for collapsed tooltips ----
    document.querySelectorAll('.sidebar-link').forEach(function (link) {
        const textEl = link.querySelector('.sidebar-link-text');
        if (textEl) {
            link.setAttribute('data-tooltip', textEl.textContent.trim());
        }
    });

    /* ============================================================
       FLASH MESSAGES — auto-dismiss with slide-out animation
       ============================================================ */
    document.querySelectorAll('.flash-container .alert').forEach(function (alert) {
        // Auto-dismiss after 4 seconds
        setTimeout(function () {
            alert.classList.add('flash-hiding');
            setTimeout(function () {
                alert.remove();
            }, 400); // matches flashSlideOut duration
        }, 4000);

        // Manual close button also uses animation
        const closeBtn = alert.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', function () {
                alert.classList.add('flash-hiding');
                setTimeout(function () { alert.remove(); }, 400);
            });
        }
    });

    /* ============================================================
       BOOTSTRAP TOOLTIPS
       ============================================================ */
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
        new bootstrap.Tooltip(el);
    });

    /* ============================================================
       SESSION TIMEOUT WARNING (25 min warning, 30 min redirect)
       ============================================================ */
    let timeoutWarning;
    let timeoutRedirect;

    function resetTimers() {
        clearTimeout(timeoutWarning);
        clearTimeout(timeoutRedirect);

        timeoutWarning = setTimeout(function () {
            alert('Your session will expire in 5 minutes due to inactivity.');
        }, 25 * 60 * 1000);

        timeoutRedirect = setTimeout(function () {
            window.location.href = '/auth/logout';
        }, 30 * 60 * 1000);
    }

    ['click', 'keypress', 'scroll', 'mousemove'].forEach(function (event) {
        document.addEventListener(event, resetTimers, { passive: true });
    });

    resetTimers();
});

/* ============================================================
   UTILITY FUNCTIONS
   ============================================================ */

function formatCurrency(amount) {
    return 'R' + parseFloat(amount).toFixed(2);
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-ZA', { year: 'numeric', month: 'short', day: 'numeric' });
}

function calculateHours(clockIn, clockOut) {
    if (!clockIn || !clockOut) return 0;
    const [inH, inM]   = clockIn.split(':').map(Number);
    const [outH, outM] = clockOut.split(':').map(Number);
    let hours   = outH - inH;
    let minutes = outM - inM;
    if (hours < 0 || (hours === 0 && minutes < 0)) hours += 24;
    return hours + (minutes / 60);
}

function validatePassword(password) {
    if (password.length < 8)          return { valid: false, message: 'Password must be at least 8 characters' };
    if (!/[A-Za-z]/.test(password))   return { valid: false, message: 'Password must contain at least one letter' };
    if (!/[0-9]/.test(password))      return { valid: false, message: 'Password must contain at least one number' };
    if (!/[@$!%*#?&]/.test(password)) return { valid: false, message: 'Password must contain at least one symbol' };
    return { valid: true, message: 'Password is strong' };
}

function confirmDelete(message) {
    return confirm(message || 'Are you sure you want to delete this item?');
}

function exportTableToCSV(tableId, filename) {
    filename = filename || 'export.csv';
    const table = document.getElementById(tableId);
    const rows  = table.querySelectorAll('tr');
    const csv   = [];

    rows.forEach(function (row) {
        const cells   = row.querySelectorAll('td, th');
        const rowData = Array.from(cells).map(function (cell) {
            let text = cell.textContent.trim();
            if (text.includes(',') || text.includes('"')) {
                text = '"' + text.replace(/"/g, '""') + '"';
            }
            return text;
        });
        csv.push(rowData.join(','));
    });

    const blob = new Blob([csv.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.setAttribute('href', URL.createObjectURL(blob));
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function printElement(elementId) {
    const element        = document.getElementById(elementId);
    const originalContents = document.body.innerHTML;
    document.body.innerHTML = element.innerHTML;
    window.print();
    document.body.innerHTML = originalContents;
    location.reload();
}

function submitFormAjax(formId, successCallback) {
    const form     = document.getElementById(formId);
    const formData = new FormData(form);

    fetch(form.action, {
        method: form.method,
        body: formData,
        headers: { 'X-CSRFToken': document.querySelector('[name="csrf_token"]').value }
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
        if (data.success) { successCallback(data); }
        else { alert(data.message || 'An error occurred'); }
    })
    .catch(function (err) {
        console.error('Error:', err);
        alert('An error occurred while submitting the form');
    });
}
