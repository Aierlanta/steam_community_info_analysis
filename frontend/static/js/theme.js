document.addEventListener('DOMContentLoaded', () => {
    const toggleBtn = document.getElementById('theme-toggle');
    const html = document.documentElement;
    const iconPath = toggleBtn.querySelector('path');

    // Icons
    const sunIcon = "M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z";
    const moonIcon = "M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z";

    function setTheme(theme) {
        html.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);

        // Update Icon
        if (theme === 'light') {
            iconPath.setAttribute('d', moonIcon);
            toggleBtn.setAttribute('aria-label', 'Switch to Dark Mode');
        } else {
            iconPath.setAttribute('d', sunIcon);
            toggleBtn.setAttribute('aria-label', 'Switch to Light Mode');
        }

        // Update Charts
        const charts = document.querySelectorAll('.js-plotly-plot');
        const textColor = theme === 'light' ? '#1e293b' : '#f8fafc';
        const gridColor = theme === 'light' ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)';

        charts.forEach(chart => {
            Plotly.relayout(chart, {
                'font.color': textColor,
                'xaxis.gridcolor': gridColor,
                'yaxis.gridcolor': gridColor,
                'paper_bgcolor': 'rgba(0,0,0,0)',
                'plot_bgcolor': 'rgba(0,0,0,0)'
            }).catch(err => console.warn('Chart update failed:', err));
        });
    }

    // Initialize
    const savedTheme = localStorage.getItem('theme');
    const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const defaultTheme = savedTheme || (systemDark ? 'dark' : 'light');

    setTheme(defaultTheme);

    // Event Listener
    toggleBtn.addEventListener('click', () => {
        const current = html.getAttribute('data-theme');
        const next = current === 'dark' ? 'light' : 'dark';
        setTheme(next);
    });

    // Listen for system changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
            setTheme(e.matches ? 'dark' : 'light');
        }
    });
});
