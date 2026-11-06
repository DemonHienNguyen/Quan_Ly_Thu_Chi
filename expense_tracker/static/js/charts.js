/**
 * charts.js - Script vẽ và cấu hình biểu đồ Chart.js cho Dashboard
 * Quản Lý Chi Tiêu Cá Nhân Dành Cho Sinh Viên - Nhóm 8 PTIT
 */

function initCategoryDoughnutChart(canvasId, labels, dataValues) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    return new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: dataValues,
                backgroundColor: [
                    '#ef4444', '#f97316', '#f59e0b', '#10b981',
                    '#06b6d4', '#3b82f6', '#6366f1', '#8b5cf6',
                    '#ec4899', '#64748b'
                ],
                borderWidth: 2,
                borderColor: '#ffffff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { boxWidth: 12, padding: 15, font: { family: 'Plus Jakarta Sans', size: 12 } }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            let label = context.label || '';
                            let value = context.parsed || 0;
                            return label + ': ' + new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(value);
                        }
                    }
                }
            },
            cutout: '65%'
        }
    });
}

function initMonthlyBarChart(canvasId, labels, incomeData, expenseData) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    return new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Thu nhập',
                    data: incomeData,
                    backgroundColor: '#10b981',
                    borderRadius: 6,
                    maxBarThickness: 32
                },
                {
                    label: 'Chi tiêu',
                    data: expenseData,
                    backgroundColor: '#ef4444',
                    borderRadius: 6,
                    maxBarThickness: 32
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function (value) {
                            if (value >= 1000000) return (value / 1000000) + ' Tr';
                            if (value >= 1000) return (value / 1000) + ' k';
                            return value;
                        }
                    },
                    grid: { color: '#f1f5f9' }
                },
                x: {
                    grid: { display: false }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: { boxWidth: 12, padding: 15, font: { family: 'Plus Jakarta Sans', size: 12 } }
                },
                tooltip: {
                    callbacks: {
                        label: function (context) {
                            return context.dataset.label + ': ' + new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(context.parsed.y);
                        }
                    }
                }
            }
        }
    });
}
