/**
 * GramaCart Admin Engine - Optimized for Hybrid Layouts
 */

const toggleSidebar = () => {
    const sidebar = document.getElementById("sidebar");
    const wrapper = document.getElementById("mainWrapper");
    const overlay = document.getElementById("sidebarOverlay");

    if (!sidebar || !wrapper) return;

    if (window.innerWidth >= 992) {
        // DESKTOP: Traditional Push/Collapse
        sidebar.classList.toggle("collapsed");
        wrapper.classList.toggle("expanded");
        
        // Clean up mobile states if they were left active
        sidebar.classList.remove("active");
        if(overlay) overlay.classList.remove("show");
    } else {
        // MOBILE: Drawer Overlay
        sidebar.classList.toggle("active");
        if(overlay) overlay.classList.toggle("show");
        
        // Prevent background scrolling when menu is open on mobile
        document.body.style.overflow = sidebar.classList.contains("active") ? "hidden" : "auto";
    }
};

document.addEventListener("DOMContentLoaded", function() {
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");

    // 1. Highlight Active Link
    const currentPath = window.location.pathname;
    document.querySelectorAll(".menu-item").forEach(link => {
        if (link.getAttribute("href") === currentPath) {
            link.classList.add("active");
        }
    });

    // 2. Mobile Link Auto-Close
    // If a user clicks a link on mobile, close the sidebar so they see the new page
    if (window.innerWidth < 992) {
        document.querySelectorAll(".menu-item").forEach(link => {
            link.addEventListener("click", () => {
                sidebar.classList.remove("active");
                if(overlay) overlay.classList.remove("show");
                document.body.style.overflow = "auto";
            });
        });
    }

    // 3. Bootstrap Tooltips (Safety Check added)
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(t => new bootstrap.Tooltip(t));
    }

    // 4. Window Resize Cleanup
    window.addEventListener('resize', () => {
        if (window.innerWidth >= 992) {
            document.body.style.overflow = "auto";
            if(overlay) overlay.classList.remove("show");
        }
    });
});

function updateTimestamp() {
    const now = new Date();
    const timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    document.getElementById('sync-time').innerText = timeString;
}

function refreshOpsData() {
    // This is where you'd typically make an AJAX call to Django
    // For now, we'll just animate the refresh and update the time
    const btn = document.querySelector('.btn-refresh-mini i');
    btn.classList.add('bi-spin'); // Add a spin animation
    
    setTimeout(() => {
        updateTimestamp();
        btn.classList.remove('bi-spin');
        console.log("GramaCart Operations Synced.");
    }, 800);
}

// Initial call
updateTimestamp();
document.addEventListener("DOMContentLoaded", function() {
    const ctx = document.getElementById('salesChart').getContext('2d');
    
    // Create a smooth gradient for the area chart
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(0, 200, 83, 0.2)');
    gradient.addColorStop(1, 'rgba(0, 200, 83, 0)');

    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            datasets: [{
                label: 'Daily Sales (₹)',
                data: [12000, 19000, 15000, 25000, 22000, 30000, 45200],
                borderColor: '#00c853',
                borderWidth: 3,
                backgroundColor: gradient,
                fill: true,
                tension: 0.4, // Makes the line curvy
                pointRadius: 0,
                pointHoverRadius: 6,
                pointHoverBackgroundColor: '#00c853',
                pointHoverBorderColor: '#fff',
                pointHoverBorderWidth: 3,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { display: false }, // Cleaner look: hide Y axis labels
                x: { grid: { display: false }, ticks: { color: '#94a3b8', font: { weight: '600' } } }
            }
        }
    });
});