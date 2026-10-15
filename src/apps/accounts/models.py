from django.db import models
from django.contrib.auth.base_user import AbstractBaseUser
from .custome_user_manager import CustomeUserManager
from django.contrib.auth.models import PermissionsMixin

class User(AbstractBaseUser,PermissionsMixin):

    class RoleChoices(models.TextChoices):
        USER = "user", "User"
        BOSS = "boss", "Boss"

    objects = CustomeUserManager()
    email = models.EmailField(unique=True, max_length=300)
    user_name = None
    role = models.CharField(max_length=200,choices=RoleChoices.choices,default=RoleChoices.USER)
    REQUIRED_FIELDS = []
    USERNAME_FIELD = "email"
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.email}"
