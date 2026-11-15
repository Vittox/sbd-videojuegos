USE tienda_juegos;

-- ============================================================================
-- 1. Vistas de restriccion de columnas (ocultan datos confidenciales y restringidos)
-- ============================================================================

-- Perfil publico de cuentas: oculta password_hash, email, telefono, nombre,
-- apellidos, fecha_nacimiento e ip_registro (mitiga T04 y T10)
CREATE OR REPLACE VIEW v_cuentas_publicas AS
SELECT
  c.id_cuenta,
  c.nick,
  c.pais,
  c.fecha_registro,
  c.estado,
  r.nombre AS rol,
  e.nombre AS empresa
FROM cuenta c
JOIN rol r ON c.id_rol = r.id_rol
LEFT JOIN empresa e ON c.id_empresa = e.id_empresa;

-- Resumen de compras para moderacion/analitica: oculta numero de tarjeta/IBAN,
-- caducidad, titular, direccion de facturacion e ip_origen (mitiga T03 y T04)
CREATE OR REPLACE VIEW v_compras_analitica AS
SELECT
  co.id_compra,
  co.numero_factura,
  c.nick AS comprador,
  mp.tipo AS tipo_pago,
  CASE
    WHEN co.id_juego IS NOT NULL THEN 'juego'
    ELSE 'objeto'
  END AS tipo_producto,
  COALESCE(j.titulo, o.nombre) AS producto,
  co.importe,
  co.fecha,
  co.estado
FROM compra co
JOIN cuenta c ON co.id_cuenta = c.id_cuenta
JOIN metodo_pago mp ON co.id_metodo = mp.id_metodo
LEFT JOIN juego j ON co.id_juego = j.id_juego
LEFT JOIN objeto_ingame o ON co.id_objeto = o.id_objeto;

-- ============================================================================
-- 2. Vistas de restriccion de filas (cada usuario consulta solo sus registros)
-- ============================================================================

-- Historial propio de compras del usuario conectado (oculta ip_origen)
CREATE OR REPLACE VIEW v_mis_compras AS
SELECT
  co.id_compra,
  co.numero_factura,
  mp.tipo AS metodo_pago,
  COALESCE(j.titulo, o.nombre) AS producto,
  co.importe,
  co.fecha,
  co.estado
FROM compra co
JOIN cuenta c ON co.id_cuenta = c.id_cuenta
JOIN metodo_pago mp ON co.id_metodo = mp.id_metodo
LEFT JOIN juego j ON co.id_juego = j.id_juego
LEFT JOIN objeto_ingame o ON co.id_objeto = o.id_objeto
WHERE c.nick = SUBSTRING_INDEX(CURRENT_USER(), '@', 1);

-- Mensajes privados donde el usuario conectado es emisor o receptor
-- y el mensaje no ha sido eliminado por moderacion
CREATE OR REPLACE VIEW v_mis_mensajes AS
SELECT
  m.id_mensaje,
  em.nick AS emisor,
  re.nick AS receptor,
  m.texto,
  m.fecha
FROM mensaje m
JOIN cuenta em ON m.id_emisor = em.id_cuenta
JOIN cuenta re ON m.id_receptor = re.id_cuenta
WHERE (
    em.nick = SUBSTRING_INDEX(CURRENT_USER(), '@', 1)
    OR re.nick = SUBSTRING_INDEX(CURRENT_USER(), '@', 1)
  )
  AND m.estado = 'normal';

-- Catalogo filtrado por la clasificacion de edad del usuario conectado (mitiga T09)
CREATE OR REPLACE VIEW v_catalogo_disponible AS
SELECT
  j.id_juego,
  j.titulo,
  j.descripcion,
  j.precio,
  j.clasificacion_edad,
  j.fecha_lanzamiento,
  cat.nombre AS categoria,
  ed.nombre AS desarrollador,
  di.nombre AS distribuidor
FROM juego j
JOIN categoria cat ON j.id_categoria = cat.id_categoria
JOIN empresa ed ON j.id_desarrollador = ed.id_empresa
JOIN empresa di ON j.id_distribuidor = di.id_empresa
JOIN cuenta c ON c.nick = SUBSTRING_INDEX(CURRENT_USER(), '@', 1)
WHERE j.clasificacion_edad <= TIMESTAMPDIFF(YEAR, c.fecha_nacimiento, CURDATE());

-- ============================================================================
-- 3. Usuarios de prueba en MySQL y permisos sobre las vistas
-- ============================================================================

CREATE USER IF NOT EXISTS 'jugador_test'@'%' IDENTIFIED BY 'Sbd_Test_2026!';
CREATE USER IF NOT EXISTS 'menor_test'@'%' IDENTIFIED BY 'Sbd_Test_2026!';
CREATE USER IF NOT EXISTS 'moderador_test'@'%' IDENTIFIED BY 'Sbd_Test_2026!';

GRANT SELECT ON tienda_juegos.v_cuentas_publicas TO 'jugador_test'@'%', 'menor_test'@'%', 'moderador_test'@'%';
GRANT SELECT ON tienda_juegos.v_catalogo_disponible TO 'jugador_test'@'%', 'menor_test'@'%';
GRANT SELECT ON tienda_juegos.v_mis_compras TO 'jugador_test'@'%', 'menor_test'@'%';
GRANT SELECT ON tienda_juegos.v_mis_mensajes TO 'jugador_test'@'%', 'menor_test'@'%';
GRANT SELECT ON tienda_juegos.v_compras_analitica TO 'moderador_test'@'%';

FLUSH PRIVILEGES;