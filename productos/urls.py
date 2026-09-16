from django.urls import path

from . import views

app_name = 'productos'

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path('catalogo/', views.catalogo, name='catalogo'),
    path('producto/<slug:slug>/', views.detalle, name='detalle'),

    # Colecciones
    path('colecciones/', views.lista_colecciones, name='colecciones'),
    path('coleccion/<slug:slug>/', views.detalle_coleccion, name='coleccion'),

    # Favoritos
    path('favoritos/', views.mis_favoritos, name='favoritos'),
    path('favoritos/alternar/<int:producto_id>/', views.alternar_favorito, name='alternar_favorito'),

    # Reseñas
    path('resena/<int:producto_id>/', views.crear_resena, name='crear_resena'),

    # Newsletter
    path('newsletter/', views.suscribir_newsletter, name='newsletter'),
]
