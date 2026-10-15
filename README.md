# Plataforma de videojuegos online — Proyecto SBD 2026-27

Miembros: Victor Castro Quesada, Oscar Fernandez Andujar

## Datos del proyecto

| | |
|---|---|
| Proyecto | Proyecto integrador: diseño, bastionado y auditoría de una base de datos MySQL |
| Caso de negocio | Plataforma de videojuegos online (n.º 4) |
| Asignatura | Seguridad en las Bases de Datos |
| Titulación | Grado en Ciberseguridad · ENTI-UB · Curso 2026-27 |
| Profesor | Eduard Lara |
| Repositorio |https://github.com/Vittox/sbd-videojuegos  |

## Integrantes

| Nombre |
|---|
| Victor Castro Quesada |
|---|
| Oscar Fernandez Andujar |
|---|

## Enunciado

Resumen del enunciado oficial del proyecto (Proyecto_integrador_Seguridad_BD_2026-27.pdf, 5 de octubre de 2026).

### Presentación

Cada equipo diseña, bastiona y audita una base de datos MySQL conectada a una aplicación en Python. El trabajo se entrega en cinco hitos (M0 a M4) y termina con un informe de auditoría de seguridad y una defensa oral. Peso en la nota final: 15 % en evaluación continuada (AC2) y 30 % en evaluación única (AU1).

### Escenario

Somos el departamento de seguridad de una organización que acaba de digitalizar su gestión. La dirección nos encarga desplegar su base de datos, protegerla y demostrar con evidencias que es segura. Nuestro caso: **plataforma de videojuegos online** (datos sensibles principales: cuentas, compras in-game, chats y menores de edad).

Requisitos mínimos del sistema:

- Al menos 8 tablas relacionadas, con claves primarias y foráneas.
- Al menos 3 categorías de datos sensibles (personales, financieros, de salud…).
- Al menos 4 perfiles de usuario distintos.
- Al menos 500 filas de datos sintéticos generados con un script (por ejemplo con Faker). Prohibido usar datos reales.
- Una aplicación en Python (consola o Flask) que permita iniciar sesión, consultar y modificar datos según el perfil.

### Organización y entorno

- Grupos de 3 a 4 personas. Cada persona es responsable de al menos un apartado técnico por hito y debe constar en el informe.
- MySQL 8.x desplegado con Docker Compose. Python 3.11 o superior con mysql-connector-python o PyMySQL.
- Credenciales en variables de entorno o en un fichero `.env` excluido del repositorio.
- Repositorio Git privado compartido con el profesor. Cada miembro hace commits con su propia cuenta.
- Comparativa (U11): Oracle Database Free o SQL Server Developer, en Docker.
- El entorno debe poder levantarse desde cero con `docker compose up` y las instrucciones del README. Si no arranca, el hito no se evalúa.
- No se permite generar con IA el código, las configuraciones ni el texto de los informes. En cada hito hay demostración en clase y preguntas a cualquier miembro del grupo.

### Hitos

| Hito | Contenido | Unidades · RA |
|---|---|---|
| M0 | Arranque y modelo de amenazas: modelo E-R, esquema MySQL, Docker Compose, datos sintéticos, clasificación de datos por sensibilidad (público, interno, confidencial, restringido) y modelo de amenazas inicial (activos, amenazas por dimensión CIA, probabilidad e impacto). | U1 · RA1 |
| M1 | Vistas de seguridad (2 de columnas y 2 de filas), 2 transacciones críticas con COMMIT y ROLLBACK, reproducción de lectura sucia, no repetible y fantasma con dos sesiones, y justificación del nivel de aislamiento. | U2-U4 · RA2-RA4 |
| M2 | Bastionado con CIS Benchmark (al menos 10 controles, antes y después), limpieza de cuentas por defecto, matriz RBAC con mínimo privilegio, implementación con CREATE ROLE, GRANT y REVOKE, y pruebas de denegación. | U5-U6 · RA5-RA6 |
| M3 | Aplicación Python con login y 4 funcionalidades, rama vulnerable a inyección SQL (2 técnicas) y su corrección con consultas parametrizadas, hash y salt (bcrypt o Argon2), cifrado de 2 columnas, enmascaramiento en vistas y cifrado en reposo (tablespace InnoDB). | U7, U8, U10 · RA7, RA8, RA10 |
| M4 | Política de backups con RPO y RTO, script automatizado y cifrado, simulación de desastre con recuperación a un punto en el tiempo, auditoría nativa en Oracle o SQL Server y comparativa con MySQL. | U9, U11 · RA9, RA11 |

Entregables de M0: esquema SQL, script de datos, `docker-compose.yml`, README, informe M0 con el diagrama E-R y la tabla de amenazas.

### Entrega

- Plazo: 23:59 del día anterior a la sesión indicada.
- PDF del informe del hito (`SBD_Grupo<n>_M<n>.pdf`) y enlace al repositorio.
- Etiqueta Git del hito (M0, M1…, FINAL) creada antes del plazo. Se evalúa el código de esa etiqueta.

### Defensa oral

20 minutos por grupo en la última sesión: exposición (8 min), demostración en directo (7 min) y preguntas individuales (5 min). La nota de la defensa es individual.

### Rúbrica

| Parte | Peso |
|---|---|
| M0 — Arranque y modelo de amenazas | 5 % |
| M1 — Vistas, transacciones y aislamiento | 15 % |
| M2 — Bastionado y control de acceso | 15 % |
| M3 — Aplicación segura, SQLi y cifrado | 20 % |
| M4 — Resiliencia y comparativa | 15 % |
| Informe final de auditoría | 15 % |
| Defensa oral (individual) | 15 % |

### Penalizaciones

- Entrega fuera de plazo: −10 % por día, hasta 3 días. Después, el hito vale 0.
- Entorno que no arranca siguiendo el README: el hito no se evalúa hasta que se corrija.
- Credenciales reales o secretos subidos al repositorio: −1 punto en el hito.
- Uso de IA no permitido o trabajo que el autor no sabe explicar: 0 en la parte afectada.

## Requisitos
- Docker y Docker Compose
- Python 3.11+

## Puesta en marcha
1. cp .env.example .env   # rellenar valores
2. docker compose up -d
3. pip install -r requirements.txt
4. python app/main.py

## Usuarios de prueba
| Rol | Usuario | Dónde está la contraseña |
|-----|---------|---------------------------|

## Estructura
- db/       esquema, datos, vistas, roles
- app/      aplicación Python
- backup/   scripts de backup y restauración
- docs/     informes de hito e informe final
