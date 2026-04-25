console.log("ventas.js cargado correctamente");

document.addEventListener("DOMContentLoaded", function () {

    let carrito = [];
    let scanner = null;
    let ultimoCodigo = null;
    let tiempoUltimaLectura = 0;
    let usandoTrasera = true;
    let productosCache = [];
    let clientesCache = [];

    // =========================
    // CARGAR VENTAS RECIENTES
    // =========================
    cargarVentasRecientes();

    // =========================
    // 📷 SCANNER
    // =========================
    window.iniciarScanner = function () {

        if (scanner) return;

        scanner = new Html5Qrcode("reader");

        scanner.start(
            { facingMode: "environment" },
            {
                fps: 20, qrbox: { width: 300, height: 150 }, disableFlip: false,
                experimentalFeatures: {
                    useBarCodeDetectorIfSupported: true
                },
                formatsToSupport: [
                    Html5QrcodeSupportedFormats.EAN_13,
                    Html5QrcodeSupportedFormats.EAN_8,
                    Html5QrcodeSupportedFormats.CODE_128,
                    Html5QrcodeSupportedFormats.CODE_39,
                    Html5QrcodeSupportedFormats.UPC_A,
                    Html5QrcodeSupportedFormats.UPC_E
                ]
            },
            codigo => {

                const ahora = Date.now();

                if (
                    codigo === ultimoCodigo &&
                    (ahora - tiempoUltimaLectura < 1500)
                ) return;

                ultimoCodigo = codigo;
                tiempoUltimaLectura = ahora;

                // Mostrar código leído en pantalla
                let estado = document.getElementById("scannerEstado");
                if (estado) {
                    estado.innerText = "Código leído: " + codigo;
                }

                // llenar buscador visualmente
                let inputBuscar = document.getElementById("buscar");
                if (inputBuscar) {
                    inputBuscar.value = codigo;
                }

                buscarProducto(codigo);

                // 🔴 APAGAR CÁMARA AQUÍ
                if (scanner) {
                    scanner.stop().then(() => {
                        scanner.clear();
                        scanner = null;
                    });
                }
            }
        );
    };

    window.cambiarCamara = function () {
        if (!scanner) return;

        scanner.stop().then(() => {
            usandoTrasera = !usandoTrasera;

            scanner.start(
                { facingMode: usandoTrasera ? "environment" : "user" },
                {
                    fps: 20, qrbox: { width: 300, height: 150 },
                    aspectRatio: 1.777, disableFlip: false,
                    experimentalFeatures: {
                        useBarCodeDetectorIfSupported: true
                    },
                    formatsToSupport: [
                        Html5QrcodeSupportedFormats.EAN_13,
                        Html5QrcodeSupportedFormats.EAN_8,
                        Html5QrcodeSupportedFormats.CODE_128,
                        Html5QrcodeSupportedFormats.CODE_39,
                        Html5QrcodeSupportedFormats.UPC_A,
                        Html5QrcodeSupportedFormats.UPC_E
                    ]
                },
                codigo => {

                    console.log("Código escaneado:", codigo);

                    let inputBuscar = document.getElementById("buscar");
                    if (inputBuscar) inputBuscar.value = codigo;

                    buscarProducto(codigo);
                    // 🔴 APAGAR CÁMARA AQUÍ
                    if (scanner) {
                        scanner.stop().then(() => {
                            scanner.clear();
                            scanner = null;
                        });
                    }
                }
            );
        });
    };

    function buscarProducto(valor) {

        if (!valor) return;

        console.log("Buscando producto:", valor);

        fetch(`/api/producto?q=${encodeURIComponent(valor)}`)
            .then(res => res.json())
            .then(lista => {

                console.log("Respuesta API:", lista);

                if (!lista || lista.length === 0) {

                    let estado = document.getElementById("scannerEstado");
                    if (estado) {
                        estado.innerText = "❌ Producto no encontrado";
                    }
                    alert("Producto no encontrado");

                    let inputBuscar = document.getElementById("buscar");
                    if (inputBuscar) inputBuscar.value = "";

                    return;
                }

                let exacto = lista.find(p => p.codigo_barras == valor);

                if (!exacto) {
                    exacto = lista[0];
                }

                agregarAlCarrito(exacto);

                let inputBuscar = document.getElementById("buscar");
                if (inputBuscar) inputBuscar.value = "";
            })
            .catch(err => {
                console.error("Error buscando producto:", err);
                alert("Error buscando producto");
            });
    }
    // =========================
    // 🛒 CARRITO
    // =========================
    function agregarAlCarrito(prod) {

        let existente = carrito.find(p => p.id == prod.id);

        let nuevaCantidad = existente ? existente.cantidad + 1 : 1;

        if (prod.stock !== undefined && nuevaCantidad > prod.stock) {
            alert("Stock insuficiente");
            return;
        }

        if (existente) {
            existente.cantidad += 1;
        } else {
            carrito.push({
                id: prod.id,
                codigo_barras: prod.codigo_barras,
                nombre: prod.nombre,
                precio: prod.precio,
                stock: prod.stock,
                cantidad: 1
            });
        }

        render();
    }

    function render() {

        let html = "";
        let total = 0;

        carrito.forEach((p, i) => {

            let subtotal = p.precio * p.cantidad;
            total += subtotal;

            html += `
            <tr>
                <td>${p.codigo_barras}</td>
                <td>
                    ${p.nombre}
                    <input type="hidden" name="producto_id" value="${p.id}">
                    <input type="hidden" name="cantidad" value="${p.cantidad}">
                </td>
                <td>${p.precio}</td>
                <td>
                    <input type="number" min="1"
                        value="${p.cantidad}"
                        onchange="cambiarCantidad(${i}, this.value)">
                </td>
                <td>${subtotal.toFixed(2)}</td>
                <td>
                    <button type="button"
                        class="btn btn-danger btn-sm"
                        onclick="eliminar(${i})">
                        <i class="bi bi-trash"></i>
                    </button>
                </td>
            </tr>`;
        });

        document.getElementById("lista").innerHTML = html;
        document.getElementById("total").innerText = total.toFixed(2);
        document.getElementById("totalPago").innerText = total.toFixed(2);

        calcularVuelto();
    }

    function calcularVuelto() {

        let total = 0;

        carrito.forEach(p => {
            total += p.precio * p.cantidad;
        });

        let pagado = parseFloat(
            document.getElementById("montoPagado").value || 0
        );

        let vuelto = pagado - total;

        document.getElementById("vuelto").innerText =
            vuelto >= 0 ? vuelto.toFixed(2) : "0.00";

        document.getElementById("alertaPago").style.display =
            pagado < total ? "block" : "none";

        // 🔥 CONTROL BOTÓN
        let btn = document.getElementById("btnRegistrar");

        if (pagado >= total && total > 0) {
            btn.style.display = "block";   // mostrar
        } else {
            btn.style.display = "none";    // ocultar
        }
    }

    // =========================
    // 💵 PAGO
    // =========================
    window.agregarPago = function (monto) {

        let input = document.getElementById("montoPagado");
        let actual = parseFloat(input.value || 0);

        input.value = (actual + monto).toFixed(2);

        calcularVuelto();
    };

    window.limpiarPago = function () {

        document.getElementById("montoPagado").value = "";
        calcularVuelto();
    };

    let inputPago = document.getElementById("montoPagado");

    if (inputPago) {
        inputPago.addEventListener("input", calcularVuelto);

        inputPago.addEventListener("focus", function () {
            this.select();
        });
    }

    // =========================
    // CAMBIAR / ELIMINAR
    // =========================
    window.cambiarCantidad = function (index, valor) {
        carrito[index].cantidad = parseFloat(valor);
        render();
    };

    window.eliminar = function (index) {
        carrito.splice(index, 1);
        render();
    };

    // =========================
    // ENTER BUSCADOR
    // =========================
    let inputBuscar = document.getElementById("buscar");

    if (inputBuscar) {
        inputBuscar.addEventListener("keyup", function (e) {
            if (e.key === "Enter") {
                buscarProducto(this.value);
                this.value = "";
            }
        });
    }

    // =========================
    // LIMPIAR MODAL CLIENTE
    // =========================
    let modalCliente = document.getElementById("modalCliente");

    if (modalCliente) {
        modalCliente.addEventListener("show.bs.modal", function () {

            document.getElementById("buscarClienteModal").value = "";
            document.getElementById("resultadosClientes").innerHTML = "";
            document.getElementById("formNuevoCliente").style.display = "none";
        });
    }

    // =========================
    // BUSCAR CLIENTE
    // =========================
    let inputCliente = document.getElementById("buscarClienteModal");

    if (inputCliente) {
        inputCliente.addEventListener("keyup", function () {

            let q = this.value;

            if (q.length < 2) return;

            fetch(`/api/clientes?q=${q}`)
                .then(res => res.json())
                .then(data => {

                    clientesCache = data;

                    let html = "<ul class='list-group'>";

                    if (data.length === 0) {
                        html += `
                        <li class="list-group-item text-muted">
                            No encontrado
                        </li>`;
                    }

                    data.forEach((c, i) => {
                        html += `
                        <li class="list-group-item d-flex justify-content-between align-items-center"
                            onclick="seleccionarCliente(${i})">
                            <span>${c.nombre} - ${c.documento}</span>
                            <i class="bi bi-send-fill"></i>
                        </li>`;
                    });

                    html += "</ul>";

                    document.getElementById("resultadosClientes").innerHTML = html;
                });
        });
    }

    window.seleccionarCliente = function (index) {

        let c = clientesCache[index];

        document.getElementById("cliente_id").value = c.id;
        document.getElementById("clienteSeleccionado").innerHTML =
            `<b>${c.nombre}</b> - ${c.documento}`;

        bootstrap.Modal.getInstance(
            document.getElementById("modalCliente")
        ).hide();
    };

    // =========================
    // LIMPIAR MODAL PRODUCTO
    // =========================
    let modalProducto = document.getElementById("modalProducto");

    if (modalProducto) {
        modalProducto.addEventListener("show.bs.modal", function () {

            let input = document.getElementById("buscarProductoModal");
            let resultados = document.getElementById("resultadosProductos");

            if (input) input.value = "";
            if (resultados) resultados.innerHTML = "";

            productosCache = [];
        });
    }

    // =========================
    // BUSCAR PRODUCTOS EN MODAL
    // =========================
    let inputProducto = document.getElementById("buscarProductoModal");

    if (inputProducto) {
        inputProducto.addEventListener("keyup", function () {

            let q = this.value.trim();

            if (q.length < 2) {
                document.getElementById("resultadosProductos").innerHTML = "";
                return;
            }

            fetch(`/api/producto?q=${encodeURIComponent(q)}`)
                .then(res => res.json())
                .then(data => {

                    productosCache = data;

                    let html = "<ul class='list-group'>";

                    if (data.length === 0) {
                        html += `
                    <li class="list-group-item text-muted">
                        No encontrado
                    </li>`;
                    }

                    data.forEach((p, i) => {
                        html += `
                    <li class="list-group-item d-flex justify-content-between align-items-center"
                        onclick="agregarDesdeModal(${i})">

                        <span>${p.nombre} - S/ ${p.precio}</span>

                        <i class="bi bi-send-fill"></i>
                    </li>`;
                    });

                    html += "</ul>";

                    document.getElementById("resultadosProductos").innerHTML = html;
                })
                .catch(err => {
                    console.error(err);
                    alert("Error buscando productos");
                });
        });
    }

    // =========================
    // AGREGAR DESDE MODAL
    // =========================
    window.agregarDesdeModal = function (index) {

        agregarAlCarrito(productosCache[index]);

        let modalEl = document.getElementById("modalProducto");
        let modal = bootstrap.Modal.getInstance(modalEl)
            || new bootstrap.Modal(modalEl);

        modal.hide();
    };

});

