import logging

from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import gettext as _

from rest_framework import status, viewsets
from rest_framework.decorators import action
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
    
    @action(methods=['POST'], detail=True)
    def status(self, request, *args, **kwargs):
        instance = self.get_object()

        status = get_container_status(instance.name)

        return Response(status, status=status.HTTP_200_OK)
    
