# Guía de pruebas — Bejeweled

## 1. Levantar el proyecto

```bash
cd joyeria_ecommerce

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copia el archivo de variables de entorno y completa tus claves
# (opcional para lo básico; necesario para PayPal, traducción y el chatbot —
# ver la sección 5 de esta guía y el README).
cp .env.example .env

# Si ya tenías una base de datos de la versión anterior, bórrala:
# rm db.sqlite3    (Windows: del db.sqlite3)

python manage.py makemigrations
python manage.py migrate

# Superusuario para entrar al panel administrativo
python manage.py createsuperuser

# Llenar con datos de prueba
python manage.py poblar_bd

# Traducción ES/EN: descarga los modelos una sola vez (necesita internet
# esta vez; después la traducción funciona sin conexión)
python manage.py instalar_modelos_traduccion

# HTTPS: obligatorio a partir de esta versión (el checkout llama a la API
# de inventario por HTTPS). No uses "runserver" — usa runsslserver:
python manage.py runsslserver 0.0.0.0:8000
```

Abre `https://127.0.0.1:8000/`. El navegador va a mostrar una advertencia de
"conexión no privada" o "certificado no confiable" — es normal, es un
certificado autofirmado de desarrollo. Busca la opción "Avanzado" o
"Continuar de todos modos" y acepta la excepción una sola vez.

Al terminar, el comando imprime las credenciales del usuario de prueba.

## 2. Credenciales

| Rol | Usuario | Contraseña |
|---|---|---|
| Cliente de prueba | `mariana` | `joyeria2026` |
| Administrador | el que creaste con `createsuperuser` | la tuya |

## 3. Qué crea el script

- 5 categorías, 6 materiales, **4 colecciones**
- **20 productos** — 6 destacados, 6 marcados como nuevos, 2 agotados,
  4 sin colección (para probar ese caso)
- **1 usuario** con perfil, teléfono y 2 direcciones (una predeterminada)
- 6 favoritos y 6 reseñas de ese usuario (calificaciones de 3 a 5 estrellas)
- **1 pedido** con 3 artículos (total $2,550.00), en estado *pendiente de pago*
- 3 suscriptores al newsletter

Para empezar de cero y volver a llenar:

```bash
python manage.py poblar_bd --limpiar
```

## 4. Recorrido de prueba

### Sin iniciar sesión

| Qué probar | Dónde | Qué debe pasar |
|---|---|---|
| Landing | `/` | Hero, banda de garantías, 4 categorías, 4 destacados, 3 colecciones, sección IA, beneficios |
| Buscar | Lupa del header | Escribe "collar" → lleva al catálogo filtrado |
| Filtros | `/catalogo/` | Filtra por categoría, material, precio (ej: 500–2000) y "solo en stock" |
| Orden | `/catalogo/` | "Precio: mayor a menor" → la Pulsera Tenis ($18,400) queda primero |
| Paginación | `/catalogo/` | Con 20 productos hay 2 páginas; al pasar de página los filtros se conservan |
| Agotados | `/catalogo/` | "Collar Capas Doradas" y "Dije Inicial Oro" salen con etiqueta *Agotado* y sin botón de carrito |
| Detalle | Cualquier producto | Atributos, descripción, reseñas y relacionados |
| Colecciones | `/colecciones/` | 4 tarjetas, cada una con su color de acento distinto |
| Carrito anónimo | Agrega algo al carrito | El contador del header sube sin necesidad de login |
| Checkout sin login | `/pedidos/checkout/` | Te redirige a iniciar sesión |
| Newsletter | Pie de página | Suscríbete; repite el mismo correo → avisa que ya está registrado |
| Favoritos sin login | Tarjetas de producto | El corazón no aparece (solo para usuarios autenticados) |

### Con la sesión de `mariana`

| Qué probar | Dónde | Qué debe pasar |
|---|---|---|
| Favoritos | `/favoritos/` | Ya trae 6 piezas guardadas |
| Marcar/desmarcar | Corazón de una tarjeta | Se llena de dorado y te regresa a la misma página |
| Reseña nueva | Un producto sin reseñar | Publica con estrellas; el promedio del producto se actualiza |
| Reseña duplicada | El mismo producto otra vez | Muestra tu reseña en vez del formulario |
| Carrito | `/carrito/` | Cambia cantidades y elimina; el total se recalcula |
| Tope de stock | Pon cantidad mayor al stock | El carrito la ajusta al máximo disponible |
| Checkout | `/pedidos/checkout/` | Elige entre las 2 direcciones; la de "Casa" viene preseleccionada |
| Confirmar pedido | Botón confirmar | Crea el pedido, vacía el carrito y descuenta el inventario |
| Historial | `/cuenta/pedidos/` | Aparecen 2 pedidos (el del script y el tuyo) |
| Perfil | `/cuenta/perfil/` | Edita nombre y teléfono, guarda y recarga |
| Direcciones | `/cuenta/direcciones/` | Agrega una nueva marcándola predeterminada → la anterior se desmarca sola |

