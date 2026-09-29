from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=128)
    slug = models.SlugField(max_length=256)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        return super().save(*args, **kwargs)


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products', null=True)
    name = models.CharField(max_length=128)
    description = models.TextField(max_length=256, blank=True, null=True)
    price = models.IntegerField()
    stock = models.BigIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
