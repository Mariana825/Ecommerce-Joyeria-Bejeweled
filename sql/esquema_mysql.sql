-- ============================================================
--  E-commerce de Joyas — Esquema de base de datos (MySQL / MariaDB)
--
--  Misma estructura que el esquema de SQLite, adaptada a MySQL por si
--  el proyecto se migra a este motor. El carrito no tiene tabla: vive
--  en la sesión del usuario (tabla django_session).
--
--  Para usar MySQL en Django habría que instalar `mysqlclient` y cambiar
--  ENGINE a 'django.db.backends.mysql' en joyeria/settings.py.
-- ============================================================

CREATE DATABASE IF NOT EXISTS joyeria_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE joyeria_db;


-- ------------------------------------------------------------
-- Tabla de usuarios de Django (referencia)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth_user (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    password      VARCHAR(128) NOT NULL,
    last_login    DATETIME     NULL,
    is_superuser  TINYINT(1)   NOT NULL DEFAULT 0,
    username      VARCHAR(150) NOT NULL UNIQUE,
    first_name    VARCHAR(150) NOT NULL DEFAULT '',
    last_name     VARCHAR(150) NOT NULL DEFAULT '',
    email         VARCHAR(254) NOT NULL DEFAULT '',
    is_staff      TINYINT(1)   NOT NULL DEFAULT 0,
    is_active     TINYINT(1)   NOT NULL DEFAULT 1,
    date_joined   DATETIME     NOT NULL
) ENGINE=InnoDB;


-- ============================================================
--  APP: usuarios
-- ============================================================

CREATE TABLE usuarios_perfil (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id        INT          NOT NULL UNIQUE,
    telefono          VARCHAR(20)  NOT NULL DEFAULT '',
    fecha_nacimiento  DATE         NULL,
    avatar            VARCHAR(100) NULL,
    creado            DATETIME     NOT NULL,
    actualizado       DATETIME     NOT NULL,
    CONSTRAINT fk_perfil_usuario FOREIGN KEY (usuario_id)
        REFERENCES auth_user (id) ON DELETE CASCADE
) ENGINE=InnoDB;


