from django.urls import path

from accounts import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("verify-pending/", views.VerifyPendingView.as_view(), name="verify-pending"),
    path("verify/resend/", views.ResendVerificationView.as_view(), name="verify-resend"),
    path("verify/<str:token>/", views.VerifyEmailView.as_view(), name="verify-email"),
    path("forgot-password/", views.ForgotPasswordView.as_view(), name="forgot-password"),
    path("reset-password/<str:token>/", views.ResetPasswordView.as_view(), name="reset-password"),
]
