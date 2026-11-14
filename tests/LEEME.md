# Pruebas unitarias de Bejeweled (pytest)

## Cómo ejecutarlas
```
pip install -r requirements-dev.txt
pytest                      # todas
pytest tests/test_carrito.py -v
pytest -k tu13              # una prueba concreta (TU-13)
```
No tocan tu base de datos, tu caché ni servicios reales (Gmail, PayPal, Gemini, API de
inventario): `joyeria/settings_test.py` usa SQLite en memoria, caché en memoria y correo en memoria,
y `conftest.py` bloquea cualquier petición HTTP real.

## Nomenclatura
- `test_tuNN_*`  → tu plan de 40 pruebas (TU-01 … TU-40). Las variantes llevan letra: `tu13b`, `tu13c`…
- `test_exNN_*`  → pruebas extra encontradas al revisar el código.

## Pruebas `xfail` (brechas reales que las pruebas detectaron)
Están marcadas `xfail(strict=True)`: la suite queda en verde hoy, y cuando corrijas el código la
prueba empezará a "pasar inesperadamente" y te avisará para que quites la marca.

| Prueba | Brecha |
|---|---|
| TU-07 | `Producto.precio` acepta precios negativos (falta `MinValueValidator`). |
| TU-36 | `crear_resena` no verifica la compra: un POST directo publica reseña sin haber comprado. |
| TU-36d | Solo pedidos en estado `pagado` permiten reseñar; al pasar a enviado/entregado se pierde el permiso. |
| EX-21 | `siguiente` se pasa directo a `redirect()` (open redirect) en newsletter, favoritos e idioma. |

## Dónde el código difiere de la descripción del plan
- TU-13: el carrito **limita** la cantidad al stock (no lanza error).
- TU-19: no existe una máquina de estados; se prueba el estado inválido y que los pagos solo operen sobre `pendiente_pago`.
- TU-20: no hay cancelación manual; se prueba la cancelación automática del checkout y la reposición de stock.
- TU-08: en SQLite `full_clean()` no valida el mínimo de `PositiveIntegerField`; se prueba el formulario y la restricción de la BD.
