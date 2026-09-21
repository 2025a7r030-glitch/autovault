// AutoVault Main Interactions & Navigation Script

document.addEventListener('DOMContentLoaded', () => {
    // 1. Mobile Sidebar Toggle
    const sidebar = document.getElementById('sidebar');
    const sidebarOpen = document.getElementById('sidebar-open');
    const sidebarClose = document.getElementById('sidebar-close');

    if (sidebarOpen && sidebar) {
        sidebarOpen.addEventListener('click', () => {
            sidebar.classList.add('mobile-open');
        });
    }

    if (sidebarClose && sidebar) {
        sidebarClose.addEventListener('click', () => {
            sidebar.classList.remove('mobile-open');
        });
    }

    // 2. Custom Vehicle Switcher Dropdown
    const dropdownBtn = document.getElementById('vehicle-dropdown-btn');
    const dropdownMenu = document.getElementById('vehicle-dropdown-menu');

    if (dropdownBtn && dropdownMenu) {
        dropdownBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            dropdownMenu.classList.toggle('show');
        });

        // Close on click outside
        document.addEventListener('click', (e) => {
            if (!dropdownBtn.contains(e.target) && !dropdownMenu.contains(e.target)) {
                dropdownMenu.classList.remove('show');
            }
        });
    }

    // 3. Auto-dismiss Flash Alerts
    const alerts = document.querySelectorAll('.toast-container .alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(() => alert.remove(), 400);
        }, 5000);
    });

    // 4. Initialize Lucide Icons
    if (window.lucide) {
        window.lucide.createIcons();
    }
});