### Panel administrativo (`/admin/`)

- **Productos**: edita precio, existencias, activo, destacado y nuevo
  directamente desde la lista, sin abrir cada producto.
- Desactiva un producto (`activo = False`) y verifica que desaparezca de la tienda.
- Sube una imagen a una categoría (los 20 productos de prueba ya traen
  cada uno su propia imagen generada por `poblar_bd`; sube una nueva a
  cualquiera para confirmar que la reemplaza sin problema).
- **Reseñas**: desmarca "aprobada" y confirma que deja de mostrarse en la tienda.
- **Pedidos**: cambia el estado a "Pagado" y revisa el color de la etiqueta en el
  historial del cliente.
- **Suscriptores**: ahí están los 3 del script más los que agregues desde el pie.

### Diseño responsivo

Reduce la ventana a menos de 1024 px: la navegación se vuelve menú hamburguesa
y los filtros del catálogo pasan arriba de los productos. Abajo de 680 px, las
tablas del carrito se reacomodan en bloques.

## 5. Probar las integraciones con APIs

Estas tres funcionan de verdad, pero necesitan sus claves en `.env` (ver
README.md → "Configurar las APIs externas"). **Sin claves, el sitio sigue
funcionando** — cada una se apaga sola y muestra un aviso en vez de romperse.

### PayPal (Sandbox)

1. Configura `PAYPAL_CLIENT_ID` y `PAYPAL_CLIENT_SECRET` en `.env` (app tipo
   *Sandbox* en el dashboard de PayPal) y reinicia `runsslserver`.
