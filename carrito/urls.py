from django.urls import path

from . import views

app_name = 'carrito'

urlpatterns = [
    path('', views.ver_carrito, name='ver_carrito'),
    path('agregar/<int:producto_id>/', views.agregar, name='agregar'),
    path('actualizar/<int:producto_id>/', views.actualizar, name='actualizar'),
    path('eliminar/<int:producto_id>/', views.eliminar, name='eliminar'),
]
