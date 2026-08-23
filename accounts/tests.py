from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class RegistrationFlowTests(TestCase):
    def test_registration_disabled(self):
        """Public registration is removed; the endpoint must not exist."""
        response = self.client.post("/accounts/register/", {"username": "newstudent"})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(User.objects.filter(username="newstudent").exists())

    def test_registration_requires_unique_email(self):
        User.objects.create_user(username="existing", email="dup@example.com", password="x")
        response = self.client.get("/accounts/register/")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(User.objects.filter(username="existing").exists())


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="student", email="student@example.com", password="secret1234")
        self.user.role = User.Role.STUDENT
        self.user.is_active = True
        self.user.is_email_verified = True
        self.user.save()

    def test_login_success_redirects_to_dashboard(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "student", "password": "secret1234"},
        )
        self.assertRedirects(response, reverse("core:dashboard"))
        response = self.client.get(reverse("core:dashboard"))
        self.assertTrue(response.context["user"].is_authenticated)

    def test_login_wrong_password_shows_error(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "student", "password": "wrongpass"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct")

    def test_anonymous_redirected_from_dashboard(self):
        response = self.client.get(reverse("core:dashboard"))
        expected = f"{reverse('accounts:login')}?next={reverse('core:dashboard')}"
        self.assertRedirects(response, expected)

    def test_lockout_after_repeated_failures(self):
        login_url = reverse("accounts:login")
        for _ in range(5):
            self.client.post(login_url, {"username": "student", "password": "wrong"})
        response = self.client.post(login_url, {"username": "student", "password": "secret1234"})
        self.assertEqual(response.status_code, 429)

    def test_remember_me_keeps_persistent_session(self):
        self.client.post(
            reverse("accounts:login"),
            {"username": "student", "password": "secret1234", "remember": True},
        )
        self.assertFalse(self.client.session.get_expire_at_browser_close())

    def test_without_remember_me_session_dies_on_browser_close(self):
        self.client.post(reverse("accounts:login"), {"username": "student", "password": "secret1234"})
        self.assertTrue(self.client.session.get_expire_at_browser_close())


class PasswordTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="student", email="student@example.com", password="secret1234")
        self.user.role = User.Role.STUDENT
        self.user.is_active = True
        self.user.is_email_verified = True
        self.user.save()
        self.client.post(reverse("accounts:login"), {"username": "student", "password": "secret1234"})

    def test_password_change(self):
        response = self.client.post(
            reverse("accounts:password_change"),
            {"old_password": "secret1234", "new_password1": "NewPass123!", "new_password2": "NewPass123!"},
        )
        self.assertRedirects(response, reverse("accounts:password_change_done"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass123!"))

    def test_password_reset_sends_email(self):
        response = self.client.post(reverse("accounts:password_reset"), {"email": "student@example.com"})
        self.assertRedirects(response, reverse("accounts:password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
