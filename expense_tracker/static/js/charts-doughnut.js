/* =============================================================================
   PTIT EXPENSE MANAGER - CHARTS (Dashboard rendering)
   - Phụ thuộc Chart.js 4 (CDN, base.html)
   - renderPie / destroy
============================================================================== */
(function (global, factory) {
    if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        global.PTITCharts = global.PTITCharts || {};
        Object.assign(global.PTITCharts, factory());
    }
})(typeof self !== 'undefined' ? self : this, function () {
    'use strict';

    var piePalette = [
        '#BE1E2D',
        '#2563EB',
        '#0F9D78',
        '#D97706',
        '#7C3AED',
        '#0891B2',
        '#DB2777',
        '#4D7C0F',
        '#475569'
    ];

    function chartDefault() {
        return {
            responsive: true,
            maintainAspectRatio: true,
            animation: {
                animateRotate: true,
                animateScale: true,
                duration: 800,
                easing: 'easeOutQuart'
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#111827',
                    titleColor: '#fff',
                    bodyColor: '#E2E8F0',
                    borderColor: '#E5E7EB',
                    borderWidth: 1,
                    padding: 12,
                    cornerRadius: 8,
                    displayColors: true,
                    callbacks: {
                        label: function (ctx) {
                            var value = ctx.raw;
                            var total = ctx.chart.data.datasets[0].data.reduce(function(a, b) { return a + b; }, 0);
                            var pct = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                            return ctx.label + ': ' + value.toLocaleString('vi-VN') + ' VND (' + pct + '%)';
                        }
                    }
                }
            },
            scales: { x: { display: false }, y: { display: false } },
            cutout: '65%'
        };
    }

    function renderPie(canvasId, payload) {
        var ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        var data = payload || {};
        var labels = data.labels || [];
        var values = data.data || [];

        // Handle empty data - show empty state in canvas parent
        if (labels.length === 0 || values.length === 0) {
            var wrap = ctx.parentElement;
            if (wrap) {
                wrap.style.display = 'flex';
                wrap.innerHTML =
                    '<div class="chart-empty-state" style="display:flex;">' +
                    '<div style="text-align:center;">' +
                    '<i class="fa-regular fa-chart-pie" style="font-size:2.5rem;margin-bottom:.5rem;opacity:.5;display:block;"></i>' +
                    '<p style="margin:0 0 .75rem;font-size:.8rem;color:var(--muted);">Chưa có giao dịch chi tiêu nào trong tháng.</p>' +
                    '<a href="/transactions/#transaction-form" class="btn btn-ptit btn-sm" style="font-size:.7rem;padding:.4rem .8rem;">Thêm giao dịch</a>' +
                    '</div></div>';
            }
            return null;
        }

        var total = 0;
        values.forEach(function (v) { total += v; });

        var entries = labels.map(function (label, i) {
            var pct = total > 0 ? (values[i] / total) * 100 : 0;
            return {
                label: label,
                value: values[i],
                pct: pct,
                color: piePalette[i % piePalette.length]
            };
        });

        var config = chartDefault();
        config.type = 'doughnut';
        config.data = {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: entries.map(function (e) { return e.color; }),
                borderColor: '#fff',
                borderWidth: 2,
                hoverBorderColor: '#fff',
                hoverBorderWidth: 3,
                hoverOffset: 8
            }]
        };
        config.options = {
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function (ctx) {
                            var value = ctx.raw;
                            var total = ctx.chart.data.datasets[0].data.reduce(function(a, b) { return a + b; }, 0);
                            var pct = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                            return ctx.label + ': ' + value.toLocaleString('vi-VN') + ' VND (' + pct + '%)';
                        }
                    }
                }
            }
        };

        var myChart = new Chart(ctx, config);
        window.PTITCharts._refs = window.PTITCharts._refs || {};
        window.PTITCharts._refs[canvasId] = myChart;
        return {
            destroy: function () {
                var r = window.PTITCharts._refs[canvasId];
                if (r) { r.destroy(); delete window.PTITCharts._refs[canvasId]; }
            }
        };
    }

    function destroy(canvasId) {
        var ref = window.PTITCharts._refs && window.PTITCharts._refs[canvasId];
        if (ref) { ref.destroy(); delete window.PTITCharts._refs[canvasId]; }
    }

    return { renderPie: renderPie, destroy: destroy, piePalette: piePalette };
});