// =========================
// 👤 MOSTRAR FORM NUEVO CLIENTE
// =========================
window.mostrarFormularioCliente = function () {

    console.log("click nuevo cliente");

    let form = document.getElementById("formNuevoCliente");

    if (!form) {
        console.error("No existe formNuevoCliente");
        return;
    }

    form.style.display =
        form.style.display === "none" || form.style.display === ""
            ? "block"
            : "none";
};

// =========================
// 💾 GUARDAR CLIENTE RÁPIDO
// =========================
window.guardarClienteRapido = function () {

    let nombre = document.getElementById("nuevoNombre").value.trim();
    let documento = document.getElementById("nuevoDocumento").value.trim();
    let direccion = document.getElementById("nuevoDireccion").value.trim();

    if (!nombre) {
        alert("Ingrese nombre del cliente");
        return;
    }

    fetch("/api/clientes/nuevo", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            nombre,
            documento,
            direccion
        })
    })
        .then(res => res.json())
        .then(data => {

            if (!data.ok) {
                alert(data.error || "Error al guardar cliente");
                return;
            }

            document.getElementById("cliente_id").value = data.cliente.id;
            document.getElementById("clienteSeleccionado").innerHTML =
                `<b>${data.cliente.nombre}</b> - ${data.cliente.documento || ""}`;

            document.getElementById("nuevoNombre").value = "";
            document.getElementById("nuevoDocumento").value = "";
            document.getElementById("nuevoDireccion").value = "";
            document.getElementById("formNuevoCliente").style.display = "none";

            let modalEl = document.getElementById("modalCliente");
            bootstrap.Modal.getInstance(modalEl).hide();
        })
        .catch(err => {
            console.error(err);
            alert("Error al crear cliente");
        });
};

// =========================
// 🧾 VENTAS RECIENTES
// =========================
function cargarVentasRecientes() {

    fetch("/api/ventas_recientes")
        .then(res => res.json())
        .then(data => {

            let html = "";

            if (!data || data.length === 0) {
                html = `
                <tr>
                    <td colspan="6" class="text-center text-muted">
                        Sin ventas recientes
                    </td>
                </tr>`;
            }

            data.forEach(v => {

                html += `
                <tr>
                    <td>${v.id}</td>
                    <td>
                        <div class="small text-muted">${v.fecha}</div>
                        <div class="fw-bold">${v.hora}</div>
                    </td>
                    <td>${v.cliente || "Sin cliente"}</td>
                    <td class="fw-bold text-success">
                        S/ ${parseFloat(v.total).toFixed(2)}
                    </td>
                    <td>
                        <span class="badge bg-success">
                            ${v.tipo_pago || "Efectivo"}
                        </span>
                    </td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary">
                            <i class="bi bi-eye"></i>
                        </button>
                    </td>
                </tr>`;
            });

            document.getElementById("ventasRecientes").innerHTML = html;
        });
}