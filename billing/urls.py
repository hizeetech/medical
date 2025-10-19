from django.urls import path
from .views import invoice_list, invoice_new

urlpatterns = [
    path('', invoice_list, name='invoice_list'),
    path('new/<int:patient_id>/', invoice_new, name='invoice_new'),
]