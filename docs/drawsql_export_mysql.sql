CREATE TABLE `rol`(
    `id_rol` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `nombre` VARCHAR(50) NOT NULL,
    `descripcion` VARCHAR(255) NOT NULL
);
ALTER TABLE
    `rol` ADD UNIQUE `rol_nombre_unique`(`nombre`);
CREATE TABLE `empresa`(
    `id_empresa` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `nombre` VARCHAR(100) NOT NULL,
    `tipo` ENUM(
        'desarrollador',
        'distribuidor',
        'ambos'
    ) NOT NULL,
    `pais` VARCHAR(60) NOT NULL,
    `email_contacto` VARCHAR(150) NOT NULL
);
CREATE TABLE `categoria`(
    `id_categoria` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `nombre` VARCHAR(60) NOT NULL,
    `descripcion` TEXT NOT NULL
);
ALTER TABLE
    `categoria` ADD UNIQUE `categoria_nombre_unique`(`nombre`);
CREATE TABLE `cuenta`(
    `id_cuenta` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `nick` VARCHAR(50) NOT NULL,
    `email` VARCHAR(150) NOT NULL,
    `telefono` VARCHAR(20) NOT NULL,
    `password_hash` VARCHAR(255) NOT NULL,
    `nombre` VARCHAR(80) NOT NULL,
    `apellidos` VARCHAR(120) NOT NULL,
    `fecha_nacimiento` DATE NOT NULL,
    `pais` VARCHAR(60) NOT NULL,
    `ip_registro` VARCHAR(45) NOT NULL,
    `fecha_registro` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP(), `estado` ENUM('activa', 'suspendida', 'baja') NOT NULL DEFAULT 'activa', `id_rol` INT NOT NULL, `id_empresa` INT NULL);
ALTER TABLE
    `cuenta` ADD UNIQUE `cuenta_nick_unique`(`nick`);
ALTER TABLE
    `cuenta` ADD UNIQUE `cuenta_email_unique`(`email`);
CREATE TABLE `juego`(
    `id_juego` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `titulo` VARCHAR(150) NOT NULL,
    `descripcion` TEXT NOT NULL,
    `precio` DECIMAL(8, 2) NOT NULL,
    `clasificacion_edad` TINYINT NOT NULL,
    `fecha_lanzamiento` DATE NOT NULL,
    `id_categoria` INT NOT NULL,
    `id_desarrollador` INT NOT NULL,
    `id_distribuidor` INT NOT NULL
);
CREATE TABLE `biblioteca`(
    `id_cuenta` INT NOT NULL,
    `id_juego` INT NOT NULL,
    `fecha_adquisicion` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP(), `clave_activacion` VARCHAR(50) NOT NULL, `horas_jugadas` DECIMAL(8, 1) NOT NULL, PRIMARY KEY(`id_cuenta`));
ALTER TABLE
    `biblioteca` ADD PRIMARY KEY(`id_juego`);
ALTER TABLE
    `biblioteca` ADD UNIQUE `biblioteca_clave_activacion_unique`(`clave_activacion`);
CREATE TABLE `metodo_pago`(
    `id_metodo` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `id_cuenta` INT NOT NULL,
    `tipo` ENUM('tarjeta', 'IBAN', 'otro') NOT NULL,
    `titular` VARCHAR(150) NOT NULL,
    `numero` VARCHAR(255) NOT NULL,
    `caducidad` VARCHAR(10) NOT NULL,
    `direccion_facturacion` VARCHAR(255) NOT NULL,
    `fecha_alta` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP());
CREATE TABLE `objeto_ingame`(
    `id_objeto` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `id_juego` INT NOT NULL,
    `nombre` VARCHAR(100) NOT NULL,
    `tipo` VARCHAR(50) NOT NULL,
    `rareza` ENUM(
        'comun',
        'poco_comun',
        'raro',
        'epico',
        'legendario'
    ) NOT NULL,
    `precio` DECIMAL(8, 2) NOT NULL
);
CREATE TABLE `inventario`(
    `id_cuenta` INT NOT NULL,
    `id_objeto` INT NOT NULL,
    `cantidad` INT NOT NULL DEFAULT 1,
    `fecha_obtencion` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP(), PRIMARY KEY(`id_cuenta`));
ALTER TABLE
    `inventario` ADD PRIMARY KEY(`id_objeto`);