CREATE TABLE usuarios_direccionenvio (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id         INT          NOT NULL,
    etiqueta           VARCHAR(50)  NOT NULL DEFAULT '',
    destinatario       VARCHAR(150) NOT NULL,
    calle              VARCHAR(200) NOT NULL,
    numero             VARCHAR(20)  NOT NULL DEFAULT '',
    colonia            VARCHAR(120) NOT NULL DEFAULT '',
    ciudad             VARCHAR(100) NOT NULL,
    estado             VARCHAR(100) NOT NULL,
    codigo_postal      VARCHAR(20)  NOT NULL,
    pais               VARCHAR(100) NOT NULL DEFAULT 'México',
    telefono_contacto  VARCHAR(20)  NOT NULL DEFAULT '',
    predeterminada     TINYINT(1)   NOT NULL DEFAULT 0,
    creado             DATETIME     NOT NULL,
    INDEX idx_direccion_usuario (usuario_id),
    CONSTRAINT fk_direccion_usuario FOREIGN KEY (usuario_id)
        REFERENCES auth_user (id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- ============================================================
--  APP: productos
-- ============================================================

CREATE TABLE productos_categoria (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    nombre       VARCHAR(100) NOT NULL UNIQUE,
    slug         VARCHAR(120) NOT NULL UNIQUE,
    descripcion  TEXT         NOT NULL,
    imagen       VARCHAR(100) NULL,
    activa       TINYINT(1)   NOT NULL DEFAULT 1,
    INDEX idx_categoria_slug (slug)
) ENGINE=InnoDB;


CREATE TABLE productos_material (
    id      INT AUTO_INCREMENT PRIMARY KEY,
    nombre  VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;


CREATE TABLE productos_coleccion (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    nombre        VARCHAR(120) NOT NULL UNIQUE,
    slug          VARCHAR(140) NOT NULL UNIQUE,
    descripcion   TEXT         NOT NULL,
    imagen        VARCHAR(100) NULL,
    color_acento  VARCHAR(7)   NOT NULL DEFAULT '#C9A84C',
    activa        TINYINT(1)   NOT NULL DEFAULT 1,
    orden         INT UNSIGNED NOT NULL DEFAULT 0
) ENGINE=InnoDB;


CREATE TABLE productos_producto (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    nombre            VARCHAR(200) NOT NULL,
    slug              VARCHAR(220) NOT NULL UNIQUE,
    categoria_id      INT          NULL,
    material_id       INT          NULL,
    coleccion_id      INT          NULL,
    descripcion       TEXT         NOT NULL,
    precio            DECIMAL(10,2) NOT NULL,
    existencias       INT UNSIGNED NOT NULL DEFAULT 0,
    imagen_principal  VARCHAR(100) NULL,
    activo            TINYINT(1)   NOT NULL DEFAULT 1,
    destacado         TINYINT(1)   NOT NULL DEFAULT 0,
    es_nuevo          TINYINT(1)   NOT NULL DEFAULT 0,
    creado            DATETIME     NOT NULL,
    actualizado       DATETIME     NOT NULL,
    INDEX idx_producto_categoria (categoria_id),
    INDEX idx_producto_material (material_id),
    INDEX idx_producto_coleccion (coleccion_id),
    INDEX idx_producto_slug (slug),
    CONSTRAINT fk_producto_categoria FOREIGN KEY (categoria_id)
        REFERENCES productos_categoria (id) ON DELETE SET NULL,
    CONSTRAINT fk_producto_material FOREIGN KEY (material_id)
        REFERENCES productos_material (id) ON DELETE SET NULL,
    CONSTRAINT fk_producto_coleccion FOREIGN KEY (coleccion_id)
        REFERENCES productos_coleccion (id) ON DELETE SET NULL
) ENGINE=InnoDB;


CREATE TABLE productos_imagenproducto (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    producto_id  INT          NOT NULL,
    imagen       VARCHAR(100) NOT NULL,
    orden        INT UNSIGNED NOT NULL DEFAULT 0,
    INDEX idx_imagen_producto (producto_id),
    CONSTRAINT fk_imagen_producto FOREIGN KEY (producto_id)
        REFERENCES productos_producto (id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- Reseñas con calificación de 1 a 5 estrellas
CREATE TABLE productos_resena (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    producto_id   INT       NOT NULL,
    usuario_id    INT       NOT NULL,
    calificacion  TINYINT UNSIGNED NOT NULL,
    comentario    TEXT      NOT NULL,
    aprobada      TINYINT(1) NOT NULL DEFAULT 1,
    creada        DATETIME  NOT NULL,
    UNIQUE KEY resena_unica_por_usuario (producto_id, usuario_id),
    INDEX idx_resena_producto (producto_id),
    INDEX idx_resena_usuario (usuario_id),
    CONSTRAINT chk_calificacion CHECK (calificacion BETWEEN 1 AND 5),
    CONSTRAINT fk_resena_producto FOREIGN KEY (producto_id)
        REFERENCES productos_producto (id) ON DELETE CASCADE,
    CONSTRAINT fk_resena_usuario FOREIGN KEY (usuario_id)
        REFERENCES auth_user (id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- Lista de deseos
CREATE TABLE productos_favorito (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id   INT      NOT NULL,
    producto_id  INT      NOT NULL,
    creado       DATETIME NOT NULL,
    UNIQUE KEY favorito_unico_por_usuario (usuario_id, producto_id),
    INDEX idx_favorito_usuario (usuario_id),
    INDEX idx_favorito_producto (producto_id),
    CONSTRAINT fk_favorito_usuario FOREIGN KEY (usuario_id)
        REFERENCES auth_user (id) ON DELETE CASCADE,
    CONSTRAINT fk_favorito_producto FOREIGN KEY (producto_id)
        REFERENCES productos_producto (id) ON DELETE CASCADE
) ENGINE=InnoDB;


-- Suscriptores al boletín
CREATE TABLE productos_suscriptor (
    id      INT AUTO_INCREMENT PRIMARY KEY,
    email   VARCHAR(254) NOT NULL UNIQUE,
    activo  TINYINT(1)   NOT NULL DEFAULT 1,
    creado  DATETIME     NOT NULL
) ENGINE=InnoDB;


-- ============================================================
--  APP: pedidos
-- ============================================================

CREATE TABLE pedidos_pedido (
    id                   INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id           INT          NULL,
    direccion_envio_id   INT          NULL,
    nombre_destinatario  VARCHAR(150) NOT NULL,
    calle                VARCHAR(200) NOT NULL,
    numero               VARCHAR(20)  NOT NULL DEFAULT '',
    colonia              VARCHAR(120) NOT NULL DEFAULT '',
    ciudad               VARCHAR(100) NOT NULL,
    estado_direccion     VARCHAR(100) NOT NULL,
    codigo_postal        VARCHAR(20)  NOT NULL,
    pais                 VARCHAR(100) NOT NULL,
    telefono_contacto    VARCHAR(20)  NOT NULL DEFAULT '',
    estado               VARCHAR(20)  NOT NULL DEFAULT 'pendiente_pago',
    metodo_pago          VARCHAR(50)  NOT NULL DEFAULT '',
    referencia_pago      VARCHAR(100) NOT NULL DEFAULT '',
    creado               DATETIME     NOT NULL,
    actualizado          DATETIME     NOT NULL,
    INDEX idx_pedido_usuario (usuario_id),
    INDEX idx_pedido_direccion (direccion_envio_id),
    INDEX idx_pedido_creado (creado),
    CONSTRAINT fk_pedido_usuario FOREIGN KEY (usuario_id)
        REFERENCES auth_user (id) ON DELETE SET NULL,
    CONSTRAINT fk_pedido_direccion FOREIGN KEY (direccion_envio_id)
        REFERENCES usuarios_direccionenvio (id) ON DELETE SET NULL
) ENGINE=InnoDB;


CREATE TABLE pedidos_pedidoitem (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    pedido_id        INT          NOT NULL,
    producto_id      INT          NULL,
    nombre_producto  VARCHAR(200) NOT NULL,
    precio_unitario  DECIMAL(10,2) NOT NULL,
    cantidad         INT UNSIGNED NOT NULL DEFAULT 1,
    INDEX idx_item_pedido (pedido_id),
    INDEX idx_item_producto (producto_id),
    CONSTRAINT fk_item_pedido FOREIGN KEY (pedido_id)
        REFERENCES pedidos_pedido (id) ON DELETE CASCADE,
    CONSTRAINT fk_item_producto FOREIGN KEY (producto_id)
        REFERENCES productos_producto (id) ON DELETE SET NULL
) ENGINE=InnoDB;
