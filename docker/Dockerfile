FROM python:3

# Set the timezone
RUN apt-get update && \
    apt-get install -y tzdata && \
    rm -rf /var/lib/apt/lists/*

# This is what make vscode remote-ssh work
RUN apt-get update && \
    apt-get install -y wget curl git bash openssh-client openssh-server grep tcsh && \
    rm -rf /var/lib/apt/lists/*

# Define build arguments
ARG DOCKER_WEB_PORT
ARG DOCKER_SSH_PORT
ARG SSH_USERNAME
ARG SSH_PASSWORD

# Install necessary python packages
RUN apt-get update && \
    apt-get install -y build-essential libssl-dev libffi-dev && \
    pip install flask flask_sqlalchemy && \
    rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV DOCKER_WEB_PORT=$DOCKER_WEB_PORT
ENV DOCKER_SSH_PORT=$DOCKER_SSH_PORT
ENV SSH_USERNAME=$SSH_USERNAME
ENV SSH_PASSWORD=$SSH_PASSWORD

# Create a new user
RUN useradd -m -s /bin/bash $SSH_USERNAME && \
    echo "$SSH_USERNAME:$SSH_PASSWORD" | chpasswd && \
    usermod -aG sudo $SSH_USERNAME

# Setup SSH
RUN mkdir /var/run/sshd && \
    sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config && \
    sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config && \
    sed -i "s/#Port 22/Port $DOCKER_SSH_PORT/" /etc/ssh/sshd_config && \
    echo "AllowUsers $SSH_USERNAME" >> /etc/ssh/sshd_config && \
    ssh-keygen -A

# Expose ports
EXPOSE $DOCKER_WEB_PORT $DOCKER_SSH_PORT

# Start the SSH daemon
CMD ["/usr/sbin/sshd", "-D"]
