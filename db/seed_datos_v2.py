#!/usr/bin/env python3
"""
Carga de datos sinteticos (Faker) en la base de datos tienda_juegos.
Proyecto SBD 2026-27 - Plataforma de videojuegos online - Hito M0.

Rellena las 11 tablas de db/01_esquema.sql respetando el orden de las claves
foraneas. Casi todo lo inventa Faker: nombres, empresas, correos, telefonos,
IPs, tarjetas, IBAN, direcciones, fechas y textos. Solo son fijos el catalogo
de roles, los generos de juego, los tipos de objeto y unas frases para probar
la moderacion de mensajes.

Reglas de coherencia:
  - Un menor no compra ni tiene en su biblioteca un juego de mas edad que la suya.
  - Solo las cuentas Creador y Distribuidor tienen empresa.
  - Un juego solo entra en la biblioteca si la compra esta completada.
  - inventario.cantidad es el numero de compras completadas de ese objeto.
  - Los objetos solo los compra quien ya tiene el juego.
  - Un mensaje eliminado siempre lleva moderador (Moderador o Administrador).

Uso:
    python db/seed_datos.py            # carga si la base de datos esta vacia
    python db/seed_datos.py --reset    # vacia las tablas y vuelve a cargar

Variables (entorno o fichero .env en la raiz del repositorio):
    MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD
    SEED_TEST_PASSWORD  clave de las cuentas de prueba (si falta, se genera una)
    SEED                semilla de Faker (2026 por defecto)
"""

import argparse
import os
import secrets
import string
import sys
import unicodedata
from collections import OrderedDict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

import bcrypt
import mysql.connector
from faker import Faker
from faker.providers import DynamicProvider

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:  # python-dotenv es opcional
    pass

# ---------------------------------------------------------------------------
# Parametros
# ---------------------------------------------------------------------------
SEED = int(os.getenv("SEED", "2026"))
AHORA = datetime(2026, 10, 16, 12, 0, 0)  # fecha fija para que los datos se repitan
LIMITE = AHORA - timedelta(days=1)         # nada se genera despues de esta fecha
SOLO_ASCII = True                          # True: sin tildes ni simbolos raros en los textos
ROUNDS_BCRYPT = 10

N_EMPRESAS = 15
N_CUENTAS = 120          # incluye las 7 cuentas de prueba
N_JUEGOS = 40
N_COMPRAS_JUEGO = 190
N_COMPRAS_OBJETO = 110
N_MENSAJES = 160

# Orden de borrado: primero las tablas que dependen de otras
BORRADO = ["mensaje", "compra", "inventario", "biblioteca", "metodo_pago",
           "objeto_ingame", "juego", "cuenta", "categoria", "empresa", "rol"]

ROLES = [
    ("Administrador", "Gestiona la plataforma y a los usuarios"),
    ("Moderador", "Modera mensajes y contenido de la comunidad"),
    ("DevOps", "Opera y mantiene la infraestructura y la base de datos"),
    ("Creador", "Estudio o desarrollador que publica juegos"),
    ("Distribuidor", "Empresa que distribuye juegos en la plataforma"),
    ("Jugador", "Usuario final que compra y juega"),
]
GENEROS = ["Accion", "Aventura", "RPG", "Estrategia", "Deportes",
           "Carreras", "Simulacion", "Puzle", "Terror", "Educativo"]

# ---------------------------------------------------------------------------
# Faker en espanol, con la semilla fijada y dos proveedores propios
# ---------------------------------------------------------------------------
Faker.seed(SEED)
fake = Faker("es_ES")
fake.add_provider(DynamicProvider(
    provider_name="tipo_objeto",
    elements=["skin", "arma", "mascota", "potenciador", "moneda", "accesorio", "emote"]))
fake.add_provider(DynamicProvider(
    provider_name="insulto",
    elements=["Eres malisimo, desinstala el juego", "Callad ya, que pesados sois",
              "Que equipo mas inutil, no sabeis jugar", "Deja de molestar, novato"]))


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def corto(texto, largo):
    """Texto de una linea, sin tildes si SOLO_ASCII, recortado al VARCHAR de la columna."""
    texto = str(texto).replace("\n", ", ")
    if SOLO_ASCII:
        texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return texto[:largo].strip()


