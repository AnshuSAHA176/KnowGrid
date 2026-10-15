from django.contrib.auth.base_user import BaseUserManager


class CustomeUserManager(BaseUserManager):
    def create_user(self, email, password, **kwargs):

        if not email:
            raise ValueError("email is required")

        user = self.model(email=self.normalize_email(email), **kwargs)

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **kwargs):
        user = self.create_user(email=email, password=password, **kwargs)
        user.is_staff = True
        user.is_superuser = True

        user.save(using=self._db)
        return user
