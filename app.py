# =========================
# app.py
# =========================

from flask import Flask, request, redirect, url_for, render_template, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import (db,User, Role, Permission,Module, Producto,Categoria,Venta,Cliente,Compra,DetalleCompra,DetalleVenta,Proveedor,Almacen,
    StockAlmacen,KardexMovimiento,TransferenciaAlmacen,TransferenciaDetalle)

from config import Config
from functools import wraps
from flask import jsonify
import os
from werkzeug.utils import secure_filename
from flask import get_flashed_messages
import re
import json
import uuid
from sqlalchemy import cast, String,or_,func
from datetime import datetime
from sqlalchemy import text


BASE_DIR = os.path.abspath(os.path.dirname(__file__))


app = Flask(__name__)
app.config.from_object(Config)



# INIT
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = None

@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for('login'))
#login_manager.login_message = None


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Importante Agregar todos los modulos que e creen

MODULOS = [
    "usuarios",
    "roles",
    "productos",
    "categorias",
    "clientes",
    "ventas",
    "compras",
    "proveedores",
    "kardex"
]

ACCIONES = ["ver", "crear", "editar", "eliminar"]

ACCIONES_KARDEX = [
    "ver",
    "editar",
    "ajustar",
    "resetear"
]

def seed_data():
    try:
        # -------- ROLE --------
        role_admin = Role.query.filter_by(name="admin").first()
        if not role_admin:
            role_admin = Role(name="admin")
            db.session.add(role_admin)
            db.session.commit()

        # -------- ADMIN --------
        admin = User.query.filter_by(username="admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@test.com",
                full_name="Administrador"
            )
            admin.set_password("admin")
            db.session.add(admin)
            db.session.commit()

        if role_admin not in admin.roles:
            admin.roles.append(role_admin)
            db.session.commit()

        # -------- MODULOS + PERMISOS --------
        for nombre_modulo in MODULOS:
            mod = Module.query.filter_by(name=nombre_modulo).first()

            if not mod:
                mod = Module(name=nombre_modulo)
                db.session.add(mod)
                db.session.commit()

            acciones_modulo = ACCIONES_KARDEX if nombre_modulo == "kardex" else ACCIONES

            for acc in acciones_modulo:
                perm = Permission.query.filter_by(
                    module_id=mod.id,
                    action=acc
                ).first()

                if not perm:
                    db.session.add(Permission(module_id=mod.id, action=acc))

        db.session.commit()

        # -------- ASIGNAR PERMISOS --------
        for perm in Permission.query.all():
            if perm not in role_admin.permissions:
                role_admin.permissions.append(perm)

        db.session.commit()

        print("✅ Datos iniciales OK")

    except Exception as e:
        print("⚠️ Error en seed:", e)


# -------- CONTEXTO INICIALIZACION --------
with app.app_context():
    try:
        print("🚀 Iniciando aplicación...")

        # ✅ SOLO crear tablas (SEGURO)
        db.create_all()
        if os.getenv("RENDER") == "true":
            seed_data()
            print("✅ Tablas verificadas/creadas")

    except Exception as e:
        print("❌ Error al iniciar BD:", e)   
#-- Funciones globales--
def validar_texto(valor, campo, min_len=3, max_len=150):
    if not valor:
        return f"{campo} es obligatorio"
    if len(valor) < min_len:
        return f"{campo} debe tener al menos {min_len} caracteres"
    if len(valor) > max_len:
        return f"{campo} no debe exceder {max_len} caracteres"
    return None


def validar_numero(valor, campo, tipo=float, minimo=0):
    try:
        num = tipo(valor)
        if num < minimo:
            return f"{campo} no puede ser negativo"
        return None
    except:
        return f"{campo} inválido"


def validar_email(email):
    if not email:
        return None
    regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if not re.match(regex, email):
        return "Email inválido"
    return None

def obtener_stock(producto_id, almacen_id):
    stock = StockAlmacen.query.filter_by(producto_id=producto_id, almacen_id=almacen_id).first()
    if not stock:
        # Crear registro si no existe
        stock = StockAlmacen(producto_id=producto_id, almacen_id=almacen_id, stock=0)
        db.session.add(stock)
        db.session.commit()
    return stock

# =========================
# PERMISOS
# =========================

def permission_required(modulo, accion):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for("login"))

            permiso = f"{modulo}.{accion}"

            if not current_user.has_permission(permiso):
                flash("No tienes permisos", "danger")
                return redirect(url_for("index"))

            return f(*args, **kwargs)
        return wrapper
    return decorator


# =========================
# RUTAS BASE
# =========================

@app.route('/')
@login_required
def index():
    return redirect(url_for("dashboard"))

@app.route('/login', methods=['GET','POST'])
def login():

    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()

        if user and user.check_password(request.form['password']):
            login_user(user)
            return redirect(url_for('index'))

        flash('Credenciales inválidas','danger')

    return render_template("login.html")

@app.route('/logout')
@login_required
def logout():
    from flask import session
    logout_user()
    session.clear()  # 🔥 borra toda la sesión
    return redirect(url_for('login'))


# =========================
# EJEMPLO CRUD USUARIOS
# =========================
@app.route("/usuarios")
@login_required
@permission_required("usuarios","ver")
def usuarios_list():
    #print([ (p.module.name, p.action) for r in current_user.roles for p in r.permissions ])
    #return "SI FUNCIONA USUARIOS"
    return render_template(
        "usuarios.html",
        lista=User.query.all(),
        roles=Role.query.all()
    )