def elegir(pesos):
    """Elige un valor segun probabilidades: elegir([("a", 0.9), ("b", 0.1)])."""
    return fake.random_element(OrderedDict(pesos))


def entre(desde, hasta):
    """Fecha y hora aleatoria entre dos datetime."""
    if hasta <= desde:
        return desde
    return fake.date_time_between_dates(desde, hasta).replace(microsecond=0)


def nacimiento(anios_min, anios_max):
    """Fecha de nacimiento para tener entre anios_min y anios_max anios en AHORA."""
    desde = AHORA.date() - timedelta(days=int(anios_max * 365.25))
    hasta = AHORA.date() - timedelta(days=int(anios_min * 365.25))
    return fake.date_between_dates(desde, hasta)


def edad_en(nac, fecha):
    """Anios cumplidos en 'fecha' (igual que TIMESTAMPDIFF(YEAR, ...) de MySQL)."""
    if isinstance(fecha, datetime):
        fecha = fecha.date()
    return fecha.year - nac.year - ((fecha.month, fecha.day) < (nac.month, nac.day))


def dinero(minimo, maximo):
    return fake.pydecimal(left_digits=3, right_digits=2,
                          min_value=minimo, max_value=maximo).quantize(Decimal("0.01"))


def unico(generador, usados, largo):
    """Llama al generador hasta obtener un valor (en minusculas) que no este en 'usados'."""
    while True:
        valor = corto(generador(), largo).lower()
        if valor and valor not in usados:
            usados.add(valor)
            return valor


def hash_clave(clave):
    return bcrypt.hashpw(clave.encode(), bcrypt.gensalt(rounds=ROUNDS_BCRYPT)).decode()


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
    except KeyError as falta:
        sys.exit(f"Falta la variable de entorno {falta}. Revisa tu fichero .env")
    except mysql.connector.Error as error:
        sys.exit(f"No se pudo conectar a MySQL: {error.msg}")


# ---------------------------------------------------------------------------
# Generacion (todo en memoria; despues se inserta)
# ---------------------------------------------------------------------------
def generar_roles():
    return [(i, nombre, descripcion) for i, (nombre, descripcion) in enumerate(ROLES, start=1)]


def generar_categorias():
    return [(i, nombre, corto(fake.sentence(nb_words=8), 255))
            for i, nombre in enumerate(GENEROS, start=1)]


def generar_empresas():
    tipos = ["desarrollador", "distribuidor", "ambos"]
    return [(i, corto(fake.company(), 100), tipos[i % 3],
             corto(fake.country(), 60), corto(fake.company_email(), 150))
            for i in range(1, N_EMPRESAS + 1)]


