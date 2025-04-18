from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

class Priority(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name

# Create your models here.
class HELPForm(models.Model):
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    date_submitted = models.DateTimeField(auto_now_add=True, null=True)
    location = models.CharField(max_length=255, choices=[
        ('HQ_Lekki', 'HQ Lekki'),
        ('CGS_Ikorodu', 'CGS Ikorodu'),
        ('LNG_PH', 'LNG PH'),
        ('LFZ_Ibeju', 'LFZ Ibeju'),
    ], blank=True, null=True)

    category = models.ForeignKey(Category, on_delete=models.SET_NULL, blank=True, null=True)


    issue = models.CharField(max_length=255, choices=[
        ('IT', 'IT Support'),
    ], blank=True, null=True)

    priority = models.ForeignKey(Priority, on_delete=models.SET_NULL, blank=True, null=True)


    subject = models.CharField(max_length=255, null=True)
    complaint = models.TextField(null=True)
    attachment = models.FileField(upload_to='attachments/', null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('Closed', 'Closed'),
        ],
        default='pending',
    )

    def __str__(self):
        return self.name