CREATE TABLE `compra`(
    `id_compra` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `id_cuenta` INT NOT NULL,
    `id_metodo` INT NOT NULL,
    `id_juego` INT NULL,
    `id_objeto` INT NULL,
    `importe` DECIMAL(8, 2) NOT NULL,
    `fecha` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP(), `estado` ENUM(
        'pendiente',
        'completada',
        'reembolsada',
        'fallida'
    ) NOT NULL, `numero_factura` VARCHAR(30) NOT NULL, `ip_origen` VARCHAR(45) NOT NULL);
ALTER TABLE
    `compra` ADD UNIQUE `compra_numero_factura_unique`(`numero_factura`);
CREATE TABLE `mensaje`(
    `id_mensaje` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `id_emisor` INT NOT NULL,
    `id_receptor` INT NOT NULL,
    `texto` TEXT NOT NULL,
    `fecha` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP(), `estado` ENUM('normal', 'eliminado') NOT NULL DEFAULT 'normal', `id_moderador` INT NULL);
ALTER TABLE
    `compra` ADD CONSTRAINT `compra_id_cuenta_foreign` FOREIGN KEY(`id_cuenta`) REFERENCES `cuenta`(`id_cuenta`);
ALTER TABLE
    `cuenta` ADD CONSTRAINT `cuenta_id_empresa_foreign` FOREIGN KEY(`id_empresa`) REFERENCES `empresa`(`id_empresa`);
ALTER TABLE
    `biblioteca` ADD CONSTRAINT `biblioteca_id_cuenta_foreign` FOREIGN KEY(`id_cuenta`) REFERENCES `cuenta`(`id_cuenta`);
ALTER TABLE
    `inventario` ADD CONSTRAINT `inventario_id_cuenta_foreign` FOREIGN KEY(`id_cuenta`) REFERENCES `cuenta`(`id_cuenta`);
ALTER TABLE
    `compra` ADD CONSTRAINT `compra_id_objeto_foreign` FOREIGN KEY(`id_objeto`) REFERENCES `objeto_ingame`(`id_objeto`);
ALTER TABLE
    `inventario` ADD CONSTRAINT `inventario_id_objeto_foreign` FOREIGN KEY(`id_objeto`) REFERENCES `objeto_ingame`(`id_objeto`);
ALTER TABLE
    `juego` ADD CONSTRAINT `juego_id_distribuidor_foreign` FOREIGN KEY(`id_distribuidor`) REFERENCES `empresa`(`id_empresa`);
ALTER TABLE
    `compra` ADD CONSTRAINT `compra_id_juego_foreign` FOREIGN KEY(`id_juego`) REFERENCES `juego`(`id_juego`);
ALTER TABLE
    `mensaje` ADD CONSTRAINT `mensaje_id_emisor_foreign` FOREIGN KEY(`id_emisor`) REFERENCES `cuenta`(`id_cuenta`);
ALTER TABLE
    `biblioteca` ADD CONSTRAINT `biblioteca_id_juego_foreign` FOREIGN KEY(`id_juego`) REFERENCES `juego`(`id_juego`);
ALTER TABLE
    `juego` ADD CONSTRAINT `juego_id_categoria_foreign` FOREIGN KEY(`id_categoria`) REFERENCES `categoria`(`id_categoria`);
ALTER TABLE
    `juego` ADD CONSTRAINT `juego_id_desarrollador_foreign` FOREIGN KEY(`id_desarrollador`) REFERENCES `empresa`(`id_empresa`);
ALTER TABLE
    `mensaje` ADD CONSTRAINT `mensaje_id_receptor_foreign` FOREIGN KEY(`id_receptor`) REFERENCES `cuenta`(`id_cuenta`);
ALTER TABLE
    `metodo_pago` ADD CONSTRAINT `metodo_pago_id_cuenta_foreign` FOREIGN KEY(`id_cuenta`) REFERENCES `cuenta`(`id_cuenta`);
ALTER TABLE
    `objeto_ingame` ADD CONSTRAINT `objeto_ingame_id_juego_foreign` FOREIGN KEY(`id_juego`) REFERENCES `juego`(`id_juego`);
ALTER TABLE
    `cuenta` ADD CONSTRAINT `cuenta_id_rol_foreign` FOREIGN KEY(`id_rol`) REFERENCES `rol`(`id_rol`);
ALTER TABLE
    `compra` ADD CONSTRAINT `compra_id_metodo_foreign` FOREIGN KEY(`id_metodo`) REFERENCES `metodo_pago`(`id_metodo`);
ALTER TABLE
    `mensaje` ADD CONSTRAINT `mensaje_id_moderador_foreign` FOREIGN KEY(`id_moderador`) REFERENCES `cuenta`(`id_cuenta`);