def generar_cuentas(roles, empresas, password):
    id_rol = {nombre: i for i, nombre, _ in roles}
    emp_desarrollo = [e[0] for e in empresas if e[2] in ("desarrollador", "ambos")]
    emp_distribucion = [e[0] for e in empresas if e[2] in ("distribuidor", "ambos")]
    cuentas, nicks, emails = [], set(), set()

    def nueva(rol, nac, nick=None, email=None, estado=None):
        id_empresa = None
        if rol == "Creador":
            id_empresa = fake.random_element(emp_desarrollo)
        elif rol == "Distribuidor":
            id_empresa = fake.random_element(emp_distribucion)
        # Se registra entre 2022 y ayer, y nunca antes de cumplir 10 anios
        registro = entre(datetime(2022, 1, 1), LIMITE)
        registro = max(registro, datetime.combine(nac, time.min) + timedelta(days=3650))
        cuentas.append({
            "id": len(cuentas) + 1,
            "nick": unico(nick or fake.user_name, nicks, 50),
            "email": unico(email or fake.email, emails, 150),
            "telefono": corto(fake.phone_number(), 20),
            "password_hash": hash_clave(password),
            "nombre": corto(fake.first_name(), 80),
            "apellidos": corto(f"{fake.last_name()} {fake.last_name()}", 120),
            "nacimiento": nac,
            "pais": corto(fake.country(), 60),
            "ip": fake.ipv4_public(),
            "registro": min(registro, LIMITE),
            "estado": estado or elegir([("activa", 0.92), ("suspendida", 0.05), ("baja", 0.03)]),
            "id_rol": id_rol[rol],
            "rol": rol,
            "id_empresa": id_empresa,
        })

    # Cuentas de prueba (una por rol y un menor). Estan en el README.
    pruebas = [
        ("admin_test", "Administrador", nacimiento(21, 58)),
        ("moderador_test", "Moderador", nacimiento(21, 58)),
        ("devops_test", "DevOps", nacimiento(21, 58)),
        ("creador_test", "Creador", nacimiento(21, 58)),
        ("distribuidor_test", "Distribuidor", nacimiento(21, 58)),
        ("jugador_test", "Jugador", nacimiento(18.5, 40)),
        ("menor_test", "Jugador", nacimiento(14, 14.9)),
    ]
    for nick, rol, nac in pruebas:
        nueva(rol, nac, nick=lambda n=nick: n, email=lambda n=nick: f"{n}@ejemplo.test",
              estado="activa")

    # Personal y empresas
    extra = ["Moderador"] * 2 + ["DevOps"] + ["Administrador"] + ["Creador"] * 6 + ["Distribuidor"] * 4
    for rol in extra:
        nueva(rol, nacimiento(21, 58))

    # Jugadores: alrededor de un 20 % son menores de edad (10 a 17 anios)
    while len(cuentas) < N_CUENTAS:
        es_menor = fake.boolean(chance_of_getting_true=20)
        nueva("Jugador", nacimiento(10, 17.99) if es_menor else nacimiento(18.5, 60))
    return cuentas


def generar_juegos(empresas, categorias):
    desarrolladoras = [e[0] for e in empresas if e[2] in ("desarrollador", "ambos")]
    distribuidoras = [e[0] for e in empresas if e[2] in ("distribuidor", "ambos")]
    precios = [("0.00", 0.08), ("4.99", 0.10), ("9.99", 0.18), ("14.99", 0.16), ("19.99", 0.16),
               ("29.99", 0.14), ("39.99", 0.08), ("49.99", 0.06), ("59.99", 0.04)]
    edades = [(3, 0.10), (7, 0.20), (12, 0.25), (16, 0.20), (18, 0.25)]
    titulos = set()
    juegos = []
    for i in range(1, N_JUEGOS + 1):
        # Titulo: dos palabras sueltas de Faker (de mas de 3 letras)
        while True:
            palabras = [p for p in fake.words(nb=3) if len(p) > 3][:2]
            titulo = corto(" ".join(p.capitalize() for p in palabras), 150)
            if len(palabras) == 2 and titulo not in titulos:
                titulos.add(titulo)
                break
        juegos.append({
            "id": i,
            "titulo": titulo,
            "descripcion": corto(fake.paragraph(nb_sentences=3), 2000),
            "precio": Decimal(elegir(precios)),
            "edad": elegir(edades),
            "lanzamiento": fake.date_between_dates(date(2015, 1, 1), date(2026, 9, 30)),
            "id_categoria": fake.random_element(categorias)[0],
            "id_desarrollador": fake.random_element(desarrolladoras),
            "id_distribuidor": fake.random_element(distribuidoras),
        })
    return juegos


def generar_objetos(juegos):
    rarezas = [("comun", 0.40), ("poco_comun", 0.28), ("raro", 0.18), ("epico", 0.10), ("legendario", 0.04)]
    rango_precio = {"comun": (0.99, 2.99), "poco_comun": (1.99, 4.99), "raro": (3.99, 9.99),
                    "epico": (7.99, 19.99), "legendario": (14.99, 49.99)}
    objetos = []
    for juego in juegos:
        nombres = set()
        for _ in range(fake.random_int(1, 4)):
            tipo = fake.tipo_objeto()
            nombre = corto(f"{tipo.capitalize()} {fake.color_name().lower()}", 100)
            if nombre in nombres:
                continue
            nombres.add(nombre)
            rareza = elegir(rarezas)
            objetos.append({
                "id": len(objetos) + 1,
                "id_juego": juego["id"],
                "nombre": nombre,
                "tipo": tipo,
                "rareza": rareza,
                "precio": dinero(*rango_precio[rareza]),
            })
    return objetos


