"""api URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import include, path
from api.urls import api_urls
from dj_rest_auth.views import PasswordResetConfirmView
from api.resources.authuser import NewEmailConfirmation
from dj_rest_auth.registration.views import VerifyEmailView, ConfirmEmailView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("v1/", include(api_urls), name="api-root"),
    path(
        "api-sessionauth/", include("rest_framework.urls", namespace="rest_framework")
    ),
    path("rest-auth/", include("dj_rest_auth.urls")),
    path(
        "rest-auth/registration/resend-verification-email/",
        NewEmailConfirmation.as_view(),
        name="resend-email-confirmation",
    ),
    path("rest-auth/registration/", include("dj_rest_auth.registration.urls")),
    path(
        "rest-auth/account-confirm-email/",
        VerifyEmailView.as_view(),
        name="account_email_verification_sent",
    ),
    path(
        "rest-auth/password/reset/confirm/<slug:uidb64>/<slug:token>/",
        PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
]
