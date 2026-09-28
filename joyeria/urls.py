from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('cuenta/', include('usuarios.urls')),
    path('carrito/', include('carrito.urls')),
    path('pedidos/', include('pedidos.urls')),
    path('pagos/', include('pagos.urls')),
    path('chatbot/', include('chatbot.urls')),
    path('idioma/', include('traduccion.urls')),
    path('api/inventario/', include('inventario.urls')),
    path('', include('productos.urls')),  # catálogo como home
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)