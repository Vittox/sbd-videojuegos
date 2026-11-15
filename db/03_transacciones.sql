USE tienda_juegos;

DROP PROCEDURE IF EXISTS sp_comprar_juego;
DROP PROCEDURE IF EXISTS sp_comprar_objeto;

DELIMITER //

-- ============================================================================
-- Operacion critica 1: Compra de un juego y registro en biblioteca
-- ============================================================================
CREATE PROCEDURE sp_comprar_juego(
  IN p_id_cuenta INT,
  IN p_id_juego INT,
  IN p_id_metodo INT,
  IN p_ip_origen VARCHAR(45)
)
BEGIN
  DECLARE v_estado_cuenta VARCHAR(20);
  DECLARE v_fecha_nac DATE;
  DECLARE v_precio DECIMAL(8,2);
  DECLARE v_edad_min TINYINT;
  DECLARE v_metodo_valido INT DEFAULT 0;
  DECLARE v_id_compra INT;
  DECLARE v_clave VARCHAR(50);

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
  START TRANSACTION;

  -- Bloqueamos la cuenta para serializar compras concurrentes del mismo usuario
  SELECT estado, fecha_nacimiento
    INTO v_estado_cuenta, v_fecha_nac
    FROM cuenta
    WHERE id_cuenta = p_id_cuenta
    FOR UPDATE;

  IF v_estado_cuenta IS NULL OR v_estado_cuenta <> 'activa' THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'La cuenta no existe o no esta activa';
  END IF;

  SELECT precio, clasificacion_edad
    INTO v_precio, v_edad_min
    FROM juego
    WHERE id_juego = p_id_juego;

  IF v_precio IS NULL THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'El juego indicado no existe';
  END IF;

  -- Control de edad minima (mitiga T09)
  IF TIMESTAMPDIFF(YEAR, v_fecha_nac, CURDATE()) < v_edad_min THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'El usuario no cumple la edad minima para este juego';
  END IF;

  -- Verificamos que el metodo de pago pertenezca a la cuenta
  SELECT COUNT(*)
    INTO v_metodo_valido
    FROM metodo_pago
    WHERE id_metodo = p_id_metodo
      AND id_cuenta = p_id_cuenta;

  IF v_metodo_valido = 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'El metodo de pago no pertenece a la cuenta';
  END IF;

  -- 1. Registramos la factura en compra
  INSERT INTO compra (
    id_cuenta, id_metodo, id_juego, id_objeto,
    importe, estado, numero_factura, ip_origen
  ) VALUES (
    p_id_cuenta, p_id_metodo, p_id_juego, NULL,
    v_precio, 'completada', CONCAT('TMP-', UUID_SHORT()), p_ip_origen
  );

  SET v_id_compra = LAST_INSERT_ID();

  UPDATE compra
    SET numero_factura = CONCAT('F', YEAR(fecha), '-', LPAD(v_id_compra, 6, '0'))
    WHERE id_compra = v_id_compra;

  -- 2. Anadimos el juego a la biblioteca (falla con 1062 y hace ROLLBACK si ya lo tiene)
  SET v_clave = UPPER(CONCAT(
    SUBSTRING(MD5(RAND()), 1, 5), '-',
    SUBSTRING(MD5(RAND()), 1, 5), '-',
    SUBSTRING(MD5(RAND()), 1, 5), '-',
    SUBSTRING(MD5(RAND()), 1, 4)
  ));

  INSERT INTO biblioteca (
    id_cuenta, id_juego, clave_activacion, horas_jugadas
  ) VALUES (
    p_id_cuenta, p_id_juego, v_clave, 0.0
  );

  COMMIT;

  SELECT
    v_id_compra AS id_compra,
    CONCAT('F', YEAR(NOW()), '-', LPAD(v_id_compra, 6, '0')) AS numero_factura,
    v_precio AS importe,
    v_clave AS clave_activacion;
END //

-- ============================================================================
-- Operacion critica 2: Compra de objeto in-game y actualizacion de inventario
-- ============================================================================
CREATE PROCEDURE sp_comprar_objeto(
  IN p_id_cuenta INT,
  IN p_id_objeto INT,
  IN p_id_metodo INT,
  IN p_cantidad INT,
  IN p_ip_origen VARCHAR(45)
)
BEGIN
  DECLARE v_estado_cuenta VARCHAR(20);
  DECLARE v_id_juego INT;
  DECLARE v_precio DECIMAL(8,2);
  DECLARE v_importe_total DECIMAL(8,2);
  DECLARE v_metodo_valido INT DEFAULT 0;
  DECLARE v_tiene_juego INT DEFAULT 0;
  DECLARE v_id_compra INT;

  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;

  SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
  START TRANSACTION;

  IF p_cantidad IS NULL OR p_cantidad <= 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'La cantidad debe ser mayor que cero';
  END IF;

  SELECT estado
    INTO v_estado_cuenta
    FROM cuenta
    WHERE id_cuenta = p_id_cuenta
    FOR UPDATE;

  IF v_estado_cuenta IS NULL OR v_estado_cuenta <> 'activa' THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'La cuenta no existe o no esta activa';
  END IF;

  SELECT id_juego, precio
    INTO v_id_juego, v_precio
    FROM objeto_ingame
    WHERE id_objeto = p_id_objeto;

  IF v_id_juego IS NULL THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'El objeto in-game indicado no existe';
  END IF;

  SELECT COUNT(*)
    INTO v_metodo_valido
    FROM metodo_pago
    WHERE id_metodo = p_id_metodo
      AND id_cuenta = p_id_cuenta;

  IF v_metodo_valido = 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'El metodo de pago no pertenece a la cuenta';
  END IF;

  SET v_importe_total = v_precio * p_cantidad;

  -- 1. Registramos la compra
  INSERT INTO compra (
    id_cuenta, id_metodo, id_juego, id_objeto,
    importe, estado, numero_factura, ip_origen
  ) VALUES (
    p_id_cuenta, p_id_metodo, NULL, p_id_objeto,
    v_importe_total, 'completada', CONCAT('TMP-', UUID_SHORT()), p_ip_origen
  );

  SET v_id_compra = LAST_INSERT_ID();

  UPDATE compra
    SET numero_factura = CONCAT('F', YEAR(fecha), '-', LPAD(v_id_compra, 6, '0'))
    WHERE id_compra = v_id_compra;

  -- 2. Regla de negocio: solo puede obtener el objeto si posee el juego base
  -- Si no lo tiene, lanza error y revierte tambien el INSERT previo en compra
  SELECT COUNT(*)
    INTO v_tiene_juego
    FROM biblioteca
    WHERE id_cuenta = p_id_cuenta
      AND id_juego = v_id_juego
    FOR UPDATE;

  IF v_tiene_juego = 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'El usuario no posee el juego base en su biblioteca';
  END IF;

  -- 3. Sumamos la cantidad al inventario del jugador
  INSERT INTO inventario (
    id_cuenta, id_objeto, cantidad, fecha_obtencion
  ) VALUES (
    p_id_cuenta, p_id_objeto, p_cantidad, NOW()
  )
  ON DUPLICATE KEY UPDATE
    cantidad = cantidad + p_cantidad,
    fecha_obtencion = NOW();

  COMMIT;

  SELECT
    v_id_compra AS id_compra,
    CONCAT('F', YEAR(NOW()), '-', LPAD(v_id_compra, 6, '0')) AS numero_factura,
    p_cantidad AS unidades,
    v_importe_total AS importe_total;
END //

DELIMITER ;