#!/usr/bin/env python3
"""
Carga de datos sintéticos (Faker) en la base de datos tienda_juegos.

Proyecto SBD 2026-27 · Plataforma de videojuegos online · Hito M0.

Qué hace
--------
Rellena las 11 tablas del esquema (db/01_esquema.sql) con datos inventados,
respetando el orden de las claves foráneas y la coherencia del negocio:

  * Un menor de edad nunca tiene en su biblioteca (ni compra) un juego con
    clasificación de edad superior a su edad en el momento de la compra.
  * Solo las cuentas Creador y Distribuidor tienen empresa asociada.
  * Un juego solo entra en la biblioteca si la compra está "completada".
  * inventario.cantidad = número de compras completadas de ese objeto.
  * Los objetos in-game solo los compra quien ya tiene el juego al que pertenecen.
  * Los mensajes eliminados llevan siempre un moderador (Moderador o Administrador).
  * Todos los datos son SINTÉTICOS. No se usa ningún dato real.

Uso
---
    pip install -r requirements.txt
    python db/seed_datos.py            # carga si las tablas están vacías
    python db/seed_datos.py --reset    # vacía las tablas y vuelve a cargar

Configuración (variables de entorno o fichero .env en la raíz del repo):
    MYSQL_HOST (127.0.0.1)  MYSQL_PORT (3306)  MYSQL_DATABASE  MYSQL_USER  MYSQL_PASSWORD
    SEED_TEST_PASSWORD  contraseña de los usuarios de prueba. Si no existe,
                        se genera una aleatoria y se muestra UNA vez por pantalla.
    SEED                semilla (2026 por defecto): mismos datos en cada ejecución.
"""

import argparse
import os
import random
import secrets
import string
import sys
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import bcrypt
import mysql.connector
from faker import Faker

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:  # python-dotenv es opcional
    pass

# ---------------------------------------------------------------------------
# Parámetros
# ---------------------------------------------------------------------------
SEED = int(os.getenv("SEED", "2026"))
AHORA = datetime(2026, 10, 16, 12, 0, 0)  # fecha fija: datos reproducibles
BCRYPT_ROUNDS = 10

N_EMPRESAS = 15
N_CUENTAS_EXTRA = 113  # además de las 7 cuentas de prueba -> 120 en total
N_JUEGOS = 40
N_COMPRAS_JUEGO = 190
N_COMPRAS_OBJETO = 110
N_MENSAJES = 160

TABLAS_ORDEN_BORRADO = [
    "mensaje", "compra", "inventario", "biblioteca", "metodo_pago",
    "objeto_ingame", "juego", "cuenta", "categoria", "empresa", "rol",
]

ROLES = [
    ("Administrador", "Gestiona la plataforma y a los usuarios"),
    ("Moderador", "Modera mensajes y contenido de la comunidad"),
    ("DevOps", "Opera y mantiene la infraestructura y la base de datos"),
    ("Creador", "Estudio o desarrollador que publica juegos"),
    ("Distribuidor", "Empresa que distribuye juegos en la plataforma"),
    ("Jugador", "Usuario final que compra y juega"),
]

CATEGORIAS = [
    ("Acción", "Juegos de reflejos y combate en tiempo real"),
    ("Aventura", "Exploración, historia y resolución de puzles"),
    ("RPG", "Rol, progresión de personaje y misiones"),
    ("Estrategia", "Gestión de recursos y toma de decisiones tácticas"),
    ("Deportes", "Simuladores y arcades deportivos"),
    ("Carreras", "Conducción y competiciones de velocidad"),
    ("Simulación", "Simulación de oficios, ciudades y vida"),
    ("Puzle", "Rompecabezas y lógica"),
    ("Terror", "Supervivencia y suspense"),
    ("Educativo", "Aprendizaje a través del juego"),
]

