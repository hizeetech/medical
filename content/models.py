from django.db import models
from ckeditor.fields import RichTextField

class CarePage(models.Model):
    SLUG_CHOICES = (
        ('antenatal', 'Antenatal Care'),
        ('postnatal', 'Postnatal Care'),
        ('immunization', 'Newborn Immunization'),
    )

    slug = models.SlugField(max_length=50, unique=True, choices=SLUG_CHOICES)
    title = models.CharField(max_length=200)
    body = RichTextField(blank=True)
    hero_image = models.ImageField(upload_to='care_pages/', blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Care Page'
        verbose_name_plural = 'Care Pages'
        ordering = ['slug']

    def __str__(self) -> str:
        return f"{self.get_slug_display()}"

class HomePage(models.Model):
    hero_title = models.CharField(max_length=200, blank=True)
    hero_subtitle = models.TextField(blank=True)
    hero_image = models.ImageField(upload_to='home/', blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Home Page'
        verbose_name_plural = 'Home Pages'

    def __str__(self) -> str:
        return self.hero_title or 'Home Page'
