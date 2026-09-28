from django.urls import path

from . import views

app_name = 'pagos'

urlpatterns = [
    path('paypal/<int:pedido_id>/crear-orden/', views.crear_orden, name='crear_orden'),
    path('paypal/<int:pedido_id>/capturar-orden/', views.capturar_orden, name='capturar_orden'),
]