def generar_metodos_pago(cuentas):
    metodos = []
    for cuenta in cuentas:
        if not fake.boolean(chance_of_getting_true=78):
            continue  # cuenta que nunca ha comprado
        es_menor = edad_en(cuenta["nacimiento"], AHORA) < 18
        for _ in range(elegir([(1, 0.75), (2, 0.25)])):
            tipo = elegir([("tarjeta", 0.70), ("IBAN", 0.25), ("otro", 0.05)])
            if tipo == "tarjeta":
                numero = fake.credit_card_number()
                caducidad = f"{fake.random_int(1, 12):02d}/{fake.random_int(27, 31)}"
            elif tipo == "IBAN":
                numero, caducidad = fake.iban(), "N/A"
            else:
                numero, caducidad = "PP-" + fake.bothify("########"), "N/A"
            # Un menor paga con una tarjeta o cuenta de un adulto (otro titular)
            titular = fake.name() if es_menor else f"{cuenta['nombre']} {cuenta['apellidos']}"
            metodos.append({
                "id": len(metodos) + 1,
                "id_cuenta": cuenta["id"],
                "tipo": tipo,
                "titular": corto(titular, 150),
                "numero": numero,
                "caducidad": caducidad,
                "direccion": corto(fake.address(), 255),
                "alta": entre(cuenta["registro"], LIMITE),
            })
    return metodos


