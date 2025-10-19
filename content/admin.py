from django.contrib import admin
from django import forms
from ckeditor.widgets import CKEditorWidget

from .models import CarePage, HomePage

class CarePageAdminForm(forms.ModelForm):
    class Meta:
        model = CarePage
        fields = '__all__'
        widgets = {
            'body': CKEditorWidget(),
        }

@admin.register(CarePage)
class CarePageAdmin(admin.ModelAdmin):
    form = CarePageAdminForm
    list_display = ('slug', 'title', 'updated_at')
    list_filter = ('slug',)
    search_fields = ('title',)
    ordering = ('slug',)

@admin.register(HomePage)
class HomePageAdmin(admin.ModelAdmin):
    list_display = ('hero_title', 'updated_at')
    search_fields = ('hero_title',)
    ordering = ('-updated_at',)
