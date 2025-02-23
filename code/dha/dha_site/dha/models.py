import logging
import os
import subprocess
import random
import string

from django.db import models
from django.conf import settings

from .utils.functions import remove_docker_container, get_container_status
import docker

class User(models.Model):
    username = models.CharField(max_length=100, unique=True)

    # directory where volumes for the instance(s) will be mounted
    directory = models.CharField(max_length=255)

    @classmethod
    def create(cls, username=None):
        # generate new username
        while True:
            if username and not cls.objects.filter(username=username).exists():
                break
            
            username = "user_" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

        try:
            # create user with no shell / login
            subprocess.run(
                ["sudo", "useradd", "-M", "-r", "-s", "/usr/sbin/nologin", username],
                check=True
            )

            # create directories for the logs, config and data
            directory = os.path.join(settings.INSTANCE_USERS_DIRECTORY, username)
            directories = [ os.path.join( directory, f ) for f in ["logs", "config", "data"] ]

            for _directory in directories:
                os.makedirs(_directory, exist_ok=True)

        except subprocess.CalledProcessError as e:
            logging.error(f"Error creating new user: {e}")
            raise Exception(f"Failed to create user: {e}")
        
        try:
            subprocess.run(
                ["sudo", "chown", "-R", f"{username}:{username}", directory],
                check=True
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to set folder ownsership to {username}. Error: {e}")

            # delete user and delete folder
            subprocess.run(
                ["sudo", "userdel", "-r", username],
                check=True
            )
            subprocess.run(
                ["rm", "-r", directory]
            )
            raise Exception(f"Failed to set folder ownership: {e}")
        
        user = cls.objects.create(username=username, directory=directory)

        return user
    
    def delete(self, using = ..., keep_parents = ...):
        try:
            subprocess.run(
                ["sudo", "userdel", "-r", "username"]
            )
        except subprocess.CalledProcessError as e:
            logging.error("Error deleting a user and their folder")
            raise Exception(f"Failed to delete the user")
        
        # delete directory that was created
        subprocess.run(
            ["sudo", "rm", "-r", self.directory]
        )
        return super().delete(using, keep_parents)

    def get_directory(self, _dir):
        _dir = _dir.lower()
        if _dir not in ["logs", "data", "config"]:
            raise ValueError("_dir argument must either be logs, data or config")

        return os.path.join(self.directory, _dir)

class Network(models.Model):
    name = models.CharField(max_length=255, unique=True)  # Network name
    cidr = models.CharField(max_length=50, null=True)  # CIDR notation for the network
    driver = models.CharField(
        max_length=50,
        choices=[
            ('bridge', 'Bridge'),
            ('overlay', 'Overlay'),
            ('host', 'Host'),
            ('macvlan', 'MacVLAN'),
            ('none', 'None')
        ],
        default='bridge'  # Default driver
    )  # Network driver type
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp for creation
    
    def __str__(self):
        return f"{self.name} ({self.driver})"
    
    @classmethod
    def create(cls, network_name=None):

        if not network_name:
            network_name = "network_" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
            
        try:
            subprocess.run(
                ["docker", "network", "create", "--driver", "bridge", "--internal", network_name],
                check=True
            )
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to create Docker network: {e}")
            raise Exception(f"Failed to create Docker network: {e}")
        
        network = cls.objects.create(name=network_name, cidr="255.255.255.0", driver="bridge")

        return network
    
    def delete(self, *args, **kwargs):
        try:
            result = subprocess.run(
                ["docker", "network", "rm", self.name],
                check=True,
                capture_output=True,
                text=True
            )
            logging.info(f"Successfully deleted network, output: {result}")
        except subprocess.CalledProcessError as e:
            logging.error(f"Failed to delete docker network")
            raise e

        return super().delete(using, keep_parents)

class Instance(models.Model):
    name = models.CharField(max_length=255, unique=True)  # Name of the container
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp for creation
    status = models.CharField(max_length=50, choices=[  # Status of the container
        ('running', 'Running'),
        ('stopped', 'Stopped'),
        ('paused', 'Paused'),
        ('created', "Created")
    ])
    
    network: Network = models.ForeignKey('Network', on_delete=models.SET_NULL, null=True, blank=True, related_name='instances')  # Attached network
    user: User = models.ForeignKey('User', on_delete=models.CASCADE, related_name='instances')  # Owner of the instance
    image_name = models.CharField(max_length=100, default=settings.DEFAULT_BASE_IMAGE)

    http_host_port = models.IntegerField()
    https_host_port = models.IntegerField(null=True)
    ssh_host_port = models.IntegerField(null=True)
    
    detach = models.BooleanField(default=True)
    ssh_access = models.BooleanField(default=False)
    https_access = models.BooleanField(default=True)

    # directory where volumes for this instance will be mounted
    directory = models.CharField(max_length=255)

    def __str__(self):
        return self.name

    def get_status(self):
        client = docker.from_env()
        try:
            status = get_container_status(self.name)

            self.status = status
            self.save()

            return {
                "status": status
            }
        except docker.errors.NotFound as e:
            raise e
    
    def stop(self):
        client = docker.from_env()

        try:
            container = client.containers.get(self.name)
            container.stop()
        except docker.errors.NotFound as e:
            raise e

    def delete(self, using = ..., keep_parents = ...):
        print("In models.py, deleting an instance object")
        try:
            self.network.delete()
            self.volume.delete()
        except subprocess.CalledProcessError:
            logging.error("There was an issue deleting the network and the volume")
            raise Exception("There was an issue deleting the network and the volume")
        
        try:
            # delete docker container
            remove_docker_container(self.name)

            # delete DB record
            super().delete(using=using, keep_parents=keep_parents)

            # delete the system user if it has no more instances associated to it
            if not self.user.instances.count():
                self.user.delete()

        except subprocess.CalledProcessError:
            logging.error("There was an issue deleting the docker container")
            raise Exception("There was an issue deleting the docker container")

        # return super().delete(using, keep_parents)
    
# TODO work on volume mount point
class Volume(models.Model):
    name = models.CharField(max_length=255) 
    mount_point = models.CharField(max_length=255, null=True)
    mount_type = models.CharField(
        max_length=2,
        choices=[
            ('ro', 'Read-Only'),
            ('rw', 'Read-Write')
        ],
        default='rw'  # Default to read-write
    ) 
    attached_instance = models.ForeignKey(
        'Instance',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='volumes',
    )  # Attached container

    def __str__(self):
        return f"{self.name} ({self.mount_type})"

    @classmethod
    def generate_random_volume_name(cls):
        return "volume_" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

    @classmethod
    def create(cls, instance=None, mount_point=None, name=None):
        name = cls.generate_random_volume_name() if not name else name
        volume = cls.objects.create(name=name, attached_instance=instance, mount_point=mount_point)

        return volume
    
    def delete(self, using = ..., keep_parents = ...):
        # TODO: delete docker volume that was created

        return super().delete(using, keep_parents)
