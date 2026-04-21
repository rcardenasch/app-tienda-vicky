
document.addEventListener("DOMContentLoaded", function () {

    const inputCodigo = document.getElementById("codigo_barras");
    const inputNombre = document.querySelector("input[name='nombre']");

    let buffer = "";
    let lastKeyTime = Date.now();

    inputCodigo.addEventListener("keydown", function (e) {

        const currentTime = Date.now();

        // Detectar si es lector (rápido) o humano (lento)
        if (currentTime - lastKeyTime > 100) {
            buffer = "";
        }

        lastKeyTime = currentTime;

        if (e.key === "Enter") {
            e.preventDefault();

            let codigo = inputCodigo.value.trim();

            if (codigo.length < 3) return;

            buscarProducto(codigo);
            return;
        }

        buffer += e.key;

        // Si viene de lector → auto ejecutar sin Enter
        if (buffer.length >= 8) {
            setTimeout(() => {
                let codigo = inputCodigo.value.trim();
                if (codigo.length >= 8) {
                    buscarProducto(codigo);
                }
            }, 50);
        }

    });


    // 🔥 Autofocus correcto al abrir modal
    const modal = document.getElementById('modalNuevo');
    modal.addEventListener('shown.bs.modal', function () {
        inputCodigo.focus();
    });

    inputCodigo.addEventListener("input", function () {

    let codigo = inputCodigo.value.trim();

    if (codigo.length >= 8) {
        buscarProducto(codigo);
    }

});


});

function buscarProducto(codigo) {

    // 🔊 Beep seguro
    let beep = document.getElementById("beep");
    if (beep) beep.play().catch(() => { });

    fetch(`/productos/buscar?codigo=${codigo}`)
        .then(res => res.json())
        .then(data => {

           if (data.existe) {
                // 🔴 AQUÍ LLAMAS
                mostrarMensaje("⚠️ Producto ya existe", "warning");

                document.querySelector("input[name='nombre']").value = data.nombre;

            } else {
                // 🟢 AQUÍ TAMBIÉN
                mostrarMensaje("✅ Producto nuevo, puedes registrarlo", "success");
            }

            //inputNombre.focus();
            document.querySelector("input[name='nombre']").focus();

        });
}

function mostrarMensaje(texto, tipo) {

    const div = document.getElementById("mensajeProducto");

    div.className = `alert alert-${tipo}`;
    div.innerText = texto;
    div.classList.remove("d-none");

    setTimeout(() => {
        div.classList.add("d-none");
    }, 2000);
}

document.getElementById("codigo_barras").addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
        document.getElementById("beep").play();
    }
});

var modal = document.getElementById('modalNuevo');
modal.addEventListener('shown.bs.modal', function () {
    document.getElementById("codigo_barras").focus();
});

let scanner = null;
let ultimoCodigo = null;
let tiempoUltimaLectura = 0;
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
            let inputBuscar = document.getElementById("codigo_barras");
            if (inputBuscar) {
                inputBuscar.value = codigo;
            }

            buscarProducto(codigo);
        }
    );
};

let usandoTrasera = true;

function cambiarCamara() {
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
                scanner.stop();
                buscarProducto(codigo);
            }
        );
    });
}

// =========================
// ❌ APAGAR CÁMARA AL CERRAR MODAL
// =========================
const modalNuevo = document.getElementById("modalNuevo");

modalNuevo.addEventListener("hidden.bs.modal", function () {

    if (scanner) {
        scanner.stop()
            .then(() => {
                scanner.clear();
                scanner = null;
                console.log("Cámara apagada correctamente");
            })
            .catch(err => {
                console.error("Error apagando cámara:", err);
            });
    }

    // limpiar estado visual
    let estado = document.getElementById("scannerEstado");
    if (estado) {
        estado.innerText = "";
    }

    // limpiar último código leído
    ultimoCodigo = null;
});

$('.datatable').DataTable({
    language: {
        emptyTable: "No hay productos"
    }
});