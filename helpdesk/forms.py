from django.contrib.auth.models import User
from django import forms
from .models import HELPForm, Category, Priority
from django.forms.widgets import ClearableFileInput

class HELPSubmissionForm(forms.ModelForm):
    class Meta:
        model = HELPForm
        fields = ['location', 'category', 'issue', 'priority', 'subject', 'complaint', 'attachment']

    location = forms.ChoiceField(choices=[
        ('HQ_Lekki', 'HQ - Lekki'),
        ('CGS_Ikorodu', 'CGS - Ikorodu'),
        ('LNG_PH', 'LNG - PH'),
        ('LFZ_Ibeju', 'LFZ - Ibeju'),
    ], widget=forms.Select(attrs={'class': 'form-select'}))   

    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    issue = forms.ChoiceField(choices=[
        ('IT', 'IT Support'),
    ], widget=forms.Select(attrs={'class': 'form-select'}))

    priority = forms.ModelChoiceField(
        queryset=Priority.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )     

    subject = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Subject of the compaint here'}))

    complaint = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}))
    attachment = forms.FileField(widget=forms.ClearableFileInput(attrs={'class': 'form-control'}), required=False)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']  # We only need the 'name' field for category creation
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter category name'}),
        }


class PriorityForm(forms.ModelForm):
    class Meta:
        model = Priority
        fields = ['name']  # We only need the 'name' field for category creation
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter priority level'}),
        }