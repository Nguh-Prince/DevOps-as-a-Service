import os
import subprocess
import random
import string

from django.conf import settings
from django.db.models import Q

from rest_framework import serializers

from .models import *
from .utils.functions import slugify

class CreateInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instance
        fields = ["name", "http_host_port", "https_host_port"]
        extra_kwargs = { 
            "http_host_port": { "required": False }, 
            "https_host_port": { "required": False } 
        }

    def validate(self, attrs):
        port_keys = ["http_host_port", "https_host_port"]

        for port_key in port_keys:
            if port_key not in attrs:
                # generate random port number
                while True:
                    port = random.randint(1024, 65535)

                    # break if port has not already been assigned
                    if not Instance.objects.filter(
                        Q(http_host_port=port) | Q(https_host_port=port) | Q(ssh_host_port=port)
                    ):
                        break
                
                attrs[port_key] = port
            else:
                # check if the key has been assigned already
                port = attrs[port_key]
                if Instance.objects.filter(
                        Q(http_host_port=port) | Q(https_host_port=port) | Q(ssh_host_port=port)
                    ):
                        raise serializers.ValidationError(f"{port_key} already assigned to another instance")

        return super().validate(attrs)

    def validate_name(self, value):
        return slugify(value)

    def create(self, validated_data):
        try:
            # create user
            user = User.create()

            # create network
            network = Network.create()

            volume = Volume.create()
        except Exception as e:
            user.delete()
            network.delete()
            raise e
        
        try:
            subprocess.run(
                [
                    "docker", "run", "-d", 
                    "--name", validated_data['name'],
                    "--network", network.name,
                    "--mount", f"type=volume,source={volume.name},target=/app/data",
                    settings.DEFAULT_BASE_IMAGE
                ],
                check=True
            )
        except subprocess.CalledProcessError as e:
            logging.error("Failed to create Docker container. Error: {e}")
            raise Exception(f"Failed to create Docker container: {e}")
        
        instance = Instance.objects.create(
            **validated_data, user=user, network=network, directory=user.directory, status='created'
        )
        volume.attached_instance = instance
        volume.save()

        return instance
    

class InstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instance
        fields = "__all__"
