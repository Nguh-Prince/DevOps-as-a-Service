from django.db import models
from django.contrib.auth.models import User

class Server(models.Model):
    hostname = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.hostname} {'active' if self.active else 'inactive'}"

class Instance(models.Model):
    name = models.CharField(max_length=100, unique=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    state = models.CharField(max_length=20, null=True)
    host_port = models.IntegerField()
    server = models.ForeignKey(Server, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    instance_id = models.IntegerField(null=True)