PREFIJOS = [
    "Crónicas de", "Leyenda de", "El Reino de", "Sombras de", "La Última",
    "Guardianes de", "Horizonte", "Furia de", "Ecos de", "Rumbo a",
    "El Secreto de", "Batalla por", "Forjadores de", "Mundo de", "Tormenta de",
]
SUJETOS = [
    "Aurora", "Eclipse", "Dragón", "Abismo", "Ceniza", "Nébula", "Cumbre",
    "Tempestad", "Vórtice", "Ónix", "Centinela", "Horizonte", "Cristal",
    "Santuario", "Quimera", "Arcano",
]
TIPOS_OBJETO = ["skin", "arma", "mascota", "potenciador", "moneda", "accesorio", "emote"]
ADJETIVOS_OBJETO = [
    "Dorado", "Espectral", "Ancestral", "Carmesí", "Glacial",
    "Arcano", "Rúnico", "Eterno", "Salvaje", "Cromado",
]
RAREZAS = ["comun", "poco_comun", "raro", "epico", "legendario"]
PESO_RAREZA = [40, 28, 18, 10, 4]
PRECIO_RAREZA = {
    "comun": (0.99, 2.99), "poco_comun": (1.99, 4.99), "raro": (3.99, 9.99),
    "epico": (7.99, 19.99), "legendario": (14.99, 49.99),
}

FRASES_NORMALES = [
    "¿Jugamos una partida esta noche?", "gg, buena partida", "Te paso la clave luego",
    "¿Quién tiene el objeto legendario?", "Acabo de comprar el nuevo juego, es genial",
    "¿Te unes a mi equipo?", "Me han reembolsado la compra, qué rapidez",
    "¿Sabes cuándo sale la próxima actualización?", "Mañana juego un rato por la tarde",
    "Ese jefe final es imposible", "Gracias por la ayuda con la misión",
]
FRASES_OFENSIVAS = [
    "Eres malísimo, desinstala el juego", "Callad ya, qué pesados sois",
    "Qué equipo más inútil, no sabéis jugar", "Deja de molestar, novato",
]


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def edad_en(nacimiento: date, fecha) -> int:
    """Años cumplidos en 'fecha' (equivale a TIMESTAMPDIFF(YEAR, ...) de MySQL)."""
    if isinstance(fecha, datetime):
        fecha = fecha.date()
    return fecha.year - nacimiento.year - ((fecha.month, fecha.day) < (nacimiento.month, nacimiento.day))


def fecha_aleatoria(desde: datetime, hasta: datetime) -> datetime:
    if hasta <= desde:
        return desde
    segundos = int((hasta - desde).total_seconds())
    return desde + timedelta(seconds=random.randint(0, segundos))


def importe(valor) -> Decimal:
    return Decimal(str(round(float(valor), 2)))


def clave_activacion(usadas: set) -> str:
    alfabeto = string.ascii_uppercase + string.digits
    while True:
        clave = "-".join("".join(random.choices(alfabeto, k=5)) for _ in range(4))
        if clave not in usadas:
            usadas.add(clave)
            return clave


def conectar():
    try:
        return mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "127.0.0.1"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            database=os.environ["MYSQL_DATABASE"],
            user=os.environ["MYSQL_USER"],
            password=os.environ["MYSQL_PASSWORD"],
            charset="utf8mb4",
        )
    except KeyError as faltante:
        sys.exit(f"Falta la variable de entorno {faltante}. Revisa tu fichero .env")
    except mysql.connector.Error as error:
        sys.exit(f"No se pudo conectar a MySQL: {error.msg}")


