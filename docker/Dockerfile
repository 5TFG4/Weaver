FROM python:alpine

# Update and remove dropbear for OpenSSH
RUN apk del dropbear && \
    apk update

# Set the timezone
RUN apk add --no-cache tzdata

# This is what make vscode remote-ssh work
RUN apk add --no-cache wget curl && \
    apk add --no-cache gcompat libstdc++6 git bash && \
    apk add --no-cache openssh && \
    apk add --no-cache grep
    
# Define build arguments
ARG DOCKER_WEB_PORT
ARG DOCKER_SSH_PORT
ARG SSH_USERNAME
ARG SSH_PASSWORD

# Install necessary python packages
RUN apk add --no-cache --virtual .build-deps \
    build-base gcc musl-dev libffi-dev openssl-dev \
    && pip install flask \
    && pip install flask_sqlalchemy \
    && apk del .build-deps

# Set environment variables
ENV DOCKER_WEB_PORT=$DOCKER_WEB_PORT
ENV DOCKER_SSH_PORT=$DOCKER_SSH_PORT
ENV SSH_USERNAME=$SSH_USERNAME
ENV SSH_PASSWORD=$SSH_PASSWORD

# Create a new user for SSH
RUN adduser -D -g '' $SSH_USERNAME && \
    echo "$SSH_USERNAME:$SSH_PASSWORD" | chpasswd && \
    sed -i s/#PermitRootLogin.*/PermitRootLogin\ no/ /etc/ssh/sshd_config && \
    sed -i s/#PasswordAuthentication.*/PasswordAuthentication\ yes/ /etc/ssh/sshd_config && \
    sed -i "s/#Port 22/Port $DOCKER_SSH_PORT/g" /etc/ssh/sshd_config

# Expose ports
EXPOSE $DOCKER_WEB_PORT
EXPOSE $DOCKER_SSH_PORT

# Generate SSH credentials
RUN ssh-keygen -A

# In /etc/ssh/sshd-config, set
# AllowTcpForwarding yes
# PermitTunnel       yes
# For VSCode Remote SSH
RUN sed -i 's/^#AllowTcpForwarding\s.*/AllowTcpForwarding yes/' /etc/ssh/sshd_config && \ 
    sed -i 's/^#PermitTunnel\s.*/PermitTunnel yes/' /etc/ssh/sshd_config


# Start the SSH daemon
CMD ["/usr/sbin/sshd", "-D"]