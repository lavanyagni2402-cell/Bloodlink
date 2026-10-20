from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    # pages
    path("", views.home, name="home"),
    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="core/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("profile/", views.profile_edit, name="profile_edit"),
    path("requests/", views.request_list, name="request_list"),
    path("requests/new/", views.request_create, name="request_create"),
    path("requests/<int:pk>/", views.request_detail, name="request_detail"),
    path("requests/<int:pk>/status/", views.request_set_status, name="request_set_status"),
    path("responses/<int:pk>/status/", views.response_set_status, name="response_set_status"),
    path("donors/", views.find_donors, name="find_donors"),

    # JSON API (called by jQuery and AngularJS)
    path("api/stats/", views.api_stats, name="api_stats"),
    path("api/requests/", views.api_requests, name="api_requests"),
    path("api/requests/<int:pk>/respond/", views.api_respond, name="api_respond"),
    path("api/donors/", views.api_donors, name="api_donors"),
    path("api/availability/", views.api_toggle_availability, name="api_toggle_availability"),
]
