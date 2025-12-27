# Module 1: Containers & Orchestration - Local Practice


## Learning Objectives

* Understand Docker concepts: images, containers, volumes, networks

* Containerize a Python Flask application

* Create multi-container applications with Docker Compose

* Practice essential Docker commands

* Prepare for cloud deployment (Module 2)

## Prerequisites
1. Install Docker Desktop:

    * [Windows/Mac](https://www.docker.com/products/docker-desktop/)

    * Linux: [Install Docker Engine](https://docs.docker.com/engine/install/)

2. Verify installation:

```bash
docker --version
docker-compose --version
docker run hello-world
```

3. Required tools:

    * Terminal/Command Prompt

    * Text editor (VS Code recommended)

    * Git (optional, for version control)

## Project Setup
1. Create Project Directory

```bash
mkdir module_01
cd module_01
```

2. Project Structure
```text
module_01/
├── app.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── nginx.conf (optional)
└── README.md
```

## Exercise 1.1: Containerize a Flask Application
### **File 1**: ```requirements.txt```

```txt
Flask==2.3.3
redis==4.6.0
```

### **File 2**: ```app.py```

```python
from flask import Flask, jsonify, request
import redis
import os
import socket

app = Flask(__name__)

# Connect to Redis
redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = int(os.getenv('REDIS_PORT', 6379))
redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

@app.route('/')
def hello():
    hostname = socket.gethostname()
    visitor_count = redis_client.incr('visitors')
    
    return jsonify({
        'message': 'Hello from Dockerized Flask App!',
        'container_id': hostname,
        'visitor_count': visitor_count,
        'environment': os.getenv('ENVIRONMENT', 'development')
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'flask-app'})

@app.route('/keys', methods=['GET', 'POST'])
def keys():
    if request.method == 'POST':
        data = request.json
        key = data.get('key')
        value = data.get('value')
        if key and value:
            redis_client.set(key, value)
            return jsonify({'message': f'Key {key} set successfully'})
    
    # GET request - list all keys
    keys = redis_client.keys('*')
    return jsonify({'keys': keys})

@app.route('/key/<key_name>')
def get_key(key_name):
    value = redis_client.get(key_name)
    return jsonify({'key': key_name, 'value': value})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

### **File 3**: ```Dockerfile```

```dockerfile
# Use official Python runtime as base image
FROM python:3.9-slim

# Set working directory in container
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV FLASK_ENV=production

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port 5000
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"

# Command to run the application
CMD ["python", "app.py"]
```

## Hands-on Practice: Docker Commands
### Task 1: Build and Run a Single Container

```bash
# 1. Build the Docker image
docker build -t flask-app:v1 .

# 2. View all images
docker images

# 3. Run the container
docker run -d -p 5000:5000 --name my-flask-app flask-app:v1


# 4. Test the application
curl http://localhost:5000
# Or open: http://localhost:5000

# 5. View running containers
docker ps

# 6. View container logs
docker logs my-flask-app

# 7. Execute commands inside container
docker exec -it my-flask-app /bin/bash
# Inside container: ls, pwd, python --version
# Exit: exit

# 8. Stop and remove container
docker stop my-flask-app
docker rm my-flask-app
```

### Task 2: Multi-Container Communication
```bash
cd v2
# 1. Build the Docker image
docker build -t flask-app:v2 .

# 2. Run Redis container
docker run -d -p 6379:6379 --name my-redis redis:7-alpine

# 3. Run Flask app connected to Redis
docker run -d \
  -p 5001:5000 \
  --name flask-with-redis \
  -e REDIS_HOST=host.docker.internal \
  -e ENVIRONMENT=production \
  flask-app:v2

# 4. Test Redis connection
curl -X POST http://localhost:5001/keys \
  -H "Content-Type: application/json" \
  -d '{"key": "student", "value": "cloud-course"}'

curl http://localhost:5001/keys
curl http://localhost:5001/key/student

# 5. Clean up
docker stop flask-with-redis my-redis
docker rm flask-with-redis my-redis
```

### Task 3: Docker Networks
```bash
# 1. Create a custom network
docker network create app-network

# 2. Run Redis in the network
docker run -d \
  --name redis-network \
  --network app-network \
  redis:7-alpine

# 3. Run Flask app in same network
docker run -d \
  -p 5002:5000 \
  --name flask-network \
  --network app-network \
  -e REDIS_HOST=redis-network \
  -e ENVIRONMENT=network-demo \
  flask-app:v2

# 4. Test
curl http://localhost:5002

# Test Redis connection
curl -X POST http://localhost:5002/keys \
  -H "Content-Type: application/json" \
  -d '{"key": "student", "value": "cloud-course"}'

curl http://localhost:5002/keys
curl http://localhost:5002/key/student

# 5. Inspect network
docker network inspect app-network

# 6. Clean up
docker stop flask-network redis-network
docker rm flask-network redis-network
docker network rm app-network
```

## Exercise 1.2: Docker Compose for Multi-Container Apps
### File 4: docker-compose.yml

```yaml
version: '3.8'

services:
  # Flask web application
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - REDIS_HOST=redis
      - ENVIRONMENT=production
      - FLASK_ENV=production
    depends_on:
      - redis
    volumes:
      - ./app.py:/app/app.py  # Mount for development
    networks:
      - app-network
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Redis service
  redis:
    image: "redis:7-alpine"
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes
    networks:
      - app-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

volumes:
  redis-data:

networks:
  app-network:
    driver: bridge
```

### File 5: ```nginx.conf``` (Optional - Reverse Proxy)

```nginx
events {
    worker_connections 1024;
}

http {
    upstream flask_servers {
        server web:5000;
    }

    server {
        listen 80;
        server_name localhost;

        location / {
            proxy_pass http://flask_servers;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /health {
            proxy_pass http://web:5000/health;
        }
    }
}
```

### Docker Compose Practice Commands
```bash
# 1. Start all services
docker compose up -d

# 2. View running services
docker compose ps

# 3. Check logs
docker compose logs          # All services
docker compose logs web      # Specific service
docker compose logs redis

# 4. Test the application
curl http://localhost:5000

# 5. Scale web service (simulate multiple instances)
docker compose up -d --scale web=3
docker compose ps

# 6. Execute commands in a service
docker compose exec web python --version
docker compose exec redis redis-cli ping

# 7. Hot-reload development
# Edit app.py, then:
docker compose restart web

# 8. Rebuild and restart
docker compose up -d --build

# 9. Stop services
docker compose stop

# 10. Remove everything
docker compose down -v
```

# Student Exercises

## Exercise 1: Modify the Application
1. Change the welcome message in app.py

2. Add a new endpoint /version that returns the Python version

3. Rebuild and test

## Exercise 2: Add PostgreSQL Service

### Add this to docker-compose.yml:

```yaml
postgres:
  image: postgres:15-alpine
  environment:
    POSTGRES_PASSWORD: student123
    POSTGRES_USER: student
    POSTGRES_DB: clouddb
  volumes:
    - postgres-data:/var/lib/postgresql/data
  networks:
    - app-network
  ports:
    - "5432:5432"
```

## Exercise 3: Environment Variables
1. Create a .env file:

```env
REDIS_HOST=redis
ENVIRONMENT=staging
POSTGRES_PASSWORD=student123
```

2. Update docker-compose.yml to use the .env file:

```yaml
web:
  build: .
  env_file:
    - .env
```

## Exercise 4: Data Persistence Test

1. Start services: ```docker compose up -d```

2. Visit [http://localhost:5000](http://localhost:5000) multiple times (watch visitor count)

3. Stop: ```docker compose stop```

4. Start again: ```docker compose start```

5. Check if visitor count persisted

# Troubleshooting Guide
## Common Issues & Solutions



|Issue                      |Solution|
|:---                       |:--- |
|Port already in use        | Change port mapping or stop conflicting process |
|Docker daemon not running  | Start Docker Desktop or ```sudo systemctl start docker```|
|Permission denied          | ```sudo usermod -aG docker $USER``` (Linux), then logout/login|
|Build cache problems       | ```docker compose build --no-cache```|
|Container won't start      |Check logs: ```docker compose logs web```|
|Network conflicts          | ```docker network prune```|



## Debug Commands

```bash
# Check container health
docker inspect --format='{{json .State.Health}}' CONTAINER_ID

# View container details
docker inspect CONTAINER_NAME

# Remove all unused resources
docker system prune -a

# View disk usage
docker system df

# List all networks
docker network ls

# List all volumes
docker volume ls
```

## Key Concepts Checklist
1. Docker Basics
    * Image vs Container

    * Dockerfile structure

    * Build context

    * Layered architecture

    * Image tagging

2. Container Operations
    * Run, stop, remove containers

    * Port mapping

    * Environment variables

    * Volume mounting

    * Network configuration

3. Docker Compose
    * Service definition

    * Dependency management

    * Multi-container networking

    * Volume persistence

    * Health checks

## Assessment Questions
1. What is the purpose of the ```EXPOSE``` instruction in a Dockerfile?

2. How does Docker achieve isolation between containers?

3. Explain the difference between ```docker stop``` and ```docker kill```

4. What problem does Docker Compose solve?

5. How would you persist data when a container is removed?

6. Explain this port mapping: ```-p 8080:80```

7. What is the purpose of the ```depends_on``` directive in Docker Compose?

8. How can you share environment variables between services?

9. What command would you use to see real-time container logs?

10. Explain the build cache mechanism in Docker

## Extension Activities
### Challenge 1: Multi-Stage Build
Create a multi-stage Dockerfile that:

1. Builds the application in a builder stage

2. Copies only necessary files to the final stage

3. Reduces final image size

### Challenge 2: Add Monitoring
Add Prometheus and Grafana to monitor:

* Container resource usage

* Application metrics

* Redis performance

### Challenge 3: CI/CD Pipeline
Create a GitHub Actions workflow that:

1. Builds the Docker image on push

2. Runs tests inside container

3. Pushes to Docker Hub

### Challenge 4: Security Scanning
Use ```docker scan``` to check for vulnerabilities:

```bash
docker scan flask-app:v1
```

### Resources & Next Steps

**Documentation**

[Docker Official Docs](https://docs.docker.com/)

[Dockerfile Reference](https://docs.docker.com/reference/dockerfile)

[Docker Compose Reference](https://docs.docker.com/reference/compose-file/)



 
