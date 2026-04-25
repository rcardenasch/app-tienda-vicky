console.log('Dashboard JS cargado');

// =========================
// TOP PRODUCTOS
// =========================
const prodCtx = document.getElementById('productosChart');

if (prodCtx) {
    new Chart(prodCtx, {
        type: 'bar',
        data: {
            labels: prodLabels,
            datasets: [{
                label: 'Cantidad vendida',
                data: prodData
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

// =========================
// VENTAS + GANANCIAS
// =========================
const ventasCtx = document.getElementById('ventasChart');

if (ventasCtx) {
    new Chart(ventasCtx, {
        type: 'line',
        data: {
            labels: ventasLabels,
            datasets: [
                {
                    label: 'Ventas',
                    data: ventasData,
                    tension: 0.3
                },
                {
                    label: 'Ganancias',
                    data: gananciaData,
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}