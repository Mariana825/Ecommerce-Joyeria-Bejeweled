-- ============================================================
--  Datos de ejemplo para probar el catálogo
--  Compatible con SQLite y MySQL.
--
--  Ejecutar DESPUÉS de crear el esquema (o después de `manage.py migrate`).
--  No incluye usuarios ni pedidos: conviene crearlos desde la aplicación
--  para que las contraseñas queden correctamente encriptadas.
-- ============================================================

-- --- Categorías ---
INSERT INTO productos_categoria (nombre, slug, descripcion, activa) VALUES
('Anillos',  'anillos',  'Anillos de compromiso, de boda y de uso diario.', 1),
('Collares', 'collares', 'Collares y gargantillas en distintos materiales.', 1),
('Pulseras', 'pulseras', 'Pulseras finas y de eslabones.', 1),
('Aretes',   'aretes',   'Aretes de broquel, argollas y colgantes.', 1),
('Dijes',    'dijes',    'Dijes y charms para personalizar tus joyas.', 1);


-- --- Materiales ---
INSERT INTO productos_material (nombre) VALUES
('Oro 18k'),
('Oro 14k'),
('Oro blanco'),
('Plata 925'),
('Acero inoxidable'),
('Chapa de oro');


-- --- Colecciones ---
INSERT INTO productos_coleccion (nombre, slug, descripcion, color_acento, activa, orden) VALUES
('Colección Dorada', 'coleccion-dorada',
 'Piezas bañadas en oro 18K para quienes aprecian el lujo sin concesiones.', '#C9A84C', 1, 1),
('Elegancia en Plata', 'elegancia-en-plata',
 'Diseños contemporáneos en plata esterlina 925. Sutileza redefinida.', '#A8AAAD', 1, 2),
('Regalos Especiales', 'regalos-especiales',
 'Curada con amor para momentos que merecen ser recordados eternamente.', '#8A74A8', 1, 3);


-- --- Productos ---
-- Los IDs de categoría y material siguen el orden de inserción anterior:
--   categorías: 1=Anillos, 2=Collares, 3=Pulseras, 4=Aretes, 5=Dijes
--   materiales: 1=Oro 18k, 2=Oro 14k, 3=Oro blanco, 4=Plata 925,
--               5=Acero inoxidable, 6=Chapa de oro
-- colecciones: 1=Dorada, 2=Plata, 3=Regalos
INSERT INTO productos_producto
    (nombre, slug, categoria_id, material_id, coleccion_id, descripcion, precio,
     existencias, imagen_principal, activo, destacado, es_nuevo, creado, actualizado)
VALUES
('Anillo solitario clásico', 'anillo-solitario-clasico', 1, 1, 1,
 'Anillo solitario en oro de 18 quilates con acabado pulido. Diseño atemporal ideal para compromiso.',
 8500.00, 5, NULL, 1, 1, 0, '2026-09-01 10:00:00', '2026-09-01 10:00:00'),

('Anillo de plata trenzado', 'anillo-de-plata-trenzado', 1, 4, 2,
 'Anillo de plata 925 con diseño trenzado, cómodo para uso diario.',
 890.00, 20, NULL, 1, 0, 1, '2026-09-01 10:05:00', '2026-09-01 10:05:00'),

('Collar cadena veneciana', 'collar-cadena-veneciana', 2, 2, 1,
 'Collar de oro 14k con tejido veneciano de 45 cm. Ligero y elegante.',
 6200.00, 8, NULL, 1, 1, 0, '2026-09-02 09:00:00', '2026-09-02 09:00:00'),

('Gargantilla minimalista', 'gargantilla-minimalista', 2, 4, 2,
 'Gargantilla de plata 925 con dije circular. Perfecta para combinar en capas.',
 1150.00, 15, NULL, 1, 0, 1, '2026-09-02 09:10:00', '2026-09-02 09:10:00'),

('Pulsera de eslabones', 'pulsera-de-eslabones', 3, 5, 3,
 'Pulsera de acero inoxidable resistente al agua, con broche de seguridad.',
 650.00, 30, NULL, 1, 0, 0, '2026-09-03 11:00:00', '2026-09-03 11:00:00'),

('Pulsera tenis', 'pulsera-tenis', 3, 3, 1,
 'Pulsera tenis en oro blanco con circonias de corte brillante.',
 12400.00, 3, NULL, 1, 1, 0, '2026-09-03 11:20:00', '2026-09-03 11:20:00'),

('Aretes de argolla pequeños', 'aretes-de-argolla-pequenos', 4, 6, 3,
 'Argollas de chapa de oro de 15 mm. Ligeras y cómodas para todo el día.',
 420.00, 40, NULL, 1, 0, 0, '2026-09-04 08:30:00', '2026-09-04 08:30:00'),

('Aretes broquel perla', 'aretes-broquel-perla', 4, 4, 2,
 'Broqueles de plata 925 con perla cultivada de agua dulce.',
 980.00, 12, NULL, 1, 0, 1, '2026-09-04 08:45:00', '2026-09-04 08:45:00'),

('Dije corazón grabable', 'dije-corazon-grabable', 5, 4, 3,
 'Dije de plata en forma de corazón, disponible para grabado personalizado.',
 560.00, 25, NULL, 1, 0, 0, '2026-09-05 12:00:00', '2026-09-05 12:00:00'),

('Dije inicial oro', 'dije-inicial-oro', 5, 2, 3,
 'Dije con letra inicial en oro 14k. Se vende por pieza.',
 2300.00, 0, NULL, 1, 0, 0, '2026-09-05 12:15:00', '2026-09-05 12:15:00');
