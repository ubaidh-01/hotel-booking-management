from django.urls import path
from . import views
from .views import (
    HomeView, RoomListView, RoomDetailView, AboutView, ContactView,
    ContactThanksView, CareersView, CareersThanksView, TermsView,
    PrivacyView, SubmitFeedbackView, FeedbackThanksView
)

app_name = 'website'

urlpatterns = [
    # Public Pages
    path('', HomeView.as_view(), name='home'),
    path('rooms/', RoomListView.as_view(), name='room_list'),
    path('rooms/<str:room_code>/', RoomDetailView.as_view(), name='room_detail'),
    path('about/', AboutView.as_view(), name='about'),
    path('contact/', ContactView.as_view(), name='contact'),
    path('contact/thanks/', ContactThanksView.as_view(), name='contact_thanks'),
    path('careers/', CareersView.as_view(), name='careers'),
    path('careers/thanks/', CareersThanksView.as_view(), name='careers_thanks'),
    path('terms/', TermsView.as_view(), name='terms'),
    path('privacy/', PrivacyView.as_view(), name='privacy'),
    path('feedback/', SubmitFeedbackView.as_view(), name='submit_feedback'),
    path('feedback/thanks/', FeedbackThanksView.as_view(), name='feedback_thanks'),

    # Tenant Portal
    path('tenant/dashboard/', views.tenant_dashboard, name='tenant_dashboard'),
    path('tenant/booking/<int:booking_id>/', views.tenant_booking_detail, name='tenant_booking_detail'),
    path('tenant/payments/', views.tenant_payments, name='tenant_payments'),
    path('tenant/maintenance/', views.tenant_maintenance, name='tenant_maintenance'),
    path('tenant/contract/<int:contract_id>/', views.tenant_contract_view, name='tenant_contract_view'),

    # Booking Flow
    path('book/<str:room_code>/', views.start_booking, name='start_booking'),
    path('booking/<int:booking_id>/payment/', views.booking_payment, name='booking_payment'),
    path('payment/<int:payment_id>/proof/', views.payment_proof_upload, name='payment_proof_upload'),
    path('booking/<int:booking_id>/confirmation/', views.booking_confirmation, name='booking_confirmation'),
]