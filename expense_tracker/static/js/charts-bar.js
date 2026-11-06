/* =============================================================================
   PTIT EXPENSE MANAGER - BAR CHART (Thu/Chi so sánh nhiều tháng)
   - Phụ thuộc Chart.js 4 (CDN, base.html)
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

    function chartDefault() {
        return {
            responsive: true,
            maintainAspectRatio: true,
            animation: {
                duration: 800,
                easing: 'easeOutQuart'
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    align: 'start',
                    labels: {
                        usePointStyle: true,
                        pointStyle: 'rectRounded',
                        padding: 24,
                        font: { size: 11, weight: '600', family: "'Inter', sans-serif" },
                        color: '#6B7280',
                        boxWidth: 12,
                        boxHeight: 12
                    }
                },
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
                        title: function(ctx) {
                            return 'Tháng ' + ctx[0].label;
                        },
                        label: function (ctx) {
                            var value = ctx.raw;
                            var label = ctx.dataset.label;
                            return label + ': ' + value.toLocaleString('vi-VN') + ' VND';
                        },
                        afterBody: function(ctx) {
                            if (ctx.length === 2) {
                                var income = ctx.find(function(c) { return c.dataset.label === 'THU'; });
                                var expense = ctx.find(function(c) { return c.dataset.label === 'CHI'; });
                                if (income && expense) {
                                    var balance = income.raw - expense.raw;
                                    var sign = balance >= 0 ? '+' : '';
                                    return 'Số dư: ' + sign + balance.toLocaleString('vi-VN') + ' VND';
                                }
                            }
                            return '';
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { font: { size: 11, weight: '600', family: "'Inter', sans-serif" }, color: '#6B7280' },
                    border: { display: false }
                },
                y: {
                    grid: { color: '#F1F3F5', drawBorder: false },
                    ticks: {
                        font: { size: 10, weight: '600', family: "'Inter', sans-serif" },
                        color: '#6B7280',
                        callback: function (val) {
                            if (val >= 1000000) {
                                return (val / 1000000).toFixed(1) + 'M đ';
                            } else if (val >= 1000) {
                                return (val / 1000).toFixed(0) + 'K đ';
                            }
                            return val + ' đ';
                        }
                    },
                    border: { display: false }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        };
    }

    function renderBar(canvasId, payload, opts) {
        var ctx = document.getElementById(canvasId);
        if (!ctx) return null;
        var data = payload || {};
        var labels = data.labels || [];
        var income = data.income || [];
        var expense = data.expense || [];

        // Handle empty data
        if (labels.length === 0) {
            var wrap = ctx.parentElement;
            if (wrap) {
                wrap.style.display = 'flex';
                wrap.innerHTML =
                    '<div class="chart-empty-state" style="display:flex;">' +
                    '<div style="text-align:center;">' +
                    '<i class="fa-regular fa-chart-bar" style="font-size:2.5rem;margin-bottom:.5rem;opacity:.5;display:block;"></i>' +
                    '<p style="margin:0 0 .75rem;font-size:.8rem;color:var(--muted);">Chưa đủ dữ liệu để hiển thị biểu đồ so sánh.</p>' +
                    '</div></div>';
            }
            return null;
        }

        var hasData = income.some(function(v) { return v > 0; }) || expense.some(function(v) { return v > 0; });
        if (!hasData) {
            var wrap = ctx.parentElement;
            if (wrap) {
                wrap.style.display = 'flex';
                wrap.innerHTML =
                    '<div class="chart-empty-state" style="display:flex;">' +
                    '<div style="text-align:center;">' +
                    '<i class="fa-regular fa-chart-bar" style="font-size:2.5rem;margin-bottom:.5rem;opacity:.5;display:block;"></i>' +
                    '<p style="margin:0 0 .75rem;font-size:.8rem;color:var(--muted);">Chưa có dữ liệu thu/chi trong 6 tháng gần đây.</p>' +
                    '</div></div>';
            }
            return null;
        }

        var legend = {
            income: { label: 'THU', color: '#3B82F6' },
            expense: { label: 'CHI', color: '#BE1E2D' }
        };
        opts = opts || {};
        if (opts.variables) {
            legend = opts.variables.reduce(function (acc, v) {
                acc[v] = { label: v === 'income' ? 'THU' : 'CHI', color: v === 'income' ? '#3B82F6' : '#BE1E2D' };
                return acc;
            }, {});
        }

        var datasets = [];
        Object.keys(legend).forEach(function (key) {
            var vals = key === 'income' ? income : expense;
            datasets.push({
                label: legend[key].label,
                data: vals,
                backgroundColor: legend[key].color,
                borderColor: legend[key].color,
                borderWidth: 0,
                borderRadius: 6,
                barPercentage: 0.6,
                categoryPercentage: 0.7,
                maxBarThickness: 32
            });
        });

        var config = chartDefault();
        config.type = 'bar';
        config.data = { labels: labels, datasets: datasets };
        config.options = {
            maintainAspectRatio: true,
            responsive: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top',
                    align: 'start',
                    labels: {
                        usePointStyle: true,
                        pointStyle: 'rectRounded',
                        padding: 24,
                        font: { size: 11, weight: '600', family: "'Inter', sans-serif" },
                        color: '#6B7280',
                        boxWidth: 12,
                        boxHeight: 12
                    }
                },
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
                        title: function(ctx) {
                            return 'Tháng ' + ctx[0].label;
                        },
                        label: function (ctx) {
                            var value = ctx.raw;
                            var label = ctx.dataset.label;
                            return label + ': ' + value.toLocaleString('vi-VN') + ' VND';
                        },
                        afterBody: function(ctx) {
                            if (ctx.length === 2) {
                                var incomeItem = ctx.find(function(c) { return c.dataset.label === 'THU'; });
                                var expenseItem = ctx.find(function(c) { return c.dataset.label === 'CHI'; });
                                if (incomeItem && expenseItem) {
                                    var balance = incomeItem.raw - expenseItem.raw;
                                    var sign = balance >= 0 ? '+' : '';
                                    return 'Số dư: ' + sign + balance.toLocaleString('vi-VN') + ' VND';
                                }
                            }
                            return '';
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { font: { size: 11, weight: '600', family: "'Inter', sans-serif" }, color: '#6B7280' },
                    border: { display: false }
                },
                y: {
                    grid: { color: '#F1F3F5', drawBorder: false },
                    ticks: {
                        font: { size: 10, weight: '600', family: "'Inter', sans-serif" },
                        color: '#6B7280',
                        callback: function (val) {
                            if (val >= 1000000) {
                                return (val / 1000000).toFixed(1) + 'M đ';
                            } else if (val >= 1000) {
                                return (val / 1000).toFixed(0) + 'K đ';
                            }
                            return val + ' đ';
                        }
                    },
                    border: { display: false }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        };

        var myChart = new Chart(ctx, config);
        window.PTITCharts = window.PTITCharts || {};
        window.PTITCharts._refs = window.PTITCharts._refs || {};
        window.PTITCharts._refs[canvasId] = myChart;
        return {
            destroy: function () {
                var r = window.PTITCharts._refs[canvasId];
                if (r) { r.destroy(); delete window.PTITCharts._refs[canvasId]; }
            }
        };
    }

    return { renderBar: renderBar };
});