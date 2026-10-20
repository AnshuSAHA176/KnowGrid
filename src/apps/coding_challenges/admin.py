from django.contrib import admin
from .models import CodingChallenge,TestCase,Submission

admin.site.register(CodingChallenge)
admin.site.register(TestCase)
admin.site.register(Submission)