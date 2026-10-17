CREATE DATABASE IF NOT EXISTS tienda_juegos
  DEFAULT CHARACTER SET utf8mb4;
USE tienda_juegos;

CREATE TABLE rol (
  id_rol INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(50) NOT NULL,
  descripcion VARCHAR(255) NOT NULL,
  CONSTRAINT uq_rol_nombre UNIQUE (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE empresa (
  id_empresa INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  tipo ENUM('desarrollador','distribuidor','ambos') NOT NULL,
  pais VARCHAR(60) NOT NULL,
  email_contacto VARCHAR(150) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE categoria (
  id_categoria INT AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(60) NOT NULL,
  descripcion TEXT NOT NULL,
  CONSTRAINT uq_categoria_nombre UNIQUE (nombre)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE cuenta (
  id_cuenta INT AUTO_INCREMENT PRIMARY KEY,
  nick VARCHAR(50) NOT NULL,
  email VARCHAR(150) NOT NULL,
  telefono VARCHAR(20) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  nombre VARCHAR(80) NOT NULL,
  apellidos VARCHAR(120) NOT NULL,
  fecha_nacimiento DATE NOT NULL,
  pais VARCHAR(60) NOT NULL,
  ip_registro VARCHAR(45) NOT NULL,
  fecha_registro DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  estado ENUM('activa','suspendida','baja') NOT NULL DEFAULT 'activa',
  id_rol INT NOT NULL,
  id_empresa INT NULL,
  CONSTRAINT uq_cuenta_nick UNIQUE (nick),
  CONSTRAINT uq_cuenta_email UNIQUE (email),
  CONSTRAINT fk_cuenta_rol FOREIGN KEY (id_rol) REFERENCES rol(id_rol)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_cuenta_empresa FOREIGN KEY (id_empresa) REFERENCES empresa(id_empresa)
    ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE juego (
  id_juego INT AUTO_INCREMENT PRIMARY KEY,
  titulo VARCHAR(150) NOT NULL,
  descripcion TEXT NOT NULL,
  precio DECIMAL(8,2) NOT NULL,
  clasificacion_edad TINYINT NOT NULL,
  fecha_lanzamiento DATE NOT NULL,
  id_categoria INT NOT NULL,
  id_desarrollador INT NOT NULL,
  id_distribuidor INT NOT NULL,
  CONSTRAINT chk_juego_precio CHECK (precio >= 0),
  CONSTRAINT chk_juego_clasificacion CHECK (clasificacion_edad IN (3,7,12,16,18)),
  CONSTRAINT fk_juego_categoria FOREIGN KEY (id_categoria) REFERENCES categoria(id_categoria)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_juego_desarrollador FOREIGN KEY (id_desarrollador) REFERENCES empresa(id_empresa)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_juego_distribuidor FOREIGN KEY (id_distribuidor) REFERENCES empresa(id_empresa)
    ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE biblioteca (
  id_cuenta INT NOT NULL,
  id_juego INT NOT NULL,
  fecha_adquisicion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  clave_activacion VARCHAR(50) NOT NULL,
  horas_jugadas DECIMAL(8,1) NOT NULL DEFAULT 0,
  PRIMARY KEY (id_cuenta, id_juego),
  CONSTRAINT uq_biblioteca_clave UNIQUE (clave_activacion),
  CONSTRAINT chk_biblioteca_horas CHECK (horas_jugadas >= 0),
  CONSTRAINT fk_biblioteca_cuenta FOREIGN KEY (id_cuenta) REFERENCES cuenta(id_cuenta)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_biblioteca_juego FOREIGN KEY (id_juego) REFERENCES juego(id_juego)
    ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE metodo_pago (
  id_metodo INT AUTO_INCREMENT PRIMARY KEY,
  id_cuenta INT NOT NULL,
  tipo ENUM('tarjeta','IBAN','otro') NOT NULL,
  titular VARCHAR(150) NOT NULL,
  numero VARCHAR(255) NOT NULL,
  caducidad VARCHAR(10) NOT NULL,
  direccion_facturacion VARCHAR(255) NOT NULL,
  fecha_alta DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_metodo_pago_cuenta FOREIGN KEY (id_cuenta) REFERENCES cuenta(id_cuenta)
    ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE objeto_ingame (
  id_objeto INT AUTO_INCREMENT PRIMARY KEY,
  id_juego INT NOT NULL,
  nombre VARCHAR(100) NOT NULL,
  tipo VARCHAR(50) NOT NULL,
  rareza ENUM('comun','poco_comun','raro','epico','legendario') NOT NULL,
  precio DECIMAL(8,2) NOT NULL,
  CONSTRAINT chk_objeto_precio CHECK (precio >= 0),
  CONSTRAINT fk_objeto_juego FOREIGN KEY (id_juego) REFERENCES juego(id_juego)
    ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE inventario (
  id_cuenta INT NOT NULL,
  id_objeto INT NOT NULL,
  cantidad INT NOT NULL DEFAULT 1,
  fecha_obtencion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id_cuenta, id_objeto),
  CONSTRAINT chk_inventario_cantidad CHECK (cantidad >= 0),
  CONSTRAINT fk_inventario_cuenta FOREIGN KEY (id_cuenta) REFERENCES cuenta(id_cuenta)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_inventario_objeto FOREIGN KEY (id_objeto) REFERENCES objeto_ingame(id_objeto)
    ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE compra (
  id_compra INT AUTO_INCREMENT PRIMARY KEY,
  id_cuenta INT NOT NULL,
  id_metodo INT NOT NULL,
  id_juego INT NULL,
  id_objeto INT NULL,
  importe DECIMAL(8,2) NOT NULL,
  fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  estado ENUM('pendiente','completada','reembolsada','fallida') NOT NULL,
  numero_factura VARCHAR(30) NOT NULL,
  ip_origen VARCHAR(45) NOT NULL,
  CONSTRAINT uq_compra_factura UNIQUE (numero_factura),
  CONSTRAINT chk_compra_importe CHECK (importe >= 0),
  CONSTRAINT chk_compra_un_producto CHECK (
    (id_juego IS NOT NULL AND id_objeto IS NULL) OR
    (id_juego IS NULL AND id_objeto IS NOT NULL)
  ),
  CONSTRAINT fk_compra_cuenta FOREIGN KEY (id_cuenta) REFERENCES cuenta(id_cuenta)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_compra_metodo FOREIGN KEY (id_metodo) REFERENCES metodo_pago(id_metodo)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_compra_juego FOREIGN KEY (id_juego) REFERENCES juego(id_juego)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_compra_objeto FOREIGN KEY (id_objeto) REFERENCES objeto_ingame(id_objeto)
    ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE mensaje (
  id_mensaje INT AUTO_INCREMENT PRIMARY KEY,
  id_emisor INT NOT NULL,
  id_receptor INT NOT NULL,
  texto TEXT NOT NULL,
  fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  estado ENUM('normal','eliminado') NOT NULL DEFAULT 'normal',
  id_moderador INT NULL,
  CONSTRAINT chk_mensaje_no_propio CHECK (id_emisor <> id_receptor),
  CONSTRAINT fk_mensaje_emisor FOREIGN KEY (id_emisor) REFERENCES cuenta(id_cuenta)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_mensaje_receptor FOREIGN KEY (id_receptor) REFERENCES cuenta(id_cuenta)
    ON DELETE RESTRICT ON UPDATE RESTRICT,
  CONSTRAINT fk_mensaje_moderador FOREIGN KEY (id_moderador) REFERENCES cuenta(id_cuenta)
    ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
