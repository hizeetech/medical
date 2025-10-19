from django.shortcuts import render
from content.models import CarePage, HomePage


def home(request):
    homepage = HomePage.objects.first()
    return render(request, 'home.html', {'homepage': homepage})


def antenatal_care(request):
    page = CarePage.objects.filter(slug='antenatal').first()
    return render(request, 'content/antenatal_care.html', {'page': page})


def postnatal_care(request):
    page = CarePage.objects.filter(slug='postnatal').first()
    return render(request, 'content/postnatal_care.html', {'page': page})


def newborn_immunization(request):
    page = CarePage.objects.filter(slug='immunization').first()
    return render(request, 'content/newborn_immunization.html', {'page': page})


def find_doctor(request):
    return render(request, 'content/find_doctor.html')


def articles(request):
    return render(request, 'content/articles.html')