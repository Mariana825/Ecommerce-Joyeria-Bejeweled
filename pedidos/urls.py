from django.urls import path

from . import views

app_name = 'pedidos'

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('<int:pedido_id>/pago-pendiente/', views.pago_pendiente, name='pago_pendiente'),
    path('<int:pedido_id>/', views.detalle_pedido, name='detalle'),
]