def generar_compras(cuentas, metodos, juegos, objetos):
    """Compras de juegos (con su biblioteca) y de objetos (con su inventario)."""
    por_id = {c["id"]: c for c in cuentas}
    objetos_de = {}
    for o in objetos:
        objetos_de.setdefault(o["id_juego"], []).append(o)
    metodos_de = {}
    for m in metodos:
        metodos_de.setdefault(m["id_cuenta"], []).append(m)
    compradores = [c for c in cuentas if c["id"] in metodos_de]

    compras, biblioteca, inventario = [], {}, {}
    claves, pares = set(), set()
    estados = [("completada", 0.85), ("reembolsada", 0.05), ("fallida", 0.05), ("pendiente", 0.05)]

    def anotar(cuenta, metodo, fecha, estado, precio, id_juego=None, id_objeto=None):
        compras.append({"id_cuenta": cuenta["id"], "id_metodo": metodo["id"], "id_juego": id_juego,
                        "id_objeto": id_objeto, "importe": precio, "fecha": fecha, "estado": estado,
                        "ip": fake.ipv4_public()})

    # Compras de juegos
    hechas = intentos = 0
    while hechas < N_COMPRAS_JUEGO and intentos < N_COMPRAS_JUEGO * 40:
        intentos += 1
        cuenta = fake.random_element(compradores)
        juego = fake.random_element(juegos)
        if (cuenta["id"], juego["id"]) in pares:
            continue
        inicio = max(cuenta["registro"], datetime.combine(juego["lanzamiento"], time.min))
        if inicio >= LIMITE:
            continue
        fecha = entre(inicio, LIMITE)
        if edad_en(cuenta["nacimiento"], fecha) < juego["edad"]:
            continue  # un menor no compra un juego de mas edad que la suya
        validos = [m for m in metodos_de[cuenta["id"]] if m["alta"] <= fecha]
        if not validos:
            continue
        pares.add((cuenta["id"], juego["id"]))
        estado = elegir(estados)
        anotar(cuenta, fake.random_element(validos), fecha, estado, juego["precio"], id_juego=juego["id"])
        if estado == "completada":
            clave = fake.bothify("?#?#?-#?#?#-?#?#?-#?#?#", letters=string.ascii_uppercase)
            while clave in claves:
                clave = fake.bothify("?#?#?-#?#?#-?#?#?-#?#?#", letters=string.ascii_uppercase)
            claves.add(clave)
            max_horas = min(500, (AHORA - fecha).days * 3)
            biblioteca[(cuenta["id"], juego["id"])] = {
                "id_cuenta": cuenta["id"], "id_juego": juego["id"], "adquisicion": fecha, "clave": clave,
                "horas": dinero(0, max_horas).quantize(Decimal("0.1")) if max_horas > 0 else Decimal("0.0"),
            }
        hechas += 1

    # Compras de objetos: solo de juegos que la cuenta ya tiene en su biblioteca
    propietarios = {}
    for (id_cuenta, _), fila in biblioteca.items():
        propietarios.setdefault(id_cuenta, []).append(fila)
    ids_propietarios = list(propietarios)
    hechas = intentos = 0
    while hechas < N_COMPRAS_OBJETO and intentos < N_COMPRAS_OBJETO * 40:
        intentos += 1
        id_cuenta = fake.random_element(ids_propietarios)
        fila = fake.random_element(propietarios[id_cuenta])
        candidatos = objetos_de.get(fila["id_juego"])
        if not candidatos:
            continue
        objeto = fake.random_element(candidatos)
        fecha = entre(fila["adquisicion"], AHORA - timedelta(hours=1))
        validos = [m for m in metodos_de[id_cuenta] if m["alta"] <= fecha]
        if not validos:
            continue
        estado = elegir(estados)
        anotar(por_id[id_cuenta], fake.random_element(validos), fecha, estado, objeto["precio"],
               id_objeto=objeto["id"])
        if estado == "completada":
            llave = (id_cuenta, objeto["id"])
            if llave in inventario:
                inventario[llave]["cantidad"] += 1
                inventario[llave]["obtencion"] = min(inventario[llave]["obtencion"], fecha)
            else:
                inventario[llave] = {"id_cuenta": id_cuenta, "id_objeto": objeto["id"],
                                     "cantidad": 1, "obtencion": fecha}
        hechas += 1

    # Ids y numeros de factura por orden cronologico (la factura es UNIQUE)
    compras.sort(key=lambda c: c["fecha"])
    for i, c in enumerate(compras, start=1):
        c["id"] = i
        c["factura"] = f"F{c['fecha'].year}-{i:06d}"
    return compras, list(biblioteca.values()), list(inventario.values())


def generar_mensajes(cuentas):
    moderadores = [c["id"] for c in cuentas if c["rol"] in ("Moderador", "Administrador")]
    mensajes = []
    for i in range(1, N_MENSAJES + 1):
        emisor, receptor = fake.random_elements(cuentas, length=2, unique=True)  # nunca el mismo
        ofensivo = fake.boolean(chance_of_getting_true=8)
        texto = fake.insulto() if ofensivo else fake.sentence(nb_words=fake.random_int(4, 14))
        eliminado = ofensivo and fake.boolean(chance_of_getting_true=75)
        libres = [m for m in moderadores if m not in (emisor["id"], receptor["id"])]
        mensajes.append({
            "id": i,
            "emisor": emisor["id"],
            "receptor": receptor["id"],
            "texto": corto(texto, 500),
            "fecha": entre(max(emisor["registro"], receptor["registro"]), AHORA - timedelta(hours=1)),
            "estado": "eliminado" if eliminado else "normal",
            "moderador": fake.random_element(libres) if eliminado else None,
        })
    return mensajes


# ---------------------------------------------------------------------------
# Insercion y comprobaciones
# ---------------------------------------------------------------------------
def insertar(cur, sql, filas):
    if filas:
        cur.executemany(sql, filas)