2. Crea una **cuenta de comprador de prueba** en
   [developer.paypal.com/dashboard/accounts](https://developer.paypal.com/dashboard/accounts)
   si no tienes una.
3. Agrega algo al carrito → `/pedidos/checkout/` → confirma el pedido → en
   `/pedidos/<id>/pago-pendiente/` debe aparecer el botón amarillo de PayPal.
4. Págalo con la cuenta de prueba. Al aprobar, la página se recarga sola y
   muestra "¡Pago confirmado!" con la referencia de PayPal.
5. Verifica en `/admin/pedidos/pedido/` que el pedido quedó en estado
   **Pagado**, con `metodo_pago = PayPal (Sandbox)` y su `referencia_pago`.
6. Sin claves configuradas: la misma página muestra el aviso de "pago
   pendiente, no configurado" en vez del botón — no se rompe.

### Inventario (API propia, HTTPS)

Esta es interna: **no necesita ninguna clave externa**, ya funciona con la
`INVENTARIO_API_KEY` de desarrollo que trae `.env.example`.

1. Anota el stock actual de un producto desde `/admin/productos/producto/`
   (por ejemplo, "Anillo Trenzado Vienne" con 24 unidades).
2. Compra 2 unidades de ese producto (agrégalo al carrito → checkout →
   confirmar). El pedido debe registrarse normalmente.
3. Vuelve a `/admin/productos/producto/` — el stock debe haber bajado en 2
   (22 unidades), sin que hayas tocado el campo a mano: lo hizo la llamada a
   la API desde el checkout.
4. Revisa `/admin/inventario/movimientoinventario/` — debe aparecer un
   movimiento de tipo "Salida" por -2, con el motivo "Venta" y la referencia
   al número de tu pedido.
5. Prueba la API directamente desde la terminal (en otra ventana, con el
   servidor corriendo):
   ```bash
   curl -sk https://127.0.0.1:8000/api/inventario/productos/ \
        -H "X-API-Key: clave-interna-de-desarrollo-CAMBIAR-EN-PRODUCCION"
   ```
   (el flag `-k` le dice a `curl` que no valide el certificado autofirmado;
   usa la misma clave que tengas en tu `.env`). Debe regresar un JSON con
   todos los productos y su stock.
6. Prueba sin la clave, o con una incorrecta — debe regresar `403 Forbidden`:
   ```bash
   curl -sk https://127.0.0.1:8000/api/inventario/productos/
   ```
7. **Probar el caso de falla:** pon manualmente las existencias de un
   producto en 0 desde el admin, agrégalo al carrito (el catálogo no te
   dejará si ya está en 0, así que agrégalo antes de bajarlo, o baja las
   existencias de otro producto que ya tengas en el carrito) y confirma el
   pedido — debe mostrarte el error "Ya no hay existencias suficientes..." y
   el pedido debe quedar en estado **Cancelado** en el admin, sin haber
   tocado el stock de los demás artículos del mismo pedido (revisa la
   bitácora: por cada uno que sí se alcanzó a descontar, debe existir un
   segundo movimiento de compensación que lo regresa).

### Traducción automática

1. Corre `python manage.py instalar_modelos_traduccion` (descarga los
   modelos es↔en de `argostranslate` — solo la primera vez, necesita
   internet) y reinicia `runsslserver`.
2. En el header, toca **EN**. Recorre el catálogo: nombres y descripciones de
   producto, categorías, materiales y colecciones deben verse en inglés.
3. Provoca un mensaje del sistema (agrega algo al carrito, o intenta entrar
   a un checkout vacío) y confirma que el aviso también sale en inglés.
4. Vuelve a **ES** — todo regresa a español de inmediato (no hay que esperar
   otra traducción: ya quedó en caché la primera vez, y de cualquier forma
   la traducción es local, no depende de internet).
5. Sin los modelos instalados: el botón EN sigue ahí, pero el contenido se
   queda en español (el filtro regresa el texto original si falta el modelo
   o algo falla al traducir).

### Chatbot con IA

1. Configura `GEMINI_API_KEY` en `.env` y reinicia `runsslserver`.
2. Debe aparecer una burbuja dorada flotante abajo a la derecha en cualquier
   página. Ábrela y pregúntale, por ejemplo:
   - "¿Qué materiales manejan?"
   - "¿Cuánto tarda el envío?"
   - "¿Cómo compro algo?"
   - "¿Cuál es su política de devoluciones?"
3. Cambia el idioma a **EN** y pregunta de nuevo — el asistente debe
   responder en inglés.
4. Recarga la página con el chat abierto: el historial de esa conversación
   debe seguir ahí (se guarda por sesión).
5. Revisa `/admin/chatbot/conversacion/` — debe aparecer tu conversación con
   todos los mensajes, visibles como inline.
6. Sin clave configurada: no aparece la burbuja flotante, y en la sección
   "¿No sabes qué joya elegir?" del inicio el botón queda deshabilitado con
   un aviso.

## 6. Problemas comunes

| Error | Causa | Solución |
|---|---|---|
| `no such column: productos_producto.es_nuevo` | Base de datos de la versión anterior | Borra `db.sqlite3` y corre `makemigrations` + `migrate` otra vez |
| `NoReverseMatch: 'productos:inicio'` | Migraciones o URLs sin recargar | Reinicia `runsslserver` |
| Las imágenes no se ven al subirlas | `DEBUG = False` | En desarrollo debe estar en `True` para servir `/media/` |
| El comando `poblar_bd` no existe | Falta el `__init__.py` | Verifica que existan `productos/management/__init__.py` y `productos/management/commands/__init__.py` |
| Las fuentes se ven en Times New Roman | Sin internet | Gilda Display y Raleway se cargan desde Google Fonts |
| El botón de PayPal no aparece | Faltan las claves o el pedido ya está pagado | Revisa `PAYPAL_CLIENT_ID`/`SECRET` en `.env` y que el pedido siga en "Pendiente de pago" |
| PayPal responde error 401 | Credenciales incorrectas o mezcladas con las de producción | Verifica que sean las de la app **Sandbox**, no las de "Live" |
| El texto no se traduce | Falta correr `instalar_modelos_traduccion`, o no hubo internet la primera vez | Corre el comando y revisa los logs de la consola (`runsslserver`) — el filtro nunca rompe la página, solo deja el texto en español |
| No aparece la burbuja de chat | Falta `GEMINI_API_KEY` | Agrégala en `.env` y reinicia `runsslserver` |
| El chatbot responde "no está disponible" | La clave de Gemini es inválida o no tiene cuota | Revisa la clave en aistudio.google.com |
| "Advertencia de seguridad" al abrir el sitio | El certificado de `runsslserver` es autofirmado | Es normal en desarrollo — acepta la excepción en el navegador |
| El checkout falla con "No se pudo actualizar el inventario" | El proyecto corre con `runserver` en vez de `runsslserver` | Detén el servidor y levántalo con `python manage.py runsslserver 0.0.0.0:8000` |
| La API de inventario responde `403 Forbidden` | Falta el encabezado `X-API-Key`, o no coincide con `INVENTARIO_API_KEY` del `.env` | Revisa que el valor sea exactamente el mismo en ambos lados |
| La API de inventario responde `409 Conflict` | Ya no hay existencias suficientes para esa cantidad | Es el comportamiento esperado — así evita vender de más |

