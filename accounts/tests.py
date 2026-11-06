from django.test import TestCase
from django.urls import reverse
from .models import User

class RegistrationTests(TestCase):
    def test_public_registration_cannot_assign_operator_role(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser', 'email': 'new@example.com', 'display_name': 'New User',
            'password1': 'Strong-Test-Password-2026!', 'password2': 'Strong-Test-Password-2026!',
            'role': 'OPERATOR',
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='newuser')
        self.assertEqual(user.role, User.Role.USER)
