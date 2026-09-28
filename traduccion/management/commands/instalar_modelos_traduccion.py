"""
Descarga e instala los modelos de traducción es<->en de argos-translate.

Uso:
    python manage.py instalar_modelos_traduccion

Solo hace falta correrlo una vez (los modelos quedan guardados en el disco,
dentro del perfil de datos de argos-translate). Necesita conexión a
internet la primera vez, para bajar los archivos ".argosmodel" (unos 30-50
MB cada uno, desde el índice público de argosopentech). Una vez instalados,
la traducción del sitio funciona 100% local — ver traduccion/services.py.
"""

from django.core.management.base import BaseCommand, CommandError

PARES = [('es', 'en'), ('en', 'es')]


class Command(BaseCommand):
    help = 'Descarga e instala los modelos de traducción es<->en de argos-translate (una sola vez).'

    def handle(self, *args, **options):
        try:
            import argostranslate.package as at_package
            import argostranslate.translate as at_translate
        except ImportError as exc:
            raise CommandError(
                'Falta el paquete "argostranslate". Instala las dependencias '
                'con `pip install -r requirements.txt` y vuelve a intentar.'
            ) from exc

        def ya_instalado(origen, destino):
            idiomas = at_translate.get_installed_languages()
            lang_origen = next((i for i in idiomas if i.code == origen), None)
            lang_destino = next((i for i in idiomas if i.code == destino), None)
            return bool(lang_origen and lang_destino and lang_origen.get_translation(lang_destino))

        faltantes = [par for par in PARES if not ya_instalado(*par)]
        if not faltantes:
            self.stdout.write(self.style.SUCCESS('Los modelos es↔en ya estaban instalados. Nada que hacer.'))
            return

        self.stdout.write('Consultando el índice de paquetes de argos-translate...')
        try:
            at_package.update_package_index()
        except Exception as error:
            raise CommandError(
                'No se pudo descargar el índice de paquetes (¿hay conexión a '
                f'internet?): {error}'
            ) from error

        disponibles = at_package.get_available_packages()

        for origen, destino in faltantes:
            paquete = next(
                (p for p in disponibles if p.from_code == origen and p.to_code == destino),
                None,
            )
            if not paquete:
                self.stdout.write(self.style.WARNING(
                    f'  {origen} → {destino}: no se encontró en el índice de paquetes.'
                ))
                continue

            self.stdout.write(f'  Descargando e instalando {origen} → {destino}...')
            ruta_descargada = paquete.download()
            at_package.install_from_path(ruta_descargada)
            self.stdout.write(self.style.SUCCESS(f'  {origen} → {destino}: instalado.'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            'Listo. La traducción del sitio (selector ES/EN del header) ya '
            'funciona sin conexión a internet.'
        ))
