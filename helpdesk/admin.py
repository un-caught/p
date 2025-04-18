from django.contrib import admin
from .models import Category, Priority

# Register your models here.

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')  # Customize this as needed

@admin.register(Priority)
class PriorityAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')  # Customize this as needed