def cargar(conn, d):
    cur = conn.cursor()
    insertar(cur, "INSERT INTO rol (id_rol, nombre, descripcion) VALUES (%s,%s,%s)", d["roles"])
    insertar(cur, "INSERT INTO empresa (id_empresa, nombre, tipo, pais, email_contacto) "
                  "VALUES (%s,%s,%s,%s,%s)", d["empresas"])
    insertar(cur, "INSERT INTO categoria (id_categoria, nombre, descripcion) VALUES (%s,%s,%s)",
             d["categorias"])
    insertar(cur, """INSERT INTO cuenta (id_cuenta, nick, email, telefono, password_hash, nombre,
                     apellidos, fecha_nacimiento, pais, ip_registro, fecha_registro, estado,
                     id_rol, id_empresa) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
             [(c["id"], c["nick"], c["email"], c["telefono"], c["password_hash"], c["nombre"],
               c["apellidos"], c["nacimiento"], c["pais"], c["ip"], c["registro"], c["estado"],
               c["id_rol"], c["id_empresa"]) for c in d["cuentas"]])
    insertar(cur, """INSERT INTO juego (id_juego, titulo, descripcion, precio, clasificacion_edad,
                     fecha_lanzamiento, id_categoria, id_desarrollador, id_distribuidor)
                     VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
             [(j["id"], j["titulo"], j["descripcion"], j["precio"], j["edad"], j["lanzamiento"],
               j["id_categoria"], j["id_desarrollador"], j["id_distribuidor"]) for j in d["juegos"]])
    insertar(cur, """INSERT INTO objeto_ingame (id_objeto, id_juego, nombre, tipo, rareza, precio)
                     VALUES (%s,%s,%s,%s,%s,%s)""",
             [(o["id"], o["id_juego"], o["nombre"], o["tipo"], o["rareza"], o["precio"])
              for o in d["objetos"]])
    insertar(cur, """INSERT INTO metodo_pago (id_metodo, id_cuenta, tipo, titular, numero, caducidad,
                     direccion_facturacion, fecha_alta) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
             [(m["id"], m["id_cuenta"], m["tipo"], m["titular"], m["numero"], m["caducidad"],
               m["direccion"], m["alta"]) for m in d["metodos"]])
    insertar(cur, """INSERT INTO compra (id_compra, id_cuenta, id_metodo, id_juego, id_objeto, importe,
                     fecha, estado, numero_factura, ip_origen) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
             [(c["id"], c["id_cuenta"], c["id_metodo"], c["id_juego"], c["id_objeto"], c["importe"],
               c["fecha"], c["estado"], c["factura"], c["ip"]) for c in d["compras"]])
    insertar(cur, """INSERT INTO biblioteca (id_cuenta, id_juego, fecha_adquisicion, clave_activacion,
                     horas_jugadas) VALUES (%s,%s,%s,%s,%s)""",
             [(b["id_cuenta"], b["id_juego"], b["adquisicion"], b["clave"], b["horas"])
              for b in d["biblioteca"]])
    insertar(cur, """INSERT INTO inventario (id_cuenta, id_objeto, cantidad, fecha_obtencion)
                     VALUES (%s,%s,%s,%s)""",
             [(i["id_cuenta"], i["id_objeto"], i["cantidad"], i["obtencion"]) for i in d["inventario"]])
    insertar(cur, """INSERT INTO mensaje (id_mensaje, id_emisor, id_receptor, texto, fecha, estado,
                     id_moderador) VALUES (%s,%s,%s,%s,%s,%s,%s)""",
             [(m["id"], m["emisor"], m["receptor"], m["texto"], m["fecha"], m["estado"], m["moderador"])
              for m in d["mensajes"]])
    cur.close()


def vaciar(conn):
    cur = conn.cursor()
    cur.execute("SET FOREIGN_KEY_CHECKS = 0")
    for tabla in BORRADO:
        cur.execute(f"TRUNCATE TABLE {tabla}")
    cur.execute("SET FOREIGN_KEY_CHECKS = 1")
    cur.close()


