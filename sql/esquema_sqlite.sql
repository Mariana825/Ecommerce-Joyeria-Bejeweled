-- ============================================================
--  E-commerce de Joyas — Esquema de base de datos (SQLite)
--  Equivalente al esquema que generan las migraciones de Django
--  para las apps: usuarios, productos, carrito, pedidos.
--
--  NOTA: las tablas de Django (auth_user, auth_group, django_session,
--  django_migrations, etc.) las crea automáticamente `manage.py migrate`.
--  Aquí solo se incluye auth_user de forma resumida porque el resto de
--  las tablas del proyecto dependen de ella mediante llaves foráneas.
--
--  El carrito NO tiene tabla: se almacena en la sesión del usuario
--  (django_session), por eso no aparece aquí.
-- ============================================================

PRAGMA foreign_keys = ON;

-- ------------------------------------------------------------
-- Tabla de usuarios de Django (referencia)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS "auth_user" (
    "id"            INTEGER  NOT NULL PRIMARY KEY AUTOINCREMENT,
    "password"      VARCHAR(128) NOT NULL,
    "last_login"    DATETIME NULL,
    "is_superuser"  BOOL     NOT NULL,
    "username"      VARCHAR(150) NOT NULL UNIQUE,
    "first_name"    VARCHAR(150) NOT NULL,
    "last_name"     VARCHAR(150) NOT NULL,
    "email"         VARCHAR(254) NOT NULL,
    "is_staff"      BOOL     NOT NULL,
    "is_active"     BOOL     NOT NULL,
    "date_joined"   DATETIME NOT NULL
);


-- ============================================================
--  APP: usuarios
-- ============================================================

-- Perfil: datos adicionales del usuario (relación 1 a 1 con auth_user)
CREATE TABLE "usuarios_perfil" (
    "id"                INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "telefono"          VARCHAR(20)  NOT NULL,
    "fecha_nacimiento"  DATE         NULL,
    "avatar"            VARCHAR(100) NULL,
    "creado"            DATETIME     NOT NULL,
    "actualizado"       DATETIME     NOT NULL,
    "usuario_id"        INTEGER      NOT NULL UNIQUE
        REFERENCES "auth_user" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
);


-- Direcciones de envío guardadas por el usuario
CREATE TABLE "usuarios_direccionenvio" (
    "id"                 INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "etiqueta"           VARCHAR(50)  NOT NULL,
    "destinatario"       VARCHAR(150) NOT NULL,
    "calle"              VARCHAR(200) NOT NULL,
    "numero"             VARCHAR(20)  NOT NULL,
    "colonia"            VARCHAR(120) NOT NULL,
    "ciudad"             VARCHAR(100) NOT NULL,
    "estado"             VARCHAR(100) NOT NULL,
    "codigo_postal"      VARCHAR(20)  NOT NULL,
    "pais"               VARCHAR(100) NOT NULL DEFAULT 'México',
    "telefono_contacto"  VARCHAR(20)  NOT NULL,
    "predeterminada"     BOOL         NOT NULL DEFAULT 0,
    "creado"             DATETIME     NOT NULL,
    "usuario_id"         INTEGER      NOT NULL
        REFERENCES "auth_user" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX "usuarios_direccionenvio_usuario_id_idx"
    ON "usuarios_direccionenvio" ("usuario_id");


-- ============================================================
--  APP: productos
-- ============================================================

-- Categorías de joyas (anillos, collares, pulseras, aretes, ...)
CREATE TABLE "productos_categoria" (
    "id"           INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "nombre"       VARCHAR(100) NOT NULL UNIQUE,
    "slug"         VARCHAR(120) NOT NULL UNIQUE,
    "descripcion"  TEXT         NOT NULL,
    "imagen"       VARCHAR(100) NULL,
    "activa"       BOOL         NOT NULL DEFAULT 1
);

CREATE INDEX "productos_categoria_slug_idx" ON "productos_categoria" ("slug");


-- Materiales (oro 18k, plata 925, acero inoxidable, ...)
CREATE TABLE "productos_material" (
    "id"      INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "nombre"  VARCHAR(100) NOT NULL UNIQUE
);


-- Colecciones curadas (Colección Dorada, Elegancia en Plata, ...)
CREATE TABLE "productos_coleccion" (
    "id"            INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "nombre"        VARCHAR(120) NOT NULL UNIQUE,
    "slug"          VARCHAR(140) NOT NULL UNIQUE,
    "descripcion"   TEXT         NOT NULL,
    "imagen"        VARCHAR(100) NULL,
    "color_acento"  VARCHAR(7)   NOT NULL DEFAULT '#C9A84C',
    "activa"        BOOL         NOT NULL DEFAULT 1,
    "orden"         INTEGER      NOT NULL DEFAULT 0
                    CHECK ("orden" >= 0)
);


-- Productos (joyas del catálogo)
CREATE TABLE "productos_producto" (
    "id"                INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "nombre"            VARCHAR(200) NOT NULL,
    "slug"              VARCHAR(220) NOT NULL UNIQUE,
    "descripcion"       TEXT         NOT NULL,
    "precio"            DECIMAL(10, 2) NOT NULL,
    "existencias"       INTEGER      NOT NULL DEFAULT 0
                        CHECK ("existencias" >= 0),
    "imagen_principal"  VARCHAR(100) NULL,
    "activo"            BOOL         NOT NULL DEFAULT 1,
    "destacado"         BOOL         NOT NULL DEFAULT 0,
    "es_nuevo"          BOOL         NOT NULL DEFAULT 0,
    "creado"            DATETIME     NOT NULL,
    "actualizado"       DATETIME     NOT NULL,
    "categoria_id"      INTEGER      NULL
        REFERENCES "productos_categoria" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED,
    "material_id"       INTEGER      NULL
        REFERENCES "productos_material" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED,
    "coleccion_id"      INTEGER      NULL
        REFERENCES "productos_coleccion" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX "productos_producto_categoria_id_idx" ON "productos_producto" ("categoria_id");
CREATE INDEX "productos_producto_material_id_idx"  ON "productos_producto" ("material_id");
CREATE INDEX "productos_producto_slug_idx"         ON "productos_producto" ("slug");


-- Imágenes adicionales de la galería de cada producto
CREATE TABLE "productos_imagenproducto" (
    "id"           INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "imagen"       VARCHAR(100) NOT NULL,
    "orden"        INTEGER      NOT NULL DEFAULT 0
                   CHECK ("orden" >= 0),
    "producto_id"  INTEGER      NOT NULL
        REFERENCES "productos_producto" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX "productos_imagenproducto_producto_id_idx"
    ON "productos_imagenproducto" ("producto_id");

CREATE INDEX "productos_producto_coleccion_id_idx" ON "productos_producto" ("coleccion_id");


-- Reseñas con calificación de 1 a 5 estrellas.
-- Un usuario solo puede reseñar cada producto una vez.
CREATE TABLE "productos_resena" (
    "id"            INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "calificacion"  SMALLINT  NOT NULL
                    CHECK ("calificacion" >= 1 AND "calificacion" <= 5),
    "comentario"    TEXT      NOT NULL,
    "aprobada"      BOOL      NOT NULL DEFAULT 1,
    "creada"        DATETIME  NOT NULL,
    "producto_id"   INTEGER   NOT NULL
        REFERENCES "productos_producto" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
    "usuario_id"    INTEGER   NOT NULL
        REFERENCES "auth_user" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "resena_unica_por_usuario" UNIQUE ("producto_id", "usuario_id")
);

CREATE INDEX "productos_resena_producto_id_idx" ON "productos_resena" ("producto_id");
CREATE INDEX "productos_resena_usuario_id_idx"  ON "productos_resena" ("usuario_id");


-- Lista de deseos: productos marcados como favoritos por cada usuario.
CREATE TABLE "productos_favorito" (
    "id"           INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "creado"       DATETIME NOT NULL,
    "usuario_id"   INTEGER  NOT NULL
        REFERENCES "auth_user" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
    "producto_id"  INTEGER  NOT NULL
        REFERENCES "productos_producto" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT "favorito_unico_por_usuario" UNIQUE ("usuario_id", "producto_id")
);

CREATE INDEX "productos_favorito_usuario_id_idx"  ON "productos_favorito" ("usuario_id");
CREATE INDEX "productos_favorito_producto_id_idx" ON "productos_favorito" ("producto_id");


-- Suscriptores al boletín (formulario del pie de página).
CREATE TABLE "productos_suscriptor" (
    "id"      INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "email"   VARCHAR(254) NOT NULL UNIQUE,
    "activo"  BOOL         NOT NULL DEFAULT 1,
    "creado"  DATETIME     NOT NULL
);


-- ============================================================
--  APP: pedidos
-- ============================================================

-- Pedido: guarda una copia de los datos de envío al momento de la compra,
-- por si la dirección original se edita o se elimina después.
--
-- Columna "estado": pendiente_pago | pagado | en_proceso | enviado |
--                   entregado | cancelado
--
-- Las columnas "metodo_pago" y "referencia_pago" quedan vacías por ahora;
-- se llenarán cuando se integre la API de PayPal.
CREATE TABLE "pedidos_pedido" (
    "id"                   INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "nombre_destinatario"  VARCHAR(150) NOT NULL,
    "calle"                VARCHAR(200) NOT NULL,
    "numero"               VARCHAR(20)  NOT NULL,
    "colonia"              VARCHAR(120) NOT NULL,
    "ciudad"               VARCHAR(100) NOT NULL,
    "estado_direccion"     VARCHAR(100) NOT NULL,
    "codigo_postal"        VARCHAR(20)  NOT NULL,
    "pais"                 VARCHAR(100) NOT NULL,
    "telefono_contacto"    VARCHAR(20)  NOT NULL,
    "estado"               VARCHAR(20)  NOT NULL DEFAULT 'pendiente_pago',
    "metodo_pago"          VARCHAR(50)  NOT NULL DEFAULT '',
    "referencia_pago"      VARCHAR(100) NOT NULL DEFAULT '',
    "creado"               DATETIME     NOT NULL,
    "actualizado"          DATETIME     NOT NULL,
    "usuario_id"           INTEGER      NULL
        REFERENCES "auth_user" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED,
    "direccion_envio_id"   INTEGER      NULL
        REFERENCES "usuarios_direccionenvio" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX "pedidos_pedido_usuario_id_idx"         ON "pedidos_pedido" ("usuario_id");
CREATE INDEX "pedidos_pedido_direccion_envio_id_idx" ON "pedidos_pedido" ("direccion_envio_id");
CREATE INDEX "pedidos_pedido_creado_idx"             ON "pedidos_pedido" ("creado");


-- Artículos que componen cada pedido.
-- Guarda copia del nombre y precio para que el histórico no cambie
-- si el producto se edita o se elimina del catálogo.
CREATE TABLE "pedidos_pedidoitem" (
    "id"               INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "nombre_producto"  VARCHAR(200) NOT NULL,
    "precio_unitario"  DECIMAL(10, 2) NOT NULL,
    "cantidad"         INTEGER      NOT NULL DEFAULT 1
                       CHECK ("cantidad" >= 0),
    "pedido_id"        INTEGER      NOT NULL
        REFERENCES "pedidos_pedido" ("id") ON DELETE CASCADE DEFERRABLE INITIALLY DEFERRED,
    "producto_id"      INTEGER      NULL
        REFERENCES "productos_producto" ("id") ON DELETE SET NULL DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX "pedidos_pedidoitem_pedido_id_idx"   ON "pedidos_pedidoitem" ("pedido_id");
CREATE INDEX "pedidos_pedidoitem_producto_id_idx" ON "pedidos_pedidoitem" ("producto_id");
