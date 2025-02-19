import logging

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext as _

import docker

from rest_framework import status, viewsets
from rest_framework.decorators import action, permission_classes
from rest_framework.response import Response

from . import serializers
from .models import Instance
from .utils.functions import get_container_status

class MultipleSerializerViewSet(viewsets.GenericViewSet):
    serializer_classes = {}
    
    def get_serializer_class(self):
        if not isinstance(self.serializer_classes, dict):
            raise ImproperlyConfigured(_("serializer_classes variable must be a dict mapping"))

        if self.action in self.serializer_classes.keys():
            return self.serializer_classes[self.action]
        
        return super().get_serializer_class()
    

class InstanceViewSet(viewsets.ModelViewSet, MultipleSerializerViewSet):
    serializer_class = serializers.InstanceSerializer
    serializer_classes = {
        'create': serializers.CreateInstanceSerializer,
    }

    queryset = Instance.objects.all()

    def create(self, request, *args, **kwargs):
        logging.info("Request to create a new container instance")

        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)

        instance = serializer.create(serializer.validated_data)
        data = self.serializer_class(instance).data

        logging.info(f"Container instance ({instance.name}) successfully created")
        return Response(data, status=status.HTTP_201_CREATED)
    
    @action(methods=['GET'], detail=True)
    def status(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            _status = instance.get_status()

            return Response(_status)
        except docker.errors.NotFound as e:
            try:
                instance.delete(ignore_errors=True)
            except Exception as e:
                logging.error("Error deleting an instance that was not linked to a docker container")
                
            return Response(f"No image with name {instance.name} found. Go back to the instances list: /api/instances", status=status.HTTP_404_NOT_FOUND)

    @action(methods=['POST'], detail=True)
    def stop(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.stop()

        return Response("Instance stopped successfully")

    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)
