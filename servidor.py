
from flask import Flask, request, redirect
import sqlite3
from datetime import datetime

app = Flask(__name__)

# ==================================
# CONFIGURACIÓN
# ==================================
MAX_AUTOS = 30
estado_estacionamiento = False
autos_actuales = 0

# ==================================
# BASE DE DATOS
# ==================================
def init_db():
    conn = sqlite3.connect("datos.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            distancia_entrada REAL,
            distancia_salida REAL,
            total_autos INTEGER,
            fecha_hora TEXT,
            evento TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ==================================
# GUARDAR EVENTOS
# ==================================
def guardar_evento(d1, d2, evento):
    global autos_actuales

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = sqlite3.connect("datos.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO historial
        (distancia_entrada, distancia_salida, total_autos, fecha_hora, evento)
        VALUES (?, ?, ?, ?, ?)
    """, (d1, d2, autos_actuales, fecha, evento))

    conn.commit()
    conn.close()

# ==================================
# API DEL ESP32
# ==================================
@app.route('/sensor', methods=['POST'])
def sensor():
    global autos_actuales, estado_estacionamiento

    if not estado_estacionamiento:
        return {"accion": "cerrado"}

    data = request.json
    tipo = data["tipo"]
    distancia = data["distancia"]

    # ENTRADA
    if tipo == "entrada":

        if autos_actuales >= MAX_AUTOS:
            return {"accion": "lleno"}

        autos_actuales += 1
        guardar_evento(distancia, 0, "Entrada")

        return {"accion": "abrir"}

    # SALIDA
    elif tipo == "salida":

        if autos_actuales > 0:
            autos_actuales -= 1

        guardar_evento(0, distancia, "Salida")

        return {"accion": "abrir"}

    return {"accion": "error"}

# ==================================
# BOTONES
# ==================================
@app.route('/abrir')
def abrir():
    global estado_estacionamiento
    estado_estacionamiento = True
    return redirect('/')

@app.route('/cerrar')
def cerrar():
    global estado_estacionamiento
    estado_estacionamiento = False
    return redirect('/')

@app.route('/reiniciar')
def reiniciar():
    global autos_actuales
    autos_actuales = 0
    return redirect('/')

# ==================================
# PÁGINA PRINCIPAL
# ==================================
@app.route('/')
def inicio():
    global autos_actuales, estado_estacionamiento

    filtro = request.args.get("filtro")
    valor = request.args.get("valor")

    conn = sqlite3.connect("datos.db")
    cursor = conn.cursor()

    # BÚSQUEDAS
    if filtro and valor:

        if filtro == "anio":
            cursor.execute("""
                SELECT * FROM historial
                WHERE strftime('%Y', fecha_hora)=?
                ORDER BY id DESC
            """, (valor,))

        elif filtro == "mes":
            cursor.execute("""
                SELECT * FROM historial
                WHERE strftime('%m', fecha_hora)=?
                ORDER BY id DESC
            """, (valor.zfill(2),))

        elif filtro == "dia":
            cursor.execute("""
                SELECT * FROM historial
                WHERE strftime('%d', fecha_hora)=?
                ORDER BY id DESC
            """, (valor.zfill(2),))

        elif filtro == "hora":
            cursor.execute("""
                SELECT * FROM historial
                WHERE strftime('%H', fecha_hora)=?
                ORDER BY id DESC
            """, (valor.zfill(2),))

        else:
            query = f"SELECT * FROM historial WHERE {filtro} LIKE ? ORDER BY id DESC"
            cursor.execute(query, ('%' + valor + '%',))

    else:
        cursor.execute("SELECT * FROM historial ORDER BY id DESC")

    datos = cursor.fetchall()
    conn.close()

    # TEXTOS
    estado = "🟢 ABIERTO" if estado_estacionamiento else "🔴 CERRADO"
    lleno = "🚨 LLENO" if autos_actuales >= MAX_AUTOS else "Disponible"

    # ==================================
    # HTML
    # ==================================
    html = f"""
    <html>
    <head>
    <title>Estacionamiento Falcon</title>
    <meta http-equiv="refresh" content="2">

    <style>

    body {{
        font-family: Arial;
        background:#f4f6f8;
        padding:25px;
    }}

    h1 {{
        color:#222;
    }}

    .panel {{
        background:white;
        padding:20px;
        border-radius:15px;
        box-shadow:0 0 10px rgba(0,0,0,0.1);
        margin-bottom:20px;
    }}

    .abierto {{
        color:green;
        font-weight:bold;
    }}

    .cerrado {{
        color:red;
        font-weight:bold;
    }}

    .disponible {{
        color:green;
        font-weight:bold;
    }}

    .lleno {{
        color:red;
        font-weight:bold;
    }}

    button {{
        padding:10px 18px;
        border:none;
        border-radius:10px;
        cursor:pointer;
        font-weight:bold;
        margin:5px;
    }}

    .btn1 {{background:#28a745; color:white;}}
    .btn2 {{background:#dc3545; color:white;}}
    .btn3 {{background:#007bff; color:white;}}

    table {{
        width:100%;
        border-collapse:collapse;
        background:white;
        border-radius:10px;
        overflow:hidden;
    }}

    th {{
        background:#222;
        color:white;
        padding:12px;
    }}

    td {{
        padding:10px;
        text-align:center;
    }}

    tr:nth-child(even) {{
        background:#f2f2f2;
    }}

    .entrada {{
        color:green;
        font-weight:bold;
    }}

    .salida {{
        color:red;
        font-weight:bold;
    }}

    input, select {{
        padding:8px;
        border-radius:8px;
        border:1px solid #ccc;
    }}

    </style>
    </head>

    <body>

    <div class="panel">

    <h1>🅿️ Estacionamiento Falcon</h1>

    <h2>Estado:
    <span class="{'abierto' if estado_estacionamiento else 'cerrado'}">
    {estado}
    </span>
    </h2>

    <h2>Autos actuales: {autos_actuales}/{MAX_AUTOS}</h2>

    <h2>
    <span class="{'lleno' if autos_actuales >= MAX_AUTOS else 'disponible'}">
    {lleno}
    </span>
    </h2>

    <a href="/abrir"><button class="btn1">ABRIR</button></a>
    <a href="/cerrar"><button class="btn2">CERRAR</button></a>
    <a href="/reiniciar"><button class="btn3">REINICIAR</button></a>

    </div>

    <div class="panel">

    <h2>🔍 Buscador</h2>

    <form method="GET">

    <select name="filtro">
        <option value="evento">Evento</option>
        <option value="fecha_hora">Fecha completa</option>
        <option value="anio">Año</option>
        <option value="mes">Mes</option>
        <option value="dia">Día</option>
        <option value="hora">Hora</option>
        <option value="total_autos">Autos</option>
    </select>

    <input type="text" name="valor" placeholder="Buscar">

    <button class="btn3" type="submit">Buscar</button>

    </form>

    </div>

    <div class="panel">

    <h2>📋 Historial</h2>

    <table>
    <tr>
        <th>ID</th>
        <th>Entrada</th>
        <th>Salida</th>
        <th>Total</th>
        <th>Fecha Hora</th>
        <th>Evento</th>
    </tr>
    """

    # FILAS
    for fila in datos:

        if fila[5] == "Entrada":
            evento = "<span class='entrada'>🟢 Entrada</span>"
        else:
            evento = "<span class='salida'>🔴 Salida</span>"

        html += f"""
        <tr>
            <td>{fila[0]}</td>
            <td>{fila[1]}</td>
            <td>{fila[2]}</td>
            <td>{fila[3]}</td>
            <td>{fila[4]}</td>
            <td>{evento}</td>
        </tr>
        """

    html += """
    </table>

    </div>

    </body>
    </html>
    """

    return html

# ==================================
# INICIAR SERVIDOR
# ==================================
if __name__ == "__main__":
    app.run(debug=True)
