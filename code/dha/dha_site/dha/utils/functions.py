import logging
import subprocess
import re
import docker

def log_error(message, error, raise_exception=True):
    logging.error(f"{message}. Error: {error}")

    if raise_exception:
        raise error

def slugify(string):
    slug = string.lower()
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = slug.strip('-')

    return slug

def remove_docker_container(container_name_or_id):
    try:
        # Attempt to stop the container (ignoring if it's already stopped)
        subprocess.run(["docker", "stop", container_name_or_id], check=True, stderr=subprocess.PIPE)
        print(f"Container '{container_name_or_id}' stopped successfully.")
    except subprocess.CalledProcessError as e:
        if "No such container" in e.stderr.decode():
            print(f"Container '{container_name_or_id}' is not running or does not exist. Proceeding to remove it.")
        else:
            print(f"Error stopping container '{container_name_or_id}': {e.stderr.decode()}")
            return

    try:
        # Remove the container
        subprocess.run(["docker", "rm", container_name_or_id], check=True, stderr=subprocess.PIPE)
        print(f"Container '{container_name_or_id}' removed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error removing container '{container_name_or_id}': {e.stderr.decode()}")


def get_container_status(container_name_or_id):
    client = docker.from_env()

    container = client.containers.get(container_name_or_id)
    container.reload()

    status = container.status

    state = container.attrs['State']
    
    health_status = state.get('Health', {}).get('Status', 'unknown')  # Check for health status if available

    # Build a more detailed status message
    if status == 'running':
        # Provide additional health details if available
        if health_status != 'unknown':
            status_detail = f"running (health: {health_status})"
        else:
            status_detail = "running"
    elif status == 'created':
        status_detail = "starting"  # Containers in 'created' state are typically in a startup process
    else:
        status_detail = status  # Use Docker's base status for other cases (e.g., 'stopped', 'exited')

    return status_detail

def get_omnibus_config(hostname, port, root_password, root_email) -> str:
    return f"""GITLAB_OMNIBUS_CONFIG="external_url 'http://{hostname}:{port}'; gitlab_rails['lfs_enabled'] = true; gitlab_rails['initial_root_password'] = '{root_password}'; gitlab_rails['initial_root_email'] = '{root_email}'" """

def get_uid_and_gid(username):
    try:
        result = subprocess.run(
            ["id", "-u", username], capture_output=True, text=True, check=True
        )
        uid = int(result.stdout.strip())  # Convert output to int

        result = subprocess.run(
            ["id", "-g", username], capture_output=True, text=True, check=True
        )
        gid = int(result.stdout.strip())  # Convert output to int

        return uid, gid
    except subprocess.CalledProcessError as e:
        log_error(f"Error getting uid and gid for {username}", e)