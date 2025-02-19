#! /bin/bash
#!/bin/bash

# Define variables
USERNAME="dockerman"
APP_DIR="/path/to/your/application"

# Step 1: Create the user if it doesn't already exist
if id "$USERNAME" &>/dev/null; then
    echo "User $USERNAME already exists."
else
    sudo useradd -m -s /bin/bash "$USERNAME"
    echo "User $USERNAME created."
fi

# Step 2: Change ownership of the application directory
if [ -d "$APP_DIR" ]; then
    sudo chown -R "$USERNAME:$USERNAME" "$APP_DIR"
    echo "Ownership of $APP_DIR given to $USERNAME."
else
    echo "Directory $APP_DIR does not exist."
    exit 1
fi

# Step 3: Add the user to the docker group
if groups "$USERNAME" | grep -q "\bdocker\b"; then
    echo "$USERNAME is already in the docker group."
else
    sudo usermod -aG docker "$USERNAME"
    echo "$USERNAME added to the docker group."
fi

# Step 4: Give the user permission to add and delete users (without sudo)
# This requires granting access to the `useradd` and `userdel` commands.
# We'll use a sudoers file to allow the user to run these commands without a password.

SUDOERS_FILE="/etc/sudoers.d/$USERNAME"
if [ ! -f "$SUDOERS_FILE" ]; then
    echo "$USERNAME ALL=(ALL) NOPASSWD: /usr/sbin/useradd, /usr/sbin/userdel" | sudo tee "$SUDOERS_FILE"
    echo "User $USERNAME can now add and delete users without sudo."
else
    echo "Sudoers rule for $USERNAME already exists."
fi

echo "Script execution completed."