def hash_password(clave: str) -> str:
    return bcrypt.hashpw(clave.encode(), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode()


# ---------------------------------------------------------------------------
# Generación de datos (todo en memoria; después se inserta en bloque)
# ---------------------------------------------------------------------------
def generar_roles():
    return [(i, nombre, desc) for i, (nombre, desc) in enumerate(ROLES, start=1)]


def generar_categorias():
    return [(i, nombre, desc) for i, (nombre, desc) in enumerate(CATEGORIAS, start=1)]


def generar_empresas(fake):
    empresas = []
    for i in range(1, N_EMPRESAS + 1):
        tipo = ("desarrollador", "distribuidor", "ambos")[i % 3]
        empresas.append((
            i, fake.company()[:100], tipo, fake.country()[:60], fake.company_email()[:150],
        ))
    return empresas


def generar_cuentas(fake, roles, empresas, password_prueba):
    """Devuelve la lista de cuentas (diccionarios) con 7 cuentas de prueba fijas."""
    id_rol = {nombre: i for i, nombre, _ in roles}
    emp_desarrollo = [e[0] for e in empresas if e[2] in ("desarrollador", "ambos")]
    emp_distribucion = [e[0] for e in empresas if e[2] in ("distribuidor", "ambos")]

    cuentas = []
    nicks, emails = set(), set()

    def nueva(nick, rol, nacimiento, id_empresa=None, email=None):
        nick = nick.lower()[:50]
        while nick in nicks:
            nick = (nick[:44] + str(random.randint(100, 99999)))[:50]
        nicks.add(nick)
        correo = (email or fake.email()).lower()[:150]
        while correo in emails:
            correo = f"{random.randint(1, 99999)}{correo}"[:150]
        emails.add(correo)
        registro = fecha_aleatoria(datetime(2022, 1, 1), datetime(2026, 9, 30))
        minimo_registro = datetime.combine(nacimiento, datetime.min.time()) + timedelta(days=365 * 10)
        registro = max(registro, minimo_registro)
        cuentas.append({
            "id": len(cuentas) + 1,
            "nick": nick,
            "email": correo,
            "telefono": fake.phone_number()[:20],
            "password_hash": hash_password(password_prueba),
            "nombre": fake.first_name()[:80],
            "apellidos": f"{fake.last_name()} {fake.last_name()}"[:120],
            "nacimiento": nacimiento,
            "pais": fake.country()[:60],
            "ip": fake.ipv4(),
            "registro": min(registro, AHORA - timedelta(days=1)),
            "estado": random.choices(["activa", "suspendida", "baja"], [92, 5, 3])[0],
            "id_rol": id_rol[rol],
            "rol": rol,
            "id_empresa": id_empresa,
        })

    def nacimiento_adulto(minima=21, maxima=58):
        return AHORA.date() - timedelta(days=random.randint(minima * 365, maxima * 365))

    def nacimiento_menor():
        return AHORA.date() - timedelta(days=random.randint(10 * 365, 17 * 365 + 300))

    # Cuentas de prueba fijas (una por rol + un menor)
    nueva("admin_test", "Administrador", nacimiento_adulto(), email="admin_test@ejemplo.test")
    nueva("moderador_test", "Moderador", nacimiento_adulto(), email="moderador_test@ejemplo.test")
    nueva("devops_test", "DevOps", nacimiento_adulto(), email="devops_test@ejemplo.test")
    nueva("creador_test", "Creador", nacimiento_adulto(), random.choice(emp_desarrollo), "creador_test@ejemplo.test")
    nueva("distribuidor_test", "Distribuidor", nacimiento_adulto(), random.choice(emp_distribucion), "distribuidor_test@ejemplo.test")
    nueva("jugador_test", "Jugador", nacimiento_adulto(18, 40), email="jugador_test@ejemplo.test")
    nueva("menor_test", "Jugador", AHORA.date() - timedelta(days=14 * 365 + 100), email="menor_test@ejemplo.test")
    for c in cuentas:  # las cuentas de prueba siempre activas
        c["estado"] = "activa"

    # Resto de cuentas: personal y jugadores (aprox. 20 % menores)
    reparto = (["Moderador"] * 2 + ["DevOps"] * 1 + ["Administrador"] * 1
               + ["Creador"] * 6 + ["Distribuidor"] * 4)
    for rol in reparto:
        id_emp = None
        if rol == "Creador":
            id_emp = random.choice(emp_desarrollo)
        elif rol == "Distribuidor":
            id_emp = random.choice(emp_distribucion)
        nueva(fake.user_name(), rol, nacimiento_adulto(), id_emp)
    while len(cuentas) < 7 + N_CUENTAS_EXTRA:
        menor = random.random() < 0.20
        nueva(fake.user_name(), "Jugador", nacimiento_menor() if menor else nacimiento_adulto(18, 60))
    return cuentas


def generar_juegos(fake, empresas, categorias):
    desarrolladoras = [e[0] for e in empresas if e[2] in ("desarrollador", "ambos")]
    distribuidoras = [e[0] for e in empresas if e[2] in ("distribuidor", "ambos")]
    combinaciones = [f"{p} {s}" for p in PREFIJOS for s in SUJETOS]
    random.shuffle(combinaciones)
    juegos = []
    for i in range(1, N_JUEGOS + 1):
        lanzamiento = date(2015, 1, 1) + timedelta(days=random.randint(0, 11 * 365 + 150))
        juegos.append({
            "id": i,
            "titulo": combinaciones[i - 1],
            "descripcion": fake.paragraph(nb_sentences=3),
            "precio": importe(random.choices(
                [0, 4.99, 9.99, 14.99, 19.99, 29.99, 39.99, 49.99, 59.99],
                [8, 10, 18, 16, 16, 14, 8, 6, 4])[0]),
            "edad": random.choices([3, 7, 12, 16, 18], [10, 20, 25, 20, 25])[0],
            "lanzamiento": lanzamiento,
            "id_categoria": random.choice(categorias)[0],
            "id_desarrollador": random.choice(desarrolladoras),
            "id_distribuidor": random.choice(distribuidoras),
        })
    return juegos


def generar_objetos(juegos):
    objetos = []
    for juego in juegos:
        nombres = set()
        for _ in range(random.randint(1, 4)):
            tipo = random.choice(TIPOS_OBJETO)
            nombre = f"{tipo.capitalize()} {random.choice(ADJETIVOS_OBJETO)}"
            if nombre in nombres:
                continue
            nombres.add(nombre)
            rareza = random.choices(RAREZAS, PESO_RAREZA)[0]
            minimo, maximo = PRECIO_RAREZA[rareza]
            objetos.append({
                "id": len(objetos) + 1,
                "id_juego": juego["id"],
                "nombre": nombre,
                "tipo": tipo,
                "rareza": rareza,
                "precio": importe(random.uniform(minimo, maximo)),
            })
    return objetos


def generar_metodos_pago(fake, cuentas):
    metodos = []
    for cuenta in cuentas:
        if random.random() > 0.78:
            continue  # cuentas sin método de pago (no han comprado nunca)
        for _ in range(random.choice([1, 1, 1, 2])):
            tipo = random.choices(["tarjeta", "IBAN", "otro"], [70, 25, 5])[0]
            menor_ahora = edad_en(cuenta["nacimiento"], AHORA) < 18
            titular = fake.name() if menor_ahora else f"{cuenta['nombre']} {cuenta['apellidos']}"
            if tipo == "tarjeta":
                numero = fake.credit_card_number()
                caducidad = f"{random.randint(1, 12):02d}/{random.randint(27, 31)}"
            elif tipo == "IBAN":
                numero = fake.iban()
                caducidad = "N/A"
            else:
                numero = "PP-" + fake.bothify("########")
                caducidad = "N/A"
            metodos.append({
                "id": len(metodos) + 1,
                "id_cuenta": cuenta["id"],
                "tipo": tipo,
                "titular": titular[:150],
                "numero": numero[:255],
                "caducidad": caducidad,
                "direccion": fake.address().replace("\n", ", ")[:255],
                "alta": fecha_aleatoria(cuenta["registro"], AHORA - timedelta(days=1)),
            })
    return metodos


def estado_compra():
    return random.choices(["completada", "reembolsada", "fallida", "pendiente"], [85, 5, 5, 5])[0]


def generar_compras(fake, cuentas, metodos, juegos, objetos):
    """Compras de juegos (con su biblioteca) y de objetos (con su inventario)."""
    cuenta_por_id = {c["id"]: c for c in cuentas}
    juego_por_id = {j["id"]: j for j in juegos}
    objetos_de_juego = {}
    for o in objetos:
        objetos_de_juego.setdefault(o["id_juego"], []).append(o)
    metodos_de = {}
    for m in metodos:
        metodos_de.setdefault(m["id_cuenta"], []).append(m)
    compradores = [c for c in cuentas if c["id"] in metodos_de]

    compras, biblioteca, claves = [], {}, set()
    pares_usados = set()
    inventario = {}

    def nueva_compra(cuenta, metodo, fecha, estado, precio, juego=None, objeto=None):
        compras.append({
            "id": len(compras) + 1,
            "id_cuenta": cuenta["id"],
            "id_metodo": metodo["id"],
            "id_juego": juego["id"] if juego else None,
            "id_objeto": objeto["id"] if objeto else None,
            "importe": precio,
            "fecha": fecha,
            "estado": estado,
            "factura": "",
            "ip": fake.ipv4(),
        })

    # --- compras de juegos --------------------------------------------------
    intentos = 0
    hechas = 0
    while hechas < N_COMPRAS_JUEGO and intentos < N_COMPRAS_JUEGO * 40:
        intentos += 1
        cuenta = random.choice(compradores)
        juego = random.choice(juegos)
        if (cuenta["id"], juego["id"]) in pares_usados:
            continue
        inicio = max(cuenta["registro"], datetime.combine(juego["lanzamiento"], datetime.min.time()))
        if inicio >= AHORA - timedelta(days=1):
            continue
        fecha = fecha_aleatoria(inicio, AHORA - timedelta(days=1))
        if edad_en(cuenta["nacimiento"], fecha) < juego["edad"]:
            continue  # regla de menores: no puede comprar un juego de más edad
        metodo = random.choice([m for m in metodos_de[cuenta["id"]] if m["alta"] <= fecha] or [None]) \
            if any(m["alta"] <= fecha for m in metodos_de[cuenta["id"]]) else None
        if metodo is None:
            continue
        pares_usados.add((cuenta["id"], juego["id"]))
        estado = estado_compra()
        nueva_compra(cuenta, metodo, fecha, estado, juego["precio"], juego=juego)
        if estado == "completada":
            biblioteca[(cuenta["id"], juego["id"])] = {
                "id_cuenta": cuenta["id"],
                "id_juego": juego["id"],
                "adquisicion": fecha,
                "clave": clave_activacion(claves),
                "horas": Decimal(str(round(random.uniform(0, min(500, (AHORA - fecha).days * 3)), 1))),
            }
        hechas += 1

    # --- compras de objetos (solo de juegos que la cuenta ya tiene) ----------
    propietarios = {}
    for (id_cuenta, id_juego), fila in biblioteca.items():
        propietarios.setdefault(id_cuenta, []).append(fila)
    intentos = 0
    hechas = 0
    while hechas < N_COMPRAS_OBJETO and intentos < N_COMPRAS_OBJETO * 40:
        intentos += 1
        id_cuenta = random.choice(list(propietarios))
        cuenta = cuenta_por_id[id_cuenta]
        fila = random.choice(propietarios[id_cuenta])
        candidatos = objetos_de_juego.get(fila["id_juego"])
        if not candidatos:
            continue
        objeto = random.choice(candidatos)
        fecha = fecha_aleatoria(fila["adquisicion"], AHORA - timedelta(hours=1))
        validos = [m for m in metodos_de[id_cuenta] if m["alta"] <= fecha]
        if not validos:
            continue
        estado = estado_compra()
        nueva_compra(cuenta, random.choice(validos), fecha, estado, objeto["precio"], objeto=objeto)
        if estado == "completada":
            clave = (id_cuenta, objeto["id"])
            if clave in inventario:
                inventario[clave]["cantidad"] += 1
                inventario[clave]["obtencion"] = min(inventario[clave]["obtencion"], fecha)
            else:
                inventario[clave] = {"id_cuenta": id_cuenta, "id_objeto": objeto["id"],
                                     "cantidad": 1, "obtencion": fecha}
        hechas += 1

    # Facturas numeradas por orden cronológico (únicas) e ids definitivos
    compras.sort(key=lambda c: c["fecha"])
    for i, c in enumerate(compras, start=1):
        c["id"] = i
        c["factura"] = f"F{c['fecha'].year}-{i:06d}"
    return compras, list(biblioteca.values()), list(inventario.values())


def generar_mensajes(fake, cuentas):
    moderadores = [c["id"] for c in cuentas if c["rol"] in ("Moderador", "Administrador")]
    mensajes = []
    for i in range(1, N_MENSAJES + 1):
        emisor, receptor = random.sample(cuentas, 2)
        inicio = max(emisor["registro"], receptor["registro"])
        fecha = fecha_aleatoria(inicio, AHORA - timedelta(hours=1))
        ofensivo = random.random() < 0.08
        if ofensivo:
            texto = random.choice(FRASES_OFENSIVAS)
        elif random.random() < 0.6:
            texto = random.choice(FRASES_NORMALES)
        else:
            texto = fake.sentence(nb_words=random.randint(4, 16))
        eliminado = ofensivo and random.random() < 0.75
        mensajes.append({
            "id": i,
            "emisor": emisor["id"],
            "receptor": receptor["id"],
            "texto": texto,
            "fecha": fecha,
            "estado": "eliminado" if eliminado else "normal",
            "moderador": random.choice(moderadores) if eliminado else None,
        })
    return mensajes


# ---------------------------------------------------------------------------
# Inserción
# ---------------------------------------------------------------------------
def insertar(cur, sql, filas):
    if filas:
        cur.executemany(sql, filas)


def cargar(conn, datos):
    cur = conn.cursor()
    insertar(cur, "INSERT INTO rol (id_rol, nombre, descripcion) VALUES (%s,%s,%s)", datos["roles"])
    insertar(cur, "INSERT INTO empresa (id_empresa, nombre, tipo, pais, email_contacto) VALUES (%s,%s,%s,%s,%s)",
             datos["empresas"])
    insertar(cur, "INSERT INTO categoria (id_categoria, nombre, descripcion) VALUES (%s,%s,%s)", datos["categorias"])
    insertar(cur, """INSERT INTO cuenta (id_cuenta, nick, email, telefono, password_hash, nombre, apellidos,
                     fecha_nacimiento, pais, ip_registro, fecha_registro, estado, id_rol, id_empresa)
                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
             [(c["id"], c["nick"], c["email"], c["telefono"], c["password_hash"], c["nombre"], c["apellidos"],
               c["nacimiento"], c["pais"], c["ip"], c["registro"], c["estado"], c["id_rol"], c["id_empresa"])
              for c in datos["cuentas"]])
    insertar(cur, """INSERT INTO juego (id_juego, titulo, descripcion, precio, clasificacion_edad,
                     fecha_lanzamiento, id_categoria, id_desarrollador, id_distribuidor)
                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
             [(j["id"], j["titulo"], j["descripcion"], j["precio"], j["edad"], j["lanzamiento"],
               j["id_categoria"], j["id_desarrollador"], j["id_distribuidor"]) for j in datos["juegos"]])
    insertar(cur, """INSERT INTO objeto_ingame (id_objeto, id_juego, nombre, tipo, rareza, precio)
                     VALUES (%s,%s,%s,%s,%s,%s)""",
             [(o["id"], o["id_juego"], o["nombre"], o["tipo"], o["rareza"], o["precio"]) for o in datos["objetos"]])
    insertar(cur, """INSERT INTO metodo_pago (id_metodo, id_cuenta, tipo, titular, numero, caducidad,
                     direccion_facturacion, fecha_alta) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
             [(m["id"], m["id_cuenta"], m["tipo"], m["titular"], m["numero"], m["caducidad"], m["direccion"],
               m["alta"]) for m in datos["metodos"]])
    insertar(cur, """INSERT INTO compra (id_compra, id_cuenta, id_metodo, id_juego, id_objeto, importe, fecha,
                     estado, numero_factura, ip_origen) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
             [(c["id"], c["id_cuenta"], c["id_metodo"], c["id_juego"], c["id_objeto"], c["importe"], c["fecha"],
               c["estado"], c["factura"], c["ip"]) for c in datos["compras"]])
    insertar(cur, """INSERT INTO biblioteca (id_cuenta, id_juego, fecha_adquisicion, clave_activacion,
                     horas_jugadas) VALUES (%s,%s,%s,%s,%s)""",
             [(b["id_cuenta"], b["id_juego"], b["adquisicion"], b["clave"], b["horas"]) for b in datos["biblioteca"]])
    insertar(cur, """INSERT INTO inventario (id_cuenta, id_objeto, cantidad, fecha_obtencion)
                     VALUES (%s,%s,%s,%s)""",
             [(i["id_cuenta"], i["id_objeto"], i["cantidad"], i["obtencion"]) for i in datos["inventario"]])
    insertar(cur, """INSERT INTO mensaje (id_mensaje, id_emisor, id_receptor, texto, fecha, estado, id_moderador)
                     VALUES (%s,%s,%s,%s,%s,%s,%s)""",
             [(m["id"], m["emisor"], m["receptor"], m["texto"], m["fecha"], m["estado"], m["moderador"])
              for m in datos["mensajes"]])
    cur.close()


def vaciar(conn):
    cur = conn.cursor()
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    for tabla in TABLAS_ORDEN_BORRADO:
        cur.execute(f"TRUNCATE TABLE {tabla}")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    cur.close()


def resumen_y_comprobaciones(conn):
    cur = conn.cursor()
    print("\nFilas por tabla:")
    total = 0
    for tabla in reversed(TABLAS_ORDEN_BORRADO):
        cur.execute(f"SELECT COUNT(*) FROM {tabla}")
        n = cur.fetchone()[0]
        total += n
        print(f"  {tabla:<14}{n:>6}")
    print(f"  {'TOTAL':<14}{total:>6}")

    comprobaciones = {
        "Menores con juegos por encima de su edad en la biblioteca": """
            SELECT COUNT(*) FROM biblioteca b JOIN cuenta c USING (id_cuenta) JOIN juego j USING (id_juego)
            WHERE TIMESTAMPDIFF(YEAR, c.fecha_nacimiento, b.fecha_adquisicion) < j.clasificacion_edad""",
        "Compras que no cumplen 'un solo producto'": """
            SELECT COUNT(*) FROM compra WHERE (id_juego IS NULL) = (id_objeto IS NULL)""",
        "Inventario con cantidad distinta de las compras completadas": """
            SELECT COUNT(*) FROM inventario i WHERE i.cantidad <> (
              SELECT COUNT(*) FROM compra c WHERE c.id_cuenta = i.id_cuenta
              AND c.id_objeto = i.id_objeto AND c.estado = 'completada')""",
        "Mensajes eliminados sin moderador": """
            SELECT COUNT(*) FROM mensaje WHERE estado = 'eliminado' AND id_moderador IS NULL""",
        "Cuentas con empresa que no son Creador/Distribuidor": """
            SELECT COUNT(*) FROM cuenta c JOIN rol r USING (id_rol)
            WHERE c.id_empresa IS NOT NULL AND r.nombre NOT IN ('Creador','Distribuidor')""",
    }
    print("\nComprobaciones de coherencia (todas deben ser 0):")
    for texto, sql in comprobaciones.items():
        cur.execute(sql)
        print(f"  {cur.fetchone()[0]:>3}  {texto}")
    cur.execute("SELECT COUNT(*) FROM cuenta WHERE TIMESTAMPDIFF(YEAR, fecha_nacimiento, %s) < 18", (AHORA,))
    print(f"\nCuentas de menores de edad: {cur.fetchone()[0]}")
    cur.close()
    return total


def main():
    parser = argparse.ArgumentParser(description="Carga datos sintéticos en tienda_juegos")
    parser.add_argument("--reset", action="store_true", help="vacía las tablas antes de cargar")
    args = parser.parse_args()

    random.seed(SEED)
    Faker.seed(SEED)
    fake = Faker("es_ES")

    password_prueba = os.getenv("SEED_TEST_PASSWORD")
    mostrar_password = False
    if not password_prueba:
        password_prueba = secrets.token_urlsafe(12)
        mostrar_password = True

    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM cuenta")
        if cur.fetchone()[0] > 0 and not args.reset:
            sys.exit("La base de datos ya tiene datos. Usa --reset para vaciarla y volver a cargar.")
        cur.close()

        print("Generando datos sintéticos (el hash bcrypt de las contraseñas tarda unos segundos)...")
        roles = generar_roles()
        categorias = generar_categorias()
        empresas = generar_empresas(fake)
        cuentas = generar_cuentas(fake, roles, empresas, password_prueba)
        juegos = generar_juegos(fake, empresas, categorias)
        objetos = generar_objetos(juegos)
        metodos = generar_metodos_pago(fake, cuentas)
        compras, biblioteca, inventario = generar_compras(fake, cuentas, metodos, juegos, objetos)
        mensajes = generar_mensajes(fake, cuentas)
        datos = {
            "roles": roles, "categorias": categorias, "empresas": empresas, "cuentas": cuentas,
            "juegos": juegos, "objetos": objetos, "metodos": metodos, "compras": compras,
            "biblioteca": biblioteca, "inventario": inventario, "mensajes": mensajes,
        }

        if args.reset:
            vaciar(conn)
        cargar(conn, datos)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pass

    total = resumen_y_comprobaciones(conn)
    conn.close()
    if total < 500:
        sys.exit(f"Atención: solo hay {total} filas y el enunciado exige al menos 500.")
    print("\nUsuarios de prueba: admin_test, moderador_test, devops_test, creador_test,"
          " distribuidor_test, jugador_test, menor_test")
    if mostrar_password:
        print(f"Contraseña de los usuarios de prueba (solo se muestra ahora): {password_prueba}")
    else:
        print("Contraseña de los usuarios de prueba: la de SEED_TEST_PASSWORD en tu .env")


if __name__ == "__main__":
    main()
