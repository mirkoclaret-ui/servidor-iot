from flask import Flask, request, redirect
import mysql.connector
import os
from datetime import datetime

app = Flask(__name__)

# ==================================
# CONFIGURACIÓN
# ==================================
MAX_AUTOS = 30
estado_estacionamiento = False
autos_actuales = 0

# ==================================
# CONEXIÓN MYSQL
# ==================================
def get_db():
    return mysql.connector.connect(
        host=os.getenv("MYSQLHOST"),
        user=os.getenv("MYSQLUSER"),
        password=os.getenv("MYSQLPASSWORD"),
        database=os.getenv("MYSQLDATABASE"),
        port=int(os.getenv("MYSQLPORT", 3306))
    )

# ==================================
# CREAR TABLA
# ==================================
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historial (
            id INT AUTO_INCREMENT PRIMARY KEY,
            distancia_entrada FLOAT,
            distancia_salida FLOAT,
            total_autos INT,
            fecha_hora VARCHAR(50),
            evento VARCHAR(20)
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ==================================
# GUARDAR EVENTO
# ==================================
def guardar_evento(d1, d2, evento):
    global autos_actuales

    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO historial
        (distancia_entrada, distancia_salida, total_autos, fecha_hora, evento)
        VALUES (%s, %s, %s, %s, %s)
    """, (d1, d2, autos_actuales, fecha, evento))

    conn.commit()
    conn.close()

# ==================================
# PRUEBA MYSQL
# ==================================
@app.route('/test')
def test():
    guardar_evento(50, 0, "Entrada")
    return "ok"

# ==================================
# API SENSOR
# ==================================
@app.route('/sensor', methods=['POST'])
def sensor():
    global autos_actuales, estado_estacionamiento

    if not estado_estacionamiento:
        return {"accion": "cerrado"}

    data = request.json
    tipo = data["tipo"]
    distancia = data["distancia"]

    if tipo == "entrada":
        if autos_actuales >= MAX_AUTOS:
            return {"accion": "lleno"}

        autos_actuales += 1
        guardar_evento(distancia, 0, "Entrada")
        return {"accion": "abrir"}

    elif tipo == "salida":
        if autos_actuales > 0:
            autos_actuales -= 1

        guardar_evento(0, distancia, "Salida")
        return {"accion": "abrir"}

    return {"accion": "error"}

# ==================================
# BOTONES WEB
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

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM historial ORDER BY id DESC")
    datos = cursor.fetchall()
    conn.close()

    estado = "🟢 ABIERTO" if estado_estacionamiento else "🔴 CERRADO"
    lleno = "🚨 LLENO" if autos_actuales >= MAX_AUTOS else "Disponible"

    html = f"""
    <html>
    <head>
    <title>Estacionamiento Falcon</title>
    <meta http-equiv="refresh" content="2">
    </head>
    <body>

    <h1>🅿️ Estacionamiento Falcon</h1>

    <h2>Estado: {estado}</h2>
    <h2>Autos: {autos_actuales}/{MAX_AUTOS}</h2>
    <h2>{lleno}</h2>

    <a href="/abrir">ABRIR</a><br>
    <a href="/cerrar">CERRAR</a><br>
    <a href="/reiniciar">REINICIAR</a><br>

    <h2>Historial</h2>

    <table border="1">
    <tr>
        <th>ID</th>
        <th>Entrada</th>
        <th>Salida</th>
        <th>Total</th>
        <th>Fecha</th>
        <th>Evento</th>
    </tr>
    """

    for fila in datos:
        html += f"""
        <tr>
            <td>{fila[0]}</td>
            <td>{fila[1]}</td>
            <td>{fila[2]}</td>
            <td>{fila[3]}</td>
            <td>{fila[4]}</td>
            <td>{fila[5]}</td>
        </tr>
        """

    html += "</table></body></html>"

    return html

# ==================================
# INICIO
# ==================================
if __name__ == "__main__":
    app.run()
