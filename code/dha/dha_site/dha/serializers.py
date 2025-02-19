import os
import subprocess
import random
import string

from django.conf import settings
from django.db.models import Q

from rest_framework import serializers

from .models import *
from .utils.functions import slugify, get_omnibus_config

class CreateInstanceSerializer(serializers.ModelSerializer):
    root_password = serializers.CharField(write_only=True)
    root_email = serializers.CharField(write_only=True)

    class Meta:
        model = Instance
        fields = ["name", "http_host_port", "https_host_port", "root_password", "root_email"]
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
        value = slugify(value)

        if Instance.objects.filter(name=value).count() > 0:
            raise serializers.ValidationError(f"{name} already used by another instance. Please choose another")

        return value

    def create(self, validated_data):
        try:
            instance_name = validated_data['name']
            username = instance_name + "-user"
            network_name = instance_name + "-network"
            # create user
            user = User.create(username=username)

            # create network
            network = Network.create(network_name=network_name)

            config_volume = Volume.create(name=instance_name + "-config-volume")
            data_volume = Volume.create(name=instance_name + "-data-volume")
            logs_volume = Volume.create(name=instance_name + "-logs-volume")
        except Exception as e:
            user.delete()
            network.delete()
            raise e
        
        try:
            http_host_port = validated_data['http_host_port']
            host_name = settings.HOST_NAME
            root_password = validated_data.pop('root_password')
            root_email = validated_data.pop('root_email')

            subprocess.run(
                [
                    "docker", "run", "-d", 
                    "--name", validated_data['name'],
                    "--hostname", f"{host_name}",
                    "--network", network.name,
                    "--env", get_omnibus_config(host_name, http_host_port, root_password, root_email ),
                    "--mount", f"type=volume,source={volume.name},target=/app/data",
                    "--publish", f"{http_host_port}:80",
                    "--restart", "always",
                    "--volume", f"{user.get_directory('config')}:/etc/gitlab",
                    "--volume", f"{user.get_directory('logs')}:/var/log/gitlab",
                    "--volume", f"{user.get_directory('data')}:/var/opt/gitlab",
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
