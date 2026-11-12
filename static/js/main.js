/**
 * Sports League Platform - Main Client Script
 */

document.addEventListener('DOMContentLoaded', () => {
    initMobileNav();
    initAlertDismissal();
    initLiveSearchWidget();
    initClientTableSorting();
});

/**
 * Mobile Navigation Toggle
 */
function initMobileNav() {
    const toggleBtn = document.getElementById('mobileMenuToggle');
    const navPanel = document.getElementById('mobileNavPanel');

    if (toggleBtn && navPanel) {
        toggleBtn.addEventListener('click', () => {
            navPanel.classList.toggle('open');
            const isOpen = navPanel.classList.contains('open');
            toggleBtn.setAttribute('aria-expanded', isOpen);
            toggleBtn.innerHTML = isOpen ? '&times;' : '&#9776;';
        });
    }
}

/**
 * Flash Alert Auto-Dismiss and Close Button
 */
function initAlertDismissal() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        // Auto-dismiss after 6 seconds
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            alert.style.transition = 'all 0.4s ease';
            setTimeout(() => alert.remove(), 400);
        }, 6000);
    });
}

/**
 * Real-Time Instant Search (for Team & Player listing)
 */
function initLiveSearchWidget() {
    const searchInput = document.getElementById('quickFilterInput');
    if (!searchInput) return;

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        const items = document.querySelectorAll('[data-search-target]');

        items.forEach(item => {
            const text = (item.getAttribute('data-search-target') || '').toLowerCase();
            if (text.includes(query)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    });
}

/**
 * Client-Side Interactive Table Column Sorting
 */
function initClientTableSorting() {
    const sortHeaders = document.querySelectorAll('th.th-sortable');
    sortHeaders.forEach(th => {
        th.addEventListener('click', () => {
            const table = th.closest('table');
            const tbody = table.querySelector('tbody');
            const colIndex = Array.from(th.parentNode.children).indexOf(th);
            const isAsc = th.getAttribute('data-order') === 'asc';
            const rows = Array.from(tbody.querySelectorAll('tr'));

            rows.sort((rowA, rowB) => {
                const cellA = rowA.children[colIndex].innerText.trim();
                const cellB = rowB.children[colIndex].innerText.trim();

                const numA = parseFloat(cellA.replace(/[^0-9.-]/g, ''));
                const numB = parseFloat(cellB.replace(/[^0-9.-]/g, ''));

                if (!isNaN(numA) && !isNaN(numB)) {
                    return isAsc ? numA - numB : numB - numA;
                }
                return isAsc ? cellA.localeCompare(cellB) : cellB.localeCompare(cellA);
            });

            // Toggle sort order state
            sortHeaders.forEach(header => header.removeAttribute('data-order'));
            th.setAttribute('data-order', isAsc ? 'desc' : 'asc');

            // Re-append sorted rows
            rows.forEach(r => tbody.appendChild(r));
        });
    });
}
