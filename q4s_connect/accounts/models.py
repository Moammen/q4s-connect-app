from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ("engineer", "Engineer"),
        ("admin",    "Admin"),
        ("operator", "Operator"),
        ("user",     "User"),
    ]

    role      = models.CharField(max_length=20, choices=ROLE_CHOICES)
    all_sites = models.BooleanField(default=False)
    ets_sites = models.ManyToManyField("core.ETSSite", blank=True)
    is_deleted         = models.BooleanField(default=False)

