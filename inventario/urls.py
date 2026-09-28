from django.urls import path

from . import views

app_name = 'inventario'

urlpatterns = [
    path('productos/', views.ProductoStockListView.as_view(), name='lista_stock'),
    path('productos/<int:pk>/', views.ProductoStockDetailView.as_view(), name='detalle_stock'),
    path('productos/<int:pk>/ajustar/', views.AjustarStockView.as_view(), name='ajustar_stock'),
    path('movimientos/', views.MovimientosListView.as_view(), name='movimientos'),
]
