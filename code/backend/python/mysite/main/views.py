import logging

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.db.models import Q

from .models import Instance, Server

import requests

def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        print("request data is:")
        print(request.POST)
        try:
            user = User.objects.get(username=username)
        except Exception as e:
            context = {
                "errrors": [
                    {
                        "message": _("Nom d'utilisateur ou mot de passe incorrect")
                    }
                ]
            }
            return render(request, "main/login.html", context=context, status=400)

        if not user.check_password(password):
            print("Mismatched passwords")
            return render(
                request,
                "main/login.html",
                context={
                    "errors": [
                        {
                            "message": _("Nom d'utilisateur ou mot de passe incorrect"),
                        }
                    ]
                },
                status=400
            )

        if not user.is_active:
            print("User is not active")
            return render(
                request,
                "main/login.html",
                context={
                    "errors": [
                        {
                            "message": _("Compte a ete desactive"),
                        }
                    ]
                },
                status=403
            )

        login(request, user)
        print("User logged in successfully")

        return redirect("home")
    else:
        return render(request, "main/login.html")

@login_required
def logout_view(request):
    logout(request)
    return redirect("login")

def signup(request):
    if request.method == "POST":
        print("POST data")
        print(request.POST)
        username = request.POST['username']
        password = request.POST['password']
        email = request.POST['email']

        if User.objects.filter(username=username).count() > 0:
            context = {
                "errors": [
                    {"message": _("Nom d'utilisateur deja prit")}
                ]
            }
            return render(request, "main/signup.html", context=context)

        else:
            print("Creating user account")
            user = User.objects.create(username=username, password=password, email=email)
            print(f"Created user {user}")
            return redirect("login")
    return render(request, "main/signup.html")

def home(request):
    return redirect("instances")

@login_required
def instances(request):
    user = request.user
    user_instances = Instance.objects.filter(user=user)

    print(f"Instances gotten for {user}")
    print(user_instances)

    if request.method == "POST":
        instance_name, port = request.POST['name'], request.POST['port']
        admin_password = request.POST['admin_password']

        errors = []
        
        if Instance.objects.filter(name=instance_name).exists():
            errors.append(_("Instance name already taken"))

        # get servers that don't have instances running on the port
        try:
            servers = Server(~Q(instance__host_port=port))

            if servers.count() == 0:
                errors.append(_("Port unavailable"))

            if len(errors) > 0:
                # return template with errors
                return render(request, "main/instances.html", {'instances': user_instances, 'errors': errors})
            else:
                # create instance
                server = servers.first()
                instance = Instance.objects.create(server=server, **request.POST, state="Starting")

                # faire une requete a l'API
                response = requests.post(f"{server.hostname}:8000/api/instances", {
                    "http_host_port": instance.host_port,
                    "root_password": admin_password,
                    "root_email": "admin@mail.com"
                })
                if response.status_code == 200:
                    print(f"Instance started successfully")
                    content = response.content

                    instance.instance_id = content['id']

                user_instances = list(user_instances) + [instance]
                return render(request, "main/instances.html", {'instances': user_instances})

        except Exception:
            pass

    return render(request, "main/instances.html", {'instances': user_instances})

def stop_instance(request, instance_id):
    user = request.user

    instance = get_object_or_404(user=user, id=instance_id)
    
    response = requests.post(f"{instance.server.hostname}:8000/api/instances/{instance.instance_id}/stop")

    try:
        response.raise_for_status()

        instance.state = "Stopped"
        instance.save()
    except Exception as e:    
        logging.error(f"Error stopping the instance. Response from server: {response.content}")
        return HttpResponse("Error stopping instance. Go back to the <a href='/instances'>instances</a> page")

    return redirect("instances")
    
def start_instance(request, instance_id):
    user = request.user

    instance = get_object_or_404(user=user, id=instance_id)

    if instance.state.lower() == "stopped":
        response = requests.post(f"{instance.server.hostname}:8000/api/instances/{instance.instance_id}/start")

        try:
            response.raise_for_status()

            instance.state = "Starting"
            instance.save()
        except Exception as e:    
            logging.error(f"Error starting the instance. Response from server: {response.content}")
            return HttpResponse("Error starting instance. Go back to the <a href='/instances'>instances</a> page")


    return redirect("instances")

def delete_instance(request, instance_id):
    user = request.user

    instance = get_object_or_404(user=user, id=instance_id)

    response = requests.delete(f"{instance.server.hostname}:8000/api/instances/{instance.instance_id}")

    try:
        response.raise_for_status()

        instance.delete()
    except Exception as e:
        logging.error(f"Error deleting the instance. Response from server: {response.content}")
        return HttpResponse("Error deleting instance. Go back to the <a href='/instances'>instances</a> page")
    
    return redirect("instances")