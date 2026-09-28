# Bejeweled — E-commerce de Joyas

Plataforma web de comercio electrónico para venta de joyas, construida con
Django, con el sistema de diseño Bejeweled (lila + oro, tipografías
Gilda Display y Raleway) e integraciones reales de PayPal, traducción
automática y un chatbot de atención con IA.

## Qué incluye

### Tienda
- **Landing page** con hero, banda de garantías, categorías, joyas destacadas,
  colecciones, sección del asistente IA y beneficios.
- **Catálogo** con búsqueda, filtros (categoría, material, rango de precio,
  solo disponibles), ordenamiento y paginación.
- **Detalle de producto** con galería, atributos, productos relacionados y reseñas.
- **Colecciones** curadas, con página propia por colección.
- **Favoritos** (lista de deseos) por usuario.
- **Reseñas** con calificación de 1 a 5 estrellas (una por usuario y producto).
- **Newsletter** — captura de suscriptores desde el pie de página.

### Cuenta
- Registro, login/logout, recuperación de contraseña.
- Edición de perfil, direcciones de envío, historial de pedidos.

### Compra y pagos
- Carrito basado en sesión (funciona sin iniciar sesión).
- Checkout que valida existencias, descuenta inventario y registra el pedido.
- **Pago con PayPal (Sandbox)** — botón real con el JS SDK de PayPal; crea y
  captura la orden a través de la API REST (Orders v2) y marca el pedido
  como pagado con su referencia de transacción.

### Traducción automática
- Selector ES/EN en el header (desktop y móvil).
- Traduce sobre la marcha, con la API de Google Cloud Translate: nombres y
  descripciones de productos, categorías, materiales, colecciones y los
  mensajes del sistema (confirmaciones, errores, avisos).
- Cada texto traducido se guarda en caché (30 días) para no volver a pedirlo
  a la API en cada visita.
- Si la API no está configurada o falla, se muestra el texto original en
  español — nunca rompe la página.

### Chatbot de atención (IA)
- Widget flotante en todas las páginas (burbuja + panel de chat).
- Responde dudas generales: categorías, materiales, cómo comprar, envíos,
  devoluciones, garantía, cuidado de las joyas.
- Usa la API de Gemini (Google) con el catálogo real (categorías,
  materiales, colecciones) como contexto, para no inventar productos, precios
  ni existencias.
- Responde en el idioma que el visitante eligió en el selector ES/EN.
- Guarda el historial por sesión (`chatbot.Conversacion` / `chatbot.Mensaje`),
  visible desde el panel administrativo.

### API de inventario (REST, HTTPS)
- API propia hecha con Django REST Framework — no es un mock: la usa la
  propia tienda para descontar existencias al confirmar una compra, en vez
  de modificar `producto.existencias` directamente en la base de datos.
- `GET /api/inventario/productos/` — stock de todo el catálogo.
- `GET /api/inventario/productos/<id>/` — stock de un producto.
- `POST /api/inventario/productos/<id>/ajustar/` — ajusta el stock con un
  delta (`cantidad`: negativo para una venta, positivo para reponer);
  responde `409` si no hay existencias suficientes. El ajuste es atómico
  (`select_for_update`) para que dos compras simultáneas del mismo producto
  no dejen el stock en negativo.
- `GET /api/inventario/movimientos/` — bitácora de cada cambio de stock
  (también visible, de solo lectura, en `/admin/inventario/`).
- Protegida con una API key propia (encabezado `X-API-Key`), no con sesión
  de usuario — así puede consumirla cualquier sistema, no solo un navegador.
- Se sirve por **HTTPS con certificado SSL** (ver la sección siguiente); el
  checkout, al llamarla, valida el certificado según
  `INVENTARIO_VERIFICAR_SSL`.
- Si la API falla a mitad de una compra con varios productos, el pedido se
  cancela y se revierte (compensa) el stock que ya se había descontado, en
  vez de dejar el inventario a medias.

### Administración
- Panel de Django (`/admin/`) para gestionar usuarios, productos, categorías,
  materiales, colecciones, reseñas, favoritos, suscriptores, pedidos, las
  conversaciones del chatbot y la bitácora de inventario.

## HTTPS con certificado SSL

El proyecto se sirve por HTTPS usando el comando `runsslserver` (propio,
ver la app `servidor_https/`), que genera automáticamente un certificado
autofirmado de desarrollo la primera vez que lo ejecutas — no hay que
generar nada a mano:

```bash
python manage.py runsslserver 0.0.0.0:8000
```

Abre `https://127.0.0.1:8000/` — el navegador va a advertir que el
certificado es autofirmado (es normal en desarrollo); acepta la excepción
para continuar.

**Importante:** a partir de esta versión, el checkout llama a la API de
inventario por HTTPS (`https://127.0.0.1:8000/api/inventario/...`), así que
el proyecto debe correrse con `runsslserver`, no con el `runserver` clásico
— si usas `runserver` (HTTP), la llamada a la API fallará y el checkout no
podrá completar la compra.

### Usar tu propio certificado (opcional)

Si prefieres generar tu propio certificado en vez del autofirmado que
`runsslserver` crea por defecto:

```bash
bash certs/generar_certificado.sh
python manage.py runsslserver --certificate certs/cert.pem --key certs/key.pem 0.0.0.0:8000
```

El script usa `openssl` para crear un certificado autofirmado válido por un
año. El archivo `.pem` y la llave privada nunca se suben a git (ver
`certs/.gitignore`) — cada quien genera los suyos.

En producción, reemplaza esto por un certificado real (Let's Encrypt, por
ejemplo) detrás de un proxy como Nginx, y activa `SECURE_SSL_REDIRECT`,
`SESSION_COOKIE_SECURE` y `CSRF_COOKIE_SECURE` en el `.env`.

## Instalación

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env          # y completa tus claves (ver abajo)

python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py poblar_bd    # datos de prueba (ver GUIA_PRUEBAS.md)
python manage.py instalar_modelos_traduccion   # una sola vez, descarga los modelos es<->en (necesita internet)

python manage.py runsslserver 0.0.0.0:8000     # HTTPS (obligatorio: ver "HTTPS con certificado SSL")
```

Tienda: `https://127.0.0.1:8000/` — Admin: `https://127.0.0.1:8000/admin/`

## Configurar las APIs externas

Copia `.env.example` como `.env` y completa lo que necesites. **El proyecto
funciona sin nada de esto configurado** — cada integración se apaga sola y
muestra un aviso si falta su clave (o su modelo), en vez de romper la
página.

| Integración | Cómo activarla | Dónde conseguirla |
|---|---|---|
| PayPal Sandbox | Completa `PAYPAL_CLIENT_ID` y `PAYPAL_CLIENT_SECRET` en `.env` | [developer.paypal.com/dashboard/applications/sandbox](https://developer.paypal.com/dashboard/applications/sandbox) — crea una app de tipo *Sandbox* |
| Traducción | Corre `python manage.py instalar_modelos_traduccion` (una sola vez) | Nada que conseguir: es el paquete `argostranslate`, 100% local y gratis — solo descarga los modelos es↔en la primera vez |
| Chatbot | Completa `GEMINI_API_KEY` en `.env` | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) — clave gratis de la API de Gemini |

Para probar el pago con PayPal necesitas una cuenta de **comprador de
prueba**, no tu cuenta real: se crean en
[developer.paypal.com/dashboard/accounts](https://developer.paypal.com/dashboard/accounts).

La **API de inventario** es distinta: es interna (la consume la propia
tienda, no un proveedor externo) y ya trae una `INVENTARIO_API_KEY` de
desarrollo por defecto, así que el checkout funciona sin tocar el `.env`.
Cámbiala por una clave propia (y guárdala solo en tu `.env`, nunca en el
código) antes de desplegar a producción.

## Estructura

```
joyeria/           configuración del proyecto (settings, urls)
usuarios/          perfil, direcciones de envío
productos/         catálogo, colecciones, reseñas, favoritos, newsletter
carrito/           carrito en sesión (sin modelos)
pedidos/           pedidos y artículos de pedido
pagos/             cliente de la API de PayPal + endpoints crear/capturar orden
traduccion/        servicio de traducción, filtro {% traducir %}, selector de idioma
chatbot/           servicio que llama a Gemini, endpoints del widget, historial
inventario/        API REST de stock (DRF) + cliente HTTP que usa el checkout
servidor_https/    comando `runsslserver` (HTTPS de desarrollo, certificado autofirmado)
templates/
  partials/        header, footer, tarjeta de producto, newsletter, IA, beneficios,
                    widget_chat
static/css/        style.css — sistema de diseño completo
sql/               esquema SQLite y MySQL + datos de ejemplo
certs/             script para generar un certificado SSL propio (opcional)
.env.example        plantilla de variables de entorno (copiar a .env)
```

## Sistema de diseño

Los tokens del diseño original (que usaba Tailwind) están portados a CSS plano
en `static/css/style.css`, porque el proyecto Django no tiene build de Tailwind.
Se conservan los mismos nombres de variables:

| Variable | Valor | Uso |
|---|---|---|
| `--primary` | `#8A74A8` | Lila principal, botones secundarios |
| `--lilac-deep` | `#6B5487` | Botones primarios, logo, header del chat |
| `--gold` | `#C9A84C` | Precios, acentos, CTA principal, burbuja de chat |
| `--background` | `#FDFBFF` | Fondo general |
| `--foreground` | `#1E1728` | Texto |
| `--muted` | `#F3EEF8` | Fondos de sección |
| `--beige` | `#F5F0E8` | Fondo del newsletter |

Tipografías: **Gilda Display** para títulos (`.font-display`, h1–h4) y
**Raleway** para el resto, cargadas desde Google Fonts.

## Notas

- Las imágenes de ejemplo del hero y de los productos sin foto apuntan a
  Unsplash. Al subir imágenes reales desde el admin, se usan esas.
- Antes de producción: cambia `DJANGO_SECRET_KEY` e `INVENTARIO_API_KEY`, pon
  `DJANGO_DEBUG=False`, configura `ALLOWED_HOSTS` y cambia `PAYPAL_MODE=live`
  con credenciales reales (no de sandbox).
- El caché de traducción y del token de PayPal usa el backend de caché por
  defecto de Django (memoria local). En producción con varios procesos
  conviene cambiar a Redis o Memcached para que el caché se comparta.
- Los scripts de `sql/` son para documentación y diagramas ER. En Django lo
  normal es dejar que `manage.py migrate` cree las tablas.
- En producción, no uses `runsslserver` (es solo para desarrollo): sirve la
  app con Gunicorn/uWSGI detrás de Nginx, con un certificado real (por
  ejemplo, de Let's Encrypt) terminando el TLS ahí.

## Datos de prueba

```bash
python manage.py poblar_bd            # llena la base con datos de prueba
python manage.py poblar_bd --limpiar  # borra y vuelve a llenar
```

Crea 20 productos, 4 colecciones, 5 categorías, 6 materiales, 1 usuario de
prueba (`mariana` / `joyeria2026`) con 2 direcciones, 6 favoritos, 6 reseñas,
1 pedido y 3 suscriptores.

Ver **GUIA_PRUEBAS.md** para el recorrido completo de pruebas, incluidas las
tres integraciones.
