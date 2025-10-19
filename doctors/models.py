from accounts.models import User

class Doctor(User):
    class Meta:
        proxy = True
        verbose_name = "Doctor"
        verbose_name_plural = "Doctors"
