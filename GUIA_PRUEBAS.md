# Guía de pruebas — Bejeweled

## 1. Levantar el proyecto

```bash
cd joyeria_ecommerce

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Si ya tenías una base de datos de la versión anterior, bórrala:
# rm db.sqlite3    (Windows: del db.sqlite3)

python manage.py makemigrations
python manage.py migrate

# Superusuario para entrar al panel administrativo
python manage.py createsuperuser

# Llenar con datos de prueba
python manage.py poblar_bd

python manage.py runserver
```

Al terminar, el comando imprime las credenciales del usuario de prueba.

## 2. Credenciales

| Rol | Usuario | Contraseña |
|---|---|---|
| Cliente de prueba | `mariana` | `joyeria2026` |
| Administrador | admin | 1234 | admin@test.com

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
- Sube una imagen a un producto y a una categoría; reemplaza la imagen de respaldo.
- **Reseñas**: desmarca "aprobada" y confirma que deja de mostrarse en la tienda.
- **Pedidos**: cambia el estado a "Pagado" y revisa el color de la etiqueta en el
  historial del cliente.
- **Suscriptores**: ahí están los 3 del script más los que agregues desde el pie.

### Diseño responsivo

Reduce la ventana a menos de 1024 px: la navegación se vuelve menú hamburguesa
y los filtros del catálogo pasan arriba de los productos. Abajo de 680 px, las
tablas del carrito se reacomodan en bloques.

## 5. Lo que todavía NO funciona (pendiente)

Estas tres cosas están diseñadas pero sin conectar, porque las dejamos para la
siguiente etapa:

- **PayPal** — el pedido se queda en "pendiente de pago"; no hay cobro real.
- **Chatbot de IA** — la sección del inicio tiene el botón deshabilitado.
- **Traducción automática** — no hay selector de idioma en el header.

## 6. Problemas comunes

| Error | Causa | Solución |
|---|---|---|
| `no such column: productos_producto.es_nuevo` | Base de datos de la versión anterior | Borra `db.sqlite3` y corre `makemigrations` + `migrate` otra vez |
| `NoReverseMatch: 'productos:inicio'` | Migraciones o URLs sin recargar | Reinicia `runserver` |
| Las imágenes no se ven al subirlas | `DEBUG = False` | En desarrollo debe estar en `True` para servir `/media/` |
| El comando `poblar_bd` no existe | Falta el `__init__.py` | Verifica que existan `productos/management/__init__.py` y `productos/management/commands/__init__.py` |
| Las fuentes se ven en Times New Roman | Sin internet | Gilda Display y Raleway se cargan desde Google Fonts |