@app.route("/usuarios/nuevo", methods=["POST"])
@login_required
@permission_required("usuarios","crear")
def usuarios_nuevo():
    try:
        # -------------------------
        # OBTENER DATOS
        # -------------------------
        username = request.form.get("username")
        password = request.form.get("password")
        email = request.form.get("email")
        full_name = request.form.get("full_name")
        roles_ids = request.form.getlist("roles")  # 👈 importante

        # -------------------------
        # VALIDACIONES
        # -------------------------
        if not username or not password:
            flash("Usuario y contraseña son obligatorios", "danger")
            return redirect(url_for("usuarios_list"))

        # Usuario único
        if User.query.filter_by(username=username).first():
            flash("El username ya existe", "warning")
            return redirect(url_for("usuarios_list"))

        # Email único (opcional pero recomendado)
        if email and User.query.filter_by(email=email).first():
            flash("El email ya está registrado", "warning")
            return redirect(url_for("usuarios_list"))

        # -------------------------
        # CREAR USUARIO
        # -------------------------
        nuevo_usuario = User(
            username=username,
            email=email,
            full_name=full_name
        )

        # 🔐 usar tu método del modelo
        nuevo_usuario.set_password(password)

        # -------------------------
        # ASIGNAR ROLES
        # -------------------------
        if roles_ids:
            roles = Role.query.filter(Role.id.in_(roles_ids)).all()
            nuevo_usuario.roles = roles  # 👈 relación many-to-many

        # -------------------------
        # GUARDAR
        # -------------------------
        db.session.add(nuevo_usuario)
        db.session.commit()

        flash("Usuario creado correctamente", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error al crear usuario: {str(e)}", "danger")

    return redirect(url_for("usuarios_list"))

@app.route("/usuarios/editar/<int:id>", methods=["POST"])
@login_required
@permission_required("usuarios","editar")
def usuarios_editar(id):
    usuario = User.query.get_or_404(id)

    try:
        username = request.form.get("username")
        email = request.form.get("email")
        full_name = request.form.get("full_name")
        roles_ids = request.form.getlist("roles")

        # -------------------------
        # VALIDACIONES
        # -------------------------
        if not username:
            flash("El username es obligatorio", "danger")
            return redirect(url_for("usuarios_list"))

        # Validar username único (excepto el mismo usuario)
        existe = User.query.filter(User.username == username, User.id != id).first()
        if existe:
            flash("El username ya está en uso", "warning")
            return redirect(url_for("usuarios_list"))

        # Validar email único
        if email:
            existe_email = User.query.filter(User.email == email, User.id != id).first()
            if existe_email:
                flash("El email ya está en uso", "warning")
                return redirect(url_for("usuarios_list"))

        # -------------------------
        # ACTUALIZAR DATOS
        # -------------------------
        usuario.username = username
        usuario.email = email
        usuario.full_name = full_name

        # -------------------------
        # ACTUALIZAR ROLES
        # -------------------------
        usuario.roles = []  # limpiar roles actuales

        if roles_ids:
            roles = Role.query.filter(Role.id.in_(roles_ids)).all()
            usuario.roles = roles

        db.session.commit()
        flash("Usuario actualizado correctamente", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error al actualizar: {str(e)}", "danger")

    return redirect(url_for("usuarios_list"))

@app.route("/usuarios/eliminar/<int:id>", methods=["POST"])
@login_required
@permission_required("usuarios","eliminar")
def usuarios_eliminar(id):
    usuario = User.query.get_or_404(id)

    try:
        # ⚠️ evitar eliminarse a sí mismo
        if usuario.id == current_user.id:
            flash("No puedes eliminar tu propio usuario", "warning")
            return redirect(url_for("usuarios_list"))

        db.session.delete(usuario)
        db.session.commit()

        flash("Usuario eliminado correctamente", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error al eliminar: {str(e)}", "danger")

    return redirect(url_for("usuarios_list"))

# =========================
# CRUD ROLES
# =========================

@app.route("/roles")
@login_required
@permission_required("roles", "ver")
def roles_list():
    
    permisos = Permission.query.all()

    from collections import defaultdict
    permisos_agrupados = defaultdict(list)

    for p in permisos:
        modulo = p.module.name if p.module else "Sin módulo"
        permisos_agrupados[modulo].append(p)

    return render_template(
        "roles.html",
        lista=Role.query.all(),
        permisos=permisos,  # reutilizas
        permisos_agrupados=permisos_agrupados,
        modulos=Module.query.all()
    )


@app.route("/roles/nuevo", methods=["POST"])
@login_required
@permission_required("roles", "crear")
def roles_nuevo():
    try:
        name = request.form.get("name")
        permisos_ids = request.form.getlist("permisos")

        if not name:
            flash("El nombre del rol es obligatorio", "danger")
            return redirect(url_for("roles_list"))

        if Role.query.filter_by(name=name).first():
            flash("El rol ya existe", "warning")
            return redirect(url_for("roles_list"))

        nuevo = Role(name=name)

        if permisos_ids:
            permisos = Permission.query.filter(Permission.id.in_(permisos_ids)).all()
            nuevo.permissions = permisos

        db.session.add(nuevo)
        db.session.commit()

        flash("Rol creado correctamente", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for("roles_list"))


@app.route("/roles/editar/<int:id>", methods=["POST"])
@login_required
@permission_required("roles", "editar")
def roles_editar(id):
    rol = Role.query.get_or_404(id)

    try:
        rol.name = request.form.get("name")
        permisos_ids = request.form.getlist("permisos")

        # actualizar permisos
        rol.permissions = []
        if permisos_ids:
            permisos = Permission.query.filter(Permission.id.in_(permisos_ids)).all()
            rol.permissions = permisos

        db.session.commit()
        flash("Rol actualizado", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for("roles_list"))


@app.route("/roles/eliminar/<int:id>", methods=["POST"])
@login_required
@permission_required("roles", "eliminar")
def roles_eliminar(id):
    rol = Role.query.get_or_404(id)

    try:
        db.session.delete(rol)
        db.session.commit()
        flash("Rol eliminado", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"No se pudo eliminar: {str(e)}", "danger")

    return redirect(url_for("roles_list"))
# =========================
# CRUD PRODUCTO
# =========================
@app.route("/productos")
@login_required
@permission_required("productos", "ver")
def productos_list():
    return render_template(
        "productos.html",
        lista=Producto.query.all(),
        categorias=Categoria.query.all()
    )

@app.route("/productos/nuevo", methods=["POST"])
@login_required
@permission_required("productos", "crear")
def productos_nuevo():

    try:
        nombre = request.form.get("nombre", "").strip()
        codigo = request.form.get("codigo_barras", "").strip()
        categoria_id = request.form.get("categoria_id")
        precio_compra = request.form.get("precio_compra")
        precio_venta = request.form.get("precio_venta")
        stock = request.form.get("stock")

        # 🔥 VALIDACIONES MEJORADAS
            
        if not codigo:
            flash("Debe ingresar o escanear un código", "danger")
            return redirect(url_for("productos_list"))

        if not nombre:
            flash("Debe ingresar nombre", "danger")
            return redirect(url_for("productos_list"))

        # 🔥 VALIDACIÓN NUMÉRICA SEGURA
        try:
            precio_compra = float(precio_compra)
            precio_venta = float(precio_venta)
            stock = float(stock)
        except:
            flash("Valores numéricos inválidos", "danger")
            return redirect(url_for("productos_list"))

        # 🔥 VALIDACIÓN ÚNICA MÁS EFICIENTE
        existente = Producto.query.filter(
            (Producto.codigo_barras == codigo) |
            (Producto.nombre == nombre)
        ).first()

        if existente:
            flash("Producto ya existe (nombre o código)", "warning")
            return redirect(url_for("productos_list"))

        producto = Producto(
            nombre=nombre,
            codigo_barras=codigo,
            categoria_id=int(categoria_id) if categoria_id else None,
            precio_compra=precio_compra,
            precio_venta=precio_venta,
            stock=stock
        )

        db.session.add(producto)
        db.session.commit()

        flash("✅ Producto creado correctamente", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for("productos_list"))


@app.route("/productos/editar/<int:id>", methods=["POST"])
@login_required
@permission_required("productos", "editar")
def productos_editar(id):

    producto = Producto.query.get_or_404(id)

    try:
        producto.nombre = request.form.get("nombre")
        producto.codigo_barras = request.form.get("codigo_barras")
        producto.categoria_id = request.form.get("categoria_id")
        producto.precio_compra = request.form.get("precio_compra")
        producto.precio_venta = request.form.get("precio_venta")
        producto.stock = request.form.get("stock")

        archivo = request.files.get("imagen")

        if archivo and archivo.filename != "":
            nombre_archivo = secure_filename(archivo.filename)
            ruta = os.path.join(app.config["UPLOAD_FOLDER"], nombre_archivo)
            archivo.save(ruta)
            producto.imagen = nombre_archivo

        db.session.commit()
        flash("Producto actualizado", "success")

    except Exception as e:
        db.session.rollback()
        flash(str(e), "danger")

    return redirect(url_for("productos_list"))


@app.route("/productos/eliminar/<int:id>", methods=["POST"])
@login_required
@permission_required("productos", "eliminar")
def productos_eliminar(id):

    producto = Producto.query.get_or_404(id)

    try:
        db.session.delete(producto)
        db.session.commit()
        flash("Producto eliminado", "success")

    except Exception as e:
        db.session.rollback()
        flash(str(e), "danger")

    return redirect(url_for("productos_list"))

@app.route("/api/producto")
@login_required
def buscar_productos():
    q = request.args.get("q", "").strip()

    if not q:
        return jsonify([])

    productos = Producto.query.filter(
        or_(
            Producto.nombre.ilike(f"%{q}%"),
            cast(Producto.codigo_barras, String).ilike(f"%{q}%")
        )
    ).order_by(
        Producto.nombre.asc()
    ).limit(10).all()

    return jsonify([
        {
            "id": p.id,
            "codigo_barras": p.codigo_barras,
            "nombre": p.nombre,
            "precio": p.precio_venta,
            "stock":p.stock
        } for p in productos
    ])

@app.route("/productos/buscar")
@login_required
def productos_buscar():
    codigo = request.args.get("codigo")

    producto = Producto.query.filter_by(codigo_barras=codigo).first()

    if producto:
        return {
            "existe": True,
            "codigo_barras": producto.codigo_barras,
            "nombre": producto.nombre,
            "precio": producto.precio_venta
        }
    else:
        return {"existe": False}

#========================
# CRUD CLIENTES
# =======================
@app.route("/clientes")
@login_required
@permission_required("clientes", "ver")
def clientes_list():
    return render_template("clientes.html", lista=Cliente.query.all())


@app.route("/clientes/nuevo", methods=["POST"])
@login_required
@permission_required("clientes", "crear")
def clientes_nuevo():

    try:
        # Detectar si es JSON (desde POS)
        es_json = request.is_json

        if es_json:
            data = request.get_json()
            nombre = data.get("nombre")
            documento = data.get("documento")
            telefono = data.get("telefono")
        else:
            nombre = request.form.get("nombre")
            documento = request.form.get("documento")
            telefono = request.form.get("telefono")
            direccion=request.form.get("direccion")

        # VALIDACIONES
        error = validar_texto(nombre, "Nombre")
        if error:
            if es_json:
                return jsonify({"ok": False, "error": error})
            flash(error, "danger")
            return redirect(url_for("clientes_list"))

        if documento and Cliente.query.filter_by(documento=documento).first():
            if es_json:
                return jsonify({"ok": False, "error": "Documento ya registrado"})
            flash("Documento ya registrado", "warning")
            return redirect(url_for("clientes_list"))

        cliente = Cliente(
            nombre=nombre,
            documento=documento,
            telefono=telefono,
            direccion=direccion
        )

        db.session.add(cliente)
        db.session.commit()

        # 🔥 RESPUESTA DIFERENTE SEGÚN CONTEXTO
        if es_json:
            return jsonify({
                "ok": True,
                "cliente": {
                    "id": cliente.id,
                    "nombre": cliente.nombre,
                    "documento": cliente.documento,
                    "direccion":cliente.direccion
                }
            })

        flash("Cliente creado", "success")

    except Exception as e:
        db.session.rollback()

        if request.is_json:
            return jsonify({"ok": False, "error": str(e)})

        flash(str(e), "danger")

    return redirect(url_for("clientes_list"))


@app.route("/clientes/editar/<int:id>", methods=["POST"])
@login_required
@permission_required("clientes", "editar")
def clientes_editar(id):

    cli = Cliente.query.get_or_404(id)

    cli.nombre = request.form.get("nombre")
    cli.documento = request.form.get("documento")
    cli.telefono = request.form.get("telefono")
    cli.direccion=request.form.get("direccion")

    db.session.commit()

    flash("Cliente actualizado", "success")
    return redirect(url_for("clientes_list"))

@app.route("/clientes/eliminar/<int:id>", methods=["POST"])
@login_required
@permission_required("clientes", "eliminar")
def clientes_eliminar(id):

    cliente = Cliente.query.get_or_404(id)

    try:
        # validar si tiene ventas
        if Venta.query.filter_by(cliente_id=cliente.id).first():
            flash("No puedes eliminar cliente con ventas", "danger")
            return redirect(url_for("clientes_list"))

        db.session.delete(cliente)
        db.session.commit()

        flash("Cliente eliminado", "success")

    except Exception as e:
        db.session.rollback()
        flash(str(e), "danger")

    return redirect(url_for("clientes_list"))

# =========================
# CRUD VENTAS
# =========================
@app.route("/ventas")
@login_required
def ventas_list():
    almacenes = Almacen.query.filter_by(activo=True).all()

    return render_template(
        "ventas.html",
        almacenes=almacenes
    )
@app.route("/ventas/nuevo", methods=["POST"])
@login_required
@permission_required("ventas", "crear")
def ventas_nuevo():

    try:
        cliente_id = request.form.get("cliente_id")
        almacen_id = int(request.form.get("almacen_id"))
        productos = request.form.getlist("producto_id")
        cantidades = request.form.getlist("cantidad")
        tipo_comprobante = request.form.get("tipo_comprobante")

        if not productos:
            flash("Debe agregar productos", "danger")
            return redirect(url_for("ventas_list"))

        venta = Venta(
            cliente_id=int(cliente_id) if cliente_id else None,
            usuario_id=current_user.id,
            tipo_comprobante=tipo_comprobante,
            total=0
        )

        db.session.add(venta)
        db.session.flush()

        total = 0

        for i in range(len(productos)):
            producto_id = int(productos[i])
            cantidad = float(cantidades[i])

            producto = Producto.query.get(producto_id)
            stock_item = obtener_stock(producto.id, almacen_id)

            # ✔ Calcula stock real considerando la venta actual
            stock_disponible = stock_item.stock

            if cantidad > stock_disponible:
                
                raise Exception(f"Stock insuficiente en almacén {stock_item.almacen.nombre} para {producto.nombre}. Disponible: {stock_disponible}")

            stock_anterior = stock_item.stock

            subtotal = cantidad * producto.precio_venta

            detalle = DetalleVenta(
                venta_id=venta.id,
                producto_id=producto.id,
                cantidad=cantidad,
                precio=producto.precio_venta,
                subtotal=subtotal
            )
            db.session.add(detalle)

            # DESCONTAR STOCK
            stock_item.stock -= cantidad

            # ACTUALIZAR STOCK GLOBAL
            producto.stock = db.session.query(
                func.coalesce(func.sum(StockAlmacen.stock), 0)
            ).filter(
                StockAlmacen.producto_id == producto.id
            ).scalar()
            # =========================
            # KARDEX VENTA
            # =========================
            movimiento = KardexMovimiento(
                producto_id=producto.id,
                almacen_id=almacen_id,
                tipo_movimiento="VENTA",
                cantidad=cantidad,
                stock_anterior=stock_anterior,
                stock_nuevo=stock_item.stock,
                costo_unitario=producto.precio_compra or 0,
                usuario_id=current_user.id,
                venta_id=venta.id,
                observacion=f"Venta #{venta.id}"
            )
            db.session.add(movimiento)

            total += subtotal

        venta.total = total

        db.session.commit()

        flash("Venta registrada correctamente", "success")

    except Exception as e:
        db.session.rollback()
        flash(str(e), "danger")

    return redirect(url_for("ventas_list"))

@app.route("/api/clientes")
def buscar_clientes():
    q = request.args.get("q", "")

    clientes = Cliente.query.filter(
        (Cliente.nombre.ilike(f"%{q}%")) |
        (cast(Cliente.documento, String).ilike(f"%{q}%"))
    ).limit(10).all()

    return jsonify([
        {
            "id": c.id,
            "nombre": c.nombre,
            "documento": c.documento,
            "direccion": getattr(c, "direccion", "")
        }
        for c in clientes
    ])


@app.route("/api/clientes/nuevo", methods=["POST"])
@login_required
def crear_cliente_rapido():
    try:
        data = request.get_json()

        nombre = data.get("nombre", "").strip()
        documento = data.get("documento", "").strip()
        direccion = data.get("direccion", "").strip()

        if not nombre:
            return jsonify({
                "ok": False,
                "error": "Nombre requerido"
            })

        # validar duplicado documento
        if documento:
            existe = Cliente.query.filter_by(documento=documento).first()
            if existe:
                return jsonify({
                    "ok": False,
                    "error": "Documento ya existe"
                })

        cliente = Cliente(
            nombre=nombre,
            documento=documento,
            direccion=direccion
        )

        db.session.add(cliente)
        db.session.commit()

        return jsonify({
            "ok": True,
            "cliente": {
                "id": cliente.id,
                "nombre": cliente.nombre,
                "documento": cliente.documento
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "ok": False,
            "error": str(e)
        })
    
@app.route("/api/ventas_recientes")
def ventas_recientes():

    ventas = Venta.query.order_by(Venta.id.desc()).limit(10).all()

    return jsonify([
        {
            "id": v.id,
            "total": v.total,
            "fecha": v.fecha.strftime("%d/%m/%Y"),  # 🔥 fecha
            "hora": v.fecha.strftime("%H:%M:%S"),   # 🔥 hora
            "cliente": v.cliente.nombre if v.cliente else None,
            "tipo_pago": "Efectivo"  # 🔥 o desde DB si lo tienes
        }
        for v in ventas
    ])

# =========================
# CRUD COMPRAS
# =========================
@app.route("/compras")
@login_required
def compras_list():

    almacenes = Almacen.query.filter_by(activo=True).all()

    return render_template(
        "compras.html",
        almacenes=almacenes
    )
   

@app.route("/compras/nuevo", methods=["GET", "POST"])
@login_required
@permission_required("compras", "crear")
def compras_nuevo():

    if request.method == "GET":
            almacenes = Almacen.query.filter_by(activo=True).all()

            return render_template(
                "compras.html",
                almacenes=almacenes
            )

    try:
        proveedor_id = request.form.get("proveedor_id")
        productos = request.form.getlist("producto_id")
        cantidades = request.form.getlist("cantidad")
        precios = request.form.getlist("precio")

        if not proveedor_id:
            flash("Seleccione proveedor", "danger")
            return redirect(url_for("compras_nuevo"))

        if not productos:
            flash("Debe agregar productos", "danger")
            return redirect(url_for("compras_nuevo"))

        almacen_id = request.form.get("almacen_id")
        compra = Compra(
            proveedor_id=int(proveedor_id),
            almacen_id=int(almacen_id),
            usuario_id=current_user.id,
            total=0
        )

        db.session.add(compra)
        db.session.flush()  # 🔥 IMPORTANTE (para obtener compra.id)

        total = 0

        for i in range(len(productos)):

            producto_id = int(productos[i])
            cantidad = float(cantidades[i])
            precio = float(precios[i])

            producto = Producto.query.get(producto_id)

            subtotal = cantidad * precio

            # =========================
            # DETALLE COMPRA
            # =========================
            detalle = DetalleCompra(
                compra_id=compra.id,
                producto_id=producto.id,
                cantidad=cantidad,
                precio=precio,
                subtotal=subtotal
            )
            db.session.add(detalle)

            # =========================
            # STOCK POR ALMACÉN
            # =========================
            stock_item = obtener_stock(producto.id, compra.almacen_id)

            stock_anterior = stock_item.stock

            # =========================
            # PROMEDIO PONDERADO
            # =========================
            stock_actual = stock_item.stock
            costo_actual = producto.precio_compra or 0

            nuevo_costo = (
                ((stock_actual * costo_actual) + (cantidad * precio))
                / (stock_actual + cantidad)
            ) if (stock_actual + cantidad) > 0 else precio

            producto.precio_compra = nuevo_costo

            # =========================
            # ACTUALIZAR STOCK
            # =========================
            stock_item.stock += cantidad

            # stock global opcional
            producto.stock = db.session.query(
                func.coalesce(func.sum(StockAlmacen.stock), 0)
            ).filter(
                StockAlmacen.producto_id == producto.id
            ).scalar()

            # =========================
            # KARDEX MOVIMIENTO
            # =========================
            movimiento = KardexMovimiento(
                producto_id=producto.id,
                almacen_id=compra.almacen_id,
                tipo_movimiento="COMPRA",
                cantidad=cantidad,
                stock_anterior=stock_anterior,
                stock_nuevo=stock_item.stock,
                costo_unitario=precio,
                usuario_id=current_user.id,
                compra_id=compra.id,
                observacion=f"Compra #{compra.id}"
            )

            db.session.add(movimiento)

            total += subtotal

        compra.total = total

        db.session.commit()

        flash("✅ Compra registrada correctamente", "success")

    except Exception as e:
        db.session.rollback()
        flash(str(e), "danger")

    return redirect(url_for("compras_nuevo"))

#======================================================================================
# PROVEEDORES 
#======================================================================================
@app.route("/proveedores")
@login_required
@permission_required("proveedores", "ver")
def proveedores_list():
    return render_template("proveedores.html", lista=Proveedor.query.all())


@app.route("/proveedores/nuevo", methods=["POST"])
@login_required
@permission_required("proveedores", "crear")
def proveedores_nuevo():

    try:
        # Detectar si es JSON (desde POS)
        es_json = request.is_json

        if es_json:
            data = request.get_json()
            nombre = data.get("nombre")
            direccion = data.get("direccion")
            telefono = data.get("telefono")
        else:
            nombre = request.form.get("nombre")
            direccion = request.form.get("direccion")
            telefono = request.form.get("telefono")

        # VALIDACIONES
        error = validar_texto(nombre, "Nombre")
        if error:
            if es_json:
                return jsonify({"ok": False, "error": error})
            flash(error, "danger")
            return redirect(url_for("proveedores_list"))

        if nombre and Proveedor.query.filter_by(nombre=nombre).first():
            if es_json:
                return jsonify({"ok": False, "error": "Proveedor ya registrado"})
            flash("Proveedor ya registrado", "warning")
            return redirect(url_for("proveedores_list"))

        proveedor = Proveedor(
            nombre=nombre,
            direccion=direccion,
            telefono=telefono
        )

        db.session.add(proveedor)
        db.session.commit()

        # 🔥 RESPUESTA DIFERENTE SEGÚN CONTEXTO
        if es_json:
            return jsonify({
                "ok": True,
                "proveedor": {
                    "id": proveedor.id,
                    "nombre": proveedor.nombre,
                    "direccion": proveedor.direccion
                }
            })

        flash("Proveedor creado", "success")

    except Exception as e:
        db.session.rollback()

        if request.is_json:
            return jsonify({"ok": False, "error": str(e)})

        flash(str(e), "danger")

    return redirect(url_for("proveedores_list"))


@app.route("/proveedores/editar/<int:id>", methods=["POST"])
@login_required
@permission_required("proveedores", "editar")
def proveedores_editar(id):

    prov = Proveedor.query.get_or_404(id)

    prov.nombre = request.form.get("nombre")
    prov.direccion = request.form.get("direccion")
    prov.telefono = request.form.get("telefono")

    db.session.commit()

    flash("Proveedor actualizado", "success")
    return redirect(url_for("proveedores_list"))

@app.route("/proveedores/eliminar/<int:id>", methods=["POST"])
@login_required
@permission_required("proveedores", "eliminar")
def proveedores_eliminar(id):

    proveedor = Proveedor.query.get_or_404(id)

    try:
        # validar si tiene ventas
        if Compra.query.filter_by(proveedor_id=proveedor.id).first():
            flash("No puedes eliminar proveedor con compras", "danger")
            return redirect(url_for("proveedores_list"))

        db.session.delete(proveedor)
        db.session.commit()

        flash("Proveedor eliminado", "success")

    except Exception as e:
        db.session.rollback()
        flash(str(e), "danger")

    return redirect(url_for("proveedores_list"))

@app.route("/api/proveedores")
def api_proveedores():
    q = request.args.get("q", "")

    data = Proveedor.query.filter(
        Proveedor.nombre.ilike(f"%{q}%")
    ).limit(10).all()

    return jsonify([
        {"id": p.id, "nombre": p.nombre}
        for p in data
    ])
@app.route("/proveedores/nuevo", methods=["POST"])
def proveedor_nuevo_api():

    data = request.get_json()

    p = Proveedor(
        nombre=data["nombre"],
        telefono=data.get("telefono"),
        direccion=data.get("direccion")
    )

    db.session.add(p)
    db.session.commit()

    return jsonify({"ok": True, "id": p.id})
# =========================
# CRUD CATEGORIAS
# =========================
@app.route("/categorias")
@login_required
@permission_required("categorias", "ver")
def categorias_list():

    categorias = Categoria.query.filter_by(parent_id=None).all()

    return render_template(
        "categorias.html",
        categorias=categorias,
        todas=Categoria.query.all()
    )
 
@app.route("/categorias/nuevo", methods=["POST"])
@login_required
@permission_required("categorias", "crear")
def categorias_nuevo():

    try:
        nombre = request.form.get("nombre", "").strip()
        parent_id = request.form.get("parent_id")

        # 🔥 FIX CLAVE
        parent_id = int(parent_id) if parent_id else None

        # VALIDACIÓN
        if not nombre:
            flash("Nombre requerido", "danger")
            return redirect(url_for("categorias_list"))

        # 🔥 VALIDACIÓN CORRECTA
        existente = Categoria.query.filter_by(
            nombre=nombre,
            parent_id=parent_id
        ).first()

        if existente:
            flash("Categoría ya existe en ese nivel", "warning")
            return redirect(url_for("categorias_list"))

        categoria = Categoria(
            nombre=nombre,
            parent_id=parent_id
        )

        db.session.add(categoria)
        db.session.commit()

        flash("✅ Categoría creada", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for("categorias_list"))

@app.route("/categorias/editar/<int:id>", methods=["POST"])
@login_required
@permission_required("categorias", "editar")
def categorias_editar(id):

    cat = Categoria.query.get_or_404(id)

    cat.nombre = request.form.get("nombre")
    parent_id = request.form.get("parent_id")

    cat.parent_id = int(parent_id) if parent_id else None

    db.session.commit()

    flash("Categoría actualizada", "success")
    return redirect(url_for("categorias_list"))

@app.route("/categorias/eliminar/<int:id>", methods=["POST"])
@login_required
@permission_required("categorias", "eliminar")
def categorias_eliminar(id):

    cat = Categoria.query.get_or_404(id)

    if cat.hijos:
        flash("No puedes eliminar una categoría con subcategorías", "danger")
        return redirect(url_for("categorias_list"))

    db.session.delete(cat)
    db.session.commit()

    flash("Categoría eliminada", "success")
    return redirect(url_for("categorias_list"))

#===============================================================
# Kardex
# ==============================================================
@app.route("/kardex")
@login_required
@permission_required("kardex", "ver")
def kardex_index():

    productos = Producto.query.filter_by(activo=True).all()
    almacenes = Almacen.query.filter_by(activo=True).all()

    movimientos = KardexMovimiento.query.order_by(
        KardexMovimiento.fecha.desc()
    ).limit(100).all()

    total_productos = Producto.query.filter_by(activo=True).count()

    total_stock = db.session.query(
        func.coalesce(func.sum(StockAlmacen.stock), 0)
    ).scalar()

    return render_template(
        "kardex/index.html",
        productos=productos,
        almacenes=almacenes,
        movimientos=movimientos,
        total_productos=total_productos,
        total_stock=total_stock
    )

@app.route("/kardex/reset", methods=["POST"])
@login_required
@permission_required("kardex", "resetear")
def kardex_reset_masivo():

    stocks = StockAlmacen.query.all()

    for s in stocks:
        anterior = s.stock
        s.stock = 0

        movimiento = KardexMovimiento(
            producto_id=s.producto_id,
            almacen_id=s.almacen_id,
            tipo_movimiento="RESET",
            cantidad=anterior,
            stock_anterior=anterior,
            stock_nuevo=0,
            costo_unitario=s.producto.precio_compra or 0,
            usuario_id=current_user.id,
            observacion="Reset masivo stock"
        )
        db.session.add(movimiento)

    db.session.commit()

    flash("Stock reseteado correctamente", "success")
    return redirect(url_for("kardex_index"))

@app.route("/kardex/igualar", methods=["POST"])
@login_required
@permission_required("kardex", "ajustar")
def kardex_igualar_stock():

    almacen_id = request.form.get("almacen_id")
    categoria_id = request.form.get("categoria_id")
    nuevo_stock = float(request.form.get("nuevo_stock"))

    productos = Producto.query.filter_by(
        categoria_id=categoria_id,
        activo=True
    ).all()

    for p in productos:

        stock = StockAlmacen.query.filter_by(
            producto_id=p.id,
            almacen_id=almacen_id
        ).first()

        if stock:
            anterior = stock.stock
            stock.stock = nuevo_stock
        else:
            anterior = 0
            stock = StockAlmacen(
                producto_id=p.id,
                almacen_id=almacen_id,
                stock=nuevo_stock
            )
            db.session.add(stock)

        movimiento = KardexMovimiento(
            producto_id=p.id,
            almacen_id=almacen_id,
            tipo_movimiento="AJUSTE_MASIVO",
            cantidad=nuevo_stock,
            stock_anterior=anterior,
            stock_nuevo=nuevo_stock,
            costo_unitario=p.precio_compra or 0,
            usuario_id=current_user.id,
            observacion="Igualación masiva stock"
        )
        db.session.add(movimiento)

    db.session.commit()

    flash("Stock igualado correctamente", "success")
    return redirect(url_for("kardex_index"))

@app.route("/kardex/ajuste", methods=["POST"])
@login_required
@permission_required("kardex", "ajustar")
def kardex_ajuste_individual():

    producto_id = request.form.get("producto_id")
    almacen_id = request.form.get("almacen_id")
    nuevo_stock = float(request.form.get("nuevo_stock"))
    observacion = request.form.get("observacion")

    stock = StockAlmacen.query.filter_by(
        producto_id=producto_id,
        almacen_id=almacen_id
    ).first()

    if not stock:
        stock = StockAlmacen(
            producto_id=producto_id,
            almacen_id=almacen_id,
            stock=0
        )
        db.session.add(stock)

    anterior = stock.stock
    stock.stock = nuevo_stock

    producto = Producto.query.get(producto_id)

    movimiento = KardexMovimiento(
        producto_id=producto_id,
        almacen_id=almacen_id,
        tipo_movimiento="AJUSTE",
        cantidad=nuevo_stock,
        stock_anterior=anterior,
        stock_nuevo=nuevo_stock,
        costo_unitario=producto.precio_compra or 0,
        usuario_id=current_user.id,
        observacion=observacion
    )

    db.session.add(movimiento)
    db.session.commit()

    flash("Ajuste realizado correctamente", "success")
    return redirect(url_for("kardex_index"))

@app.route("/kardex/transferencia", methods=["POST"])
@login_required
@permission_required("kardex", "editar")
def kardex_transferencia():

    producto_id = int(request.form.get("producto_id"))
    origen_id = int(request.form.get("origen_id"))
    destino_id = int(request.form.get("destino_id"))
    cantidad = float(request.form.get("cantidad"))
    observacion = request.form.get("observacion")

    origen = StockAlmacen.query.filter_by(
        producto_id=producto_id,
        almacen_id=origen_id
    ).first()

    if not origen or origen.stock < cantidad:
        flash("Stock insuficiente en almacén origen", "danger")
        return redirect(url_for("kardex_index"))

    destino = StockAlmacen.query.filter_by(
        producto_id=producto_id,
        almacen_id=destino_id
    ).first()

    if not destino:
        destino = StockAlmacen(
            producto_id=producto_id,
            almacen_id=destino_id,
            stock=0
        )
        db.session.add(destino)

    producto = Producto.query.get(producto_id)
    costo = producto.precio_compra or 0

    transferencia = TransferenciaAlmacen(
        almacen_origen_id=origen_id,
        almacen_destino_id=destino_id,
        usuario_id=current_user.id,
        observacion=observacion
    )
    db.session.add(transferencia)
    db.session.flush()

    detalle = TransferenciaDetalle(
        transferencia_id=transferencia.id,
        producto_id=producto_id,
        cantidad=cantidad,
        costo_unitario=costo
    )
    db.session.add(detalle)

    # salida origen
    stock_anterior_origen = origen.stock
    origen.stock -= cantidad

    # entrada destino
    stock_anterior_destino = destino.stock
    destino.stock += cantidad

    mov1 = KardexMovimiento(
        producto_id=producto_id,
        almacen_id=origen_id,
        tipo_movimiento="TRANSFERENCIA_SALIDA",
        cantidad=cantidad,
        stock_anterior=stock_anterior_origen,
        stock_nuevo=origen.stock,
        costo_unitario=costo,
        usuario_id=current_user.id,
        observacion=observacion
    )

    mov2 = KardexMovimiento(
        producto_id=producto_id,
        almacen_id=destino_id,
        tipo_movimiento="TRANSFERENCIA_ENTRADA",
        cantidad=cantidad,
        stock_anterior=stock_anterior_destino,
        stock_nuevo=destino.stock,
        costo_unitario=costo,
        usuario_id=current_user.id,
        observacion=observacion
    )

    db.session.add(mov1)
    db.session.add(mov2)

    db.session.commit()

    flash("Transferencia realizada correctamente", "success")
    return redirect(url_for("kardex_index"))


@app.route("/api/kardex/producto/<codigo>")
@login_required
@permission_required("kardex", "ver")
def buscar_producto_codigo(codigo):

    producto = Producto.query.filter_by(
        codigo_barras=codigo,
        activo=True
    ).first()

    if not producto:
        return jsonify({"ok": False})

    return jsonify({
        "ok": True,
        "id": producto.id,
        "nombre": producto.nombre,
        "precio_compra": producto.precio_compra
    })

@app.route("/kardex/movimientos")
@login_required
@permission_required("kardex", "ver")
def kardex_movimientos():

    movimientos = KardexMovimiento.query.order_by(
        KardexMovimiento.fecha.desc()
    ).all()

    return render_template(
        "kardex/movimientos.html",
        movimientos=movimientos
    )


#==================================================================
# DASHBOARD - Productos - Ventas
#==================================================================
@app.route("/dashboard")
@login_required
def dashboard():

    from sqlalchemy import func

    # =========================
    # 💰 VENTAS TOTALES
    # =========================
    total_ventas = round(db.session.query(func.sum(Venta.total)).scalar() or 0, 2)

    # =========================
    # 📦 PRODUCTOS MÁS VENDIDOS
    # =========================
    top_productos = db.session.query(
        Producto.nombre,
        func.sum(DetalleVenta.cantidad).label("total")
    ).join(DetalleVenta, Producto.id == DetalleVenta.producto_id)\
     .group_by(Producto.nombre)\
     .order_by(func.sum(DetalleVenta.cantidad).desc())\
     .limit(5).all()

    # =========================
    # ⚠️ STOCK BAJO
    # =========================
    bajo_stock = Producto.query.filter(Producto.stock < 5).all()

    # =========================
    # 🌟 PRODUCTO ESTRELLA
    # =========================
    producto_estrella = db.session.query(
        Producto.nombre,
        func.sum(DetalleVenta.subtotal).label("total")
    ).join(DetalleVenta)\
     .group_by(Producto.nombre)\
     .order_by(func.sum(DetalleVenta.subtotal).desc())\
     .first()

    # =========================
    # 👤 MEJOR CLIENTE
    # =========================
    mejor_cliente = db.session.query(
        Cliente.nombre,
        func.sum(Venta.total).label("total")
    ).join(Venta)\
     .group_by(Cliente.nombre)\
     .order_by(func.sum(Venta.total).desc())\
     .first()

    # =========================
    # 📈 VENTAS POR DÍA
    # =========================
    ventas_dia = db.session.query(
        func.date(Venta.fecha),
        func.sum(Venta.total)
    ).group_by(func.date(Venta.fecha)).all()

    ventas_dia = [(fecha.strftime("%d/%m"), total) for fecha, total in ventas_dia]

    return render_template(
        "dashboard.html",
        total_ventas=total_ventas,
        top_productos=top_productos,
        bajo_stock=bajo_stock,
        producto_estrella=producto_estrella,
        mejor_cliente=mejor_cliente,
        ventas_dia=ventas_dia
    )



if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5056, debug=True)