from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    PermissionsMixin,
    BaseUserManager,
)
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import uuid


class UserManager(BaseUserManager):

    def create_user(self, name, email, password):
        if not email:
            raise ValueError("Users must have an email")
        if not name:
            raise ValueError("Users must have a name")
        if not password:
            raise ValueError("Users must have a password")

        try:
            validate_password(password)
        except ValidationError as e:
            raise ValueError(f"Invalid password: {e.message}")

        user = self.model(email=self.normalize_email(email), name=name)
        validate_password(password=password)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, name, password):
        if not email:
            raise ValueError("Users must have an email")
        if not password:
            raise ValueError("Users must have a password")

        user = self.model(email=self.normalize_email(email), name=name)
        user.set_password(password)
        user.is_staff, user.is_admin, user.is_superuser = True, True
        user.save()
        return user


class User(AbstractBaseUser):

    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    email = models.EmailField(unique=True, blank=False)
    name = models.CharField(max_length=100, blank=False)
    is_staff = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        ordering = ["name"]
        
    def __str__(self) -> str:
        return f"{self.name}"
