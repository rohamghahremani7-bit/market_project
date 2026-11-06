from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        USER = 'USER', 'کاربر'
        OPERATOR = 'OPERATOR', 'اپراتور'
        ADMIN = 'ADMIN', 'مدیر'
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.USER, db_index=True)
    display_name = models.CharField(max_length=120, blank=True)
    bio = models.TextField(blank=True, max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_operator(self):
        return self.is_superuser or self.is_staff or self.role in {self.Role.OPERATOR, self.Role.ADMIN}

    @property
    def is_admin_role(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    def save(self, *args, **kwargs):
        previous_role = None
        if self.pk and not self.is_superuser:
            previous_role = type(self).objects.filter(pk=self.pk).values_list('role', flat=True).first()
        if self.role == self.Role.ADMIN:
            self.is_staff = True  # نقش مدیر به پنل Django Admin نیز دسترسی دارد.
        elif previous_role == self.Role.ADMIN and not self.is_superuser:
            self.is_staff = False
        super().save(*args, **kwargs)

    def has_perm(self, perm, obj=None):
        if self.is_active and self.is_admin_role:
            return True
        return super().has_perm(perm, obj)

    def has_module_perms(self, app_label):
        if self.is_active and self.is_admin_role:
            return True
        return super().has_module_perms(app_label)

    def __str__(self):
        return self.display_name or self.username