def resumen(conn):
    cur = conn.cursor()
    print("\nFilas por tabla:")
    total = 0
    for tabla in reversed(BORRADO):
        cur.execute(f"SELECT COUNT(*) FROM {tabla}")
        n = cur.fetchone()[0]
        total += n
        print(f"  {tabla:<14}{n:>6}")
    print(f"  {'TOTAL':<14}{total:>6}")

    comprobaciones = {
        "Menores con un juego por encima de su edad en la biblioteca": """
            SELECT COUNT(*) FROM biblioteca b JOIN cuenta c USING (id_cuenta)
            JOIN juego j USING (id_juego)
            WHERE TIMESTAMPDIFF(YEAR, c.fecha_nacimiento, b.fecha_adquisicion) < j.clasificacion_edad""",
        "Compras que no cumplen 'un solo producto'": """
            SELECT COUNT(*) FROM compra WHERE (id_juego IS NULL) = (id_objeto IS NULL)""",
        "Inventario con cantidad distinta de las compras completadas": """
            SELECT COUNT(*) FROM inventario i WHERE i.cantidad <> (
              SELECT COUNT(*) FROM compra c WHERE c.id_cuenta = i.id_cuenta
              AND c.id_objeto = i.id_objeto AND c.estado = 'completada')""",
        "Mensajes eliminados sin moderador": """
            SELECT COUNT(*) FROM mensaje WHERE estado = 'eliminado' AND id_moderador IS NULL""",
        "Cuentas con empresa que no son Creador ni Distribuidor": """
            SELECT COUNT(*) FROM cuenta c JOIN rol r USING (id_rol)
            WHERE c.id_empresa IS NOT NULL AND r.nombre NOT IN ('Creador', 'Distribuidor')""",
    }
    print("\nComprobaciones de coherencia (todas deben ser 0):")
    for texto, sql in comprobaciones.items():
        cur.execute(sql)
        print(f"  {cur.fetchone()[0]:>3}  {texto}")

    cur.execute("SELECT COUNT(*) FROM cuenta WHERE TIMESTAMPDIFF(YEAR, fecha_nacimiento, %s) < 18", (AHORA,))
    print(f"\nCuentas de menores de edad: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(DISTINCT id_rol) FROM cuenta")
    print(f"Perfiles de usuario distintos: {cur.fetchone()[0]}")
    cur.close()
    return total


def main():
    parser = argparse.ArgumentParser(description="Carga datos sinteticos en tienda_juegos")
    parser.add_argument("--reset", action="store_true", help="vacia las tablas antes de cargar")
    args = parser.parse_args()

    password = os.getenv("SEED_TEST_PASSWORD")
    mostrar_password = not password
    if mostrar_password:
        password = secrets.token_urlsafe(12)

    conn = conectar()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM cuenta")
        if cur.fetchone()[0] > 0 and not args.reset:
            sys.exit("La base de datos ya tiene datos. Usa --reset para vaciarla y volver a cargar.")
        cur.close()

        print("Generando datos sinteticos (el hash bcrypt de las claves tarda unos segundos)...")
        roles = generar_roles()
        categorias = generar_categorias()
        empresas = generar_empresas()
        cuentas = generar_cuentas(roles, empresas, password)
        juegos = generar_juegos(empresas, categorias)
        objetos = generar_objetos(juegos)
        metodos = generar_metodos_pago(cuentas)
        compras, biblioteca, inventario = generar_compras(cuentas, metodos, juegos, objetos)
        mensajes = generar_mensajes(cuentas)

        if args.reset:
            vaciar(conn)
        cargar(conn, {"roles": roles, "categorias": categorias, "empresas": empresas,
                      "cuentas": cuentas, "juegos": juegos, "objetos": objetos, "metodos": metodos,
                      "compras": compras, "biblioteca": biblioteca, "inventario": inventario,
                      "mensajes": mensajes})
        conn.commit()
    except Exception:
        conn.rollback()
        raise

    total = resumen(conn)
    conn.close()
    if total < 500:
        sys.exit(f"Atencion: solo hay {total} filas y el enunciado exige al menos 500.")
    print("\nUsuarios de prueba: admin_test, moderador_test, devops_test, creador_test,"
          " distribuidor_test, jugador_test, menor_test")
    if mostrar_password:
        print(f"Clave de los usuarios de prueba (solo se muestra ahora): {password}")
    else:
        print("Clave de los usuarios de prueba: la de SEED_TEST_PASSWORD en tu .env")


if __name__ == "__main__":
    main()
