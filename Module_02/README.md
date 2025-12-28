# Module 2: Kubernetes Deployment on Minikube
Kubernetes Deployment Files for Flask + Redis Application

## Prerequisites
1. Install Minikube: [https://minikube.sigs.k8s.io/docs/start/](https://minikube.sigs.k8s.io/docs/start/)

2. Install kubectl: [https://kubernetes.io/docs/tasks/tools/](https://kubernetes.io/docs/tasks/tools/)

3. Start Minikube cluster:

```bash
minikube start
minikube status
```

## Project Structure for Kubernetes

```text
module_02-kubernetes/
├── 00-namespace.yaml
├── 01-configmap.yaml
├── 02-secret.yaml
├── 03-redis-deployment.yaml
├── 04-redis-service.yaml
├── 05-flask-deployment.yaml
├── 06-flask-service.yaml
├── 07-ingress.yaml
├── 08-hpa.yaml
└── 09-persistent-volume.yaml
```

### File 1: Namespace Configuration
```00-namespace.yaml```

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: cloud-course
  labels:
    name: cloud-course
    environment: development
```

### File 2: ConfigMap for Application Configuration
```01-configmap.yaml```

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: flask-app-config
  namespace: cloud-course
data:
  # Application configuration
  flask-environment: "production"
  flask-debug: "false"
  
  # Redis configuration
  redis-host: "redis-service"
  redis-port: "6379"
  
  # Application settings
  app-name: "Cloud Course Flask App"
  welcome-message: "Hello from Kubernetes!"
  
  # Nginx configuration (if using as sidecar)
  nginx.conf: |
    events {
        worker_connections 1024;
    }
    http {
        upstream flask_backend {
            server 127.0.0.1:5000;
        }
        server {
            listen 80;
            location / {
                proxy_pass http://flask_backend;
                proxy_set_header Host $host;
                proxy_set_header X-Real-IP $remote_addr;
            }
        }
    }
```

### File 3: Secrets for Sensitive Data
```02-secret.yaml```

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: flask-app-secrets
  namespace: cloud-course
type: Opaque
data:
  # Generate with: echo -n "password" | base64
  redis-password: cGFzc3dvcmQ=  # "password" in base64
  api-key: YXBpLWtleS1zZWNyZXQ=  # "api-key-secret" in base64
  database-url: cG9zdGdyZXNxbDovL3VzZXI6cGFzc3dvcmRAZGI6NTQzMi9kYg==
```

### File 4: Redis Deployment
```03-redis-deployment.yaml```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis-deployment
  namespace: cloud-course
  labels:
    app: redis
    component: cache
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
      component: cache
  template:
    metadata:
      labels:
        app: redis
        component: cache
        tier: backend
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 6379
          name: redis
        resources:
          requests:
            memory: "64Mi"
            cpu: "100m"
          limits:
            memory: "128Mi"
            cpu: "200m"
        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: flask-app-secrets
              key: redis-password
        # Redis configuration as command arguments
        command: ["redis-server"]
        args: ["--appendonly", "yes", "--requirepass", "$(REDIS_PASSWORD)"]
        livenessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 5
          periodSeconds: 5
        volumeMounts:
        - name: redis-storage
          mountPath: /data
      volumes:
      - name: redis-storage
        emptyDir: {}
```

### File 5: Redis Service
```04-redis-service.yaml```

```yaml
apiVersion: v1
kind: Service
metadata:
  name: redis-service
  namespace: cloud-course
  labels:
    app: redis
    component: cache
spec:
  selector:
    app: redis
    component: cache
  ports:
  - port: 6379
    targetPort: 6379
    protocol: TCP
    name: redis
  # ClusterIP is default, only accessible within cluster
  type: ClusterIP
```

### File 6: Flask Application Deployment
```05-flask-deployment.yaml```

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: flask-deployment
  namespace: cloud-course
  labels:
    app: flask
    component: backend
spec:
  replicas: 3  # Running 3 instances for high availability
  selector:
    matchLabels:
      app: flask
      component: backend
  template:
    metadata:
      labels:
        app: flask
        component: backend
        tier: backend
    spec:
      containers:
      # Main Flask application container
      - name: flask-app
        image: flask-app:v1  # Using locally built image
        imagePullPolicy: IfNotPresent  # Use "Always" for production with registry
        ports:
        - containerPort: 5000
          name: http
        env:
        - name: REDIS_HOST
          valueFrom:
            configMapKeyRef:
              name: flask-app-config
              key: redis-host
        - name: REDIS_PORT
          valueFrom:
            configMapKeyRef:
              name: flask-app-config
              key: redis-port
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: flask-app-secrets
              key: redis-password
        - name: FLASK_ENV
          valueFrom:
            configMapKeyRef:
              name: flask-app-config
              key: flask-environment
        - name: APP_NAME
          valueFrom:
            configMapKeyRef:
              name: flask-app-config
              key: app-name
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 2
        startupProbe:
          httpGet:
            path: /health
            port: 5000
          failureThreshold: 30  # Allow more time for startup
          periodSeconds: 10
      
      # Optional: Nginx sidecar container for reverse proxy
      - name: nginx-sidecar
        image: nginx:alpine
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 80
          name: http
        volumeMounts:
        - name: nginx-config
          mountPath: /etc/nginx/nginx.conf
          subPath: nginx.conf
        resources:
          requests:
            memory: "64Mi"
            cpu: "50m"
          limits:
            memory: "128Mi"
            cpu: "100m"
      
      volumes:
      - name: nginx-config
        configMap:
          name: flask-app-config
          items:
          - key: nginx.conf
            path: nginx.conf
```

### File 7: Flask Service
```06-flask-service.yaml```

```yaml
apiVersion: v1
kind: Service
metadata:
  name: flask-service
  namespace: cloud-course
  labels:
    app: flask
    component: backend
spec:
  selector:
    app: flask
    component: backend
  ports:
  - port: 80
    targetPort: 5000  # Maps to Flask container port
    protocol: TCP
    name: http
  - port: 5000
    targetPort: 5000
    protocol: TCP
    name: http-alt
  # For Minikube, use NodePort to access from host
  type: NodePort
  # For cloud providers, you might use LoadBalancer:
  # type: LoadBalancer
```

### File 8: Ingress Controller (Optional)
```07-ingress.yaml```

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: flask-ingress
  namespace: cloud-course
  annotations:
    # Minikube ingress addon
    kubernetes.io/ingress.class: "nginx"
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/ssl-redirect: "false"
spec:
  rules:
  - host: flask-app.local  # Add this to your /etc/hosts
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: flask-service
            port:
              number: 80
```

### File 9: Horizontal Pod Autoscaler
```08-hpa.yaml```

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: flask-hpa
  namespace: cloud-course
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: flask-deployment
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 60
```

### File 10: Persistent Volume (For Redis Data)
```09-persistent-volume.yaml```

```yaml
# Persistent Volume Claim for Redis
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: cloud-course
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: standard  # Minikube default storage class
---
# Update Redis deployment to use PVC
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis-deployment-pv
  namespace: cloud-course
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis-pv
  template:
    metadata:
      labels:
        app: redis-pv
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        volumeMounts:
        - name: redis-data
          mountPath: /data
      volumes:
      - name: redis-data
        persistentVolumeClaim:
          claimName: redis-pvc
```

## Deployment Script 
1. Create a ```deploy.sh``` script:

```bash
#!/bin/bash
# Kubernetes Deployment Script for Minikube

echo "======================================"
echo "Kubernetes Deployment - Cloud Course"
echo "======================================"

# Step 1: Start Minikube (if not running)
echo "1. Starting Minikube..."
minikube status || minikube start

# Step 2: Build Docker image and load into Minikube
echo "2. Building and loading Docker image..."
eval $(minikube docker-env)
docker build -t flask-app:v1 ../module3-docker-example/.
docker images | grep flask-app

# Step 3: Create namespace
echo "3. Creating namespace..."
kubectl apply -f 00-namespace.yaml

# Step 4: Create ConfigMap and Secrets
echo "4. Creating ConfigMap and Secrets..."
kubectl apply -f 01-configmap.yaml
kubectl apply -f 02-secret.yaml

# Step 5: Deploy Redis
echo "5. Deploying Redis..."
kubectl apply -f 03-redis-deployment.yaml
kubectl apply -f 04-redis-service.yaml

# Step 6: Deploy Flask application
echo "6. Deploying Flask application..."
kubectl apply -f 05-flask-deployment.yaml
kubectl apply -f 06-flask-service.yaml

# Step 7: Wait for pods to be ready
echo "7. Waiting for pods to be ready..."
sleep 10
kubectl get pods -n cloud-course --watch

# Step 8: Get service URLs
echo "8. Getting service information..."
minikube service list -n cloud-course

# Step 9: Enable ingress (optional)
echo "9. Enabling ingress addon..."
minikube addons enable ingress

# Step 10: Deploy additional resources
echo "10. Deploying additional resources..."
kubectl apply -f 07-ingress.yaml
kubectl apply -f 08-hpa.yaml
kubectl apply -f 09-persistent-volume.yaml

echo "======================================"
echo "Deployment Complete!"
echo "======================================"
echo ""
echo "Commands to test deployment:"
echo "1. Check all resources:"
echo "   kubectl get all -n cloud-course"
echo ""
echo "2. Get Flask service URL:"
echo "   minikube service flask-service -n cloud-course --url"
echo ""
echo "3. Check pod logs:"
echo "   kubectl logs -n cloud-course -l app=flask --tail=10"
echo ""
echo "4. Scale deployment:"
echo "   kubectl scale -n cloud-course deployment/flask-deployment --replicas=5"
echo ""
echo "5. Access application:"
echo "   curl \$(minikube service flask-service -n cloud-course --url)"
```

2. Test the deployment:

Run these command to test the deployment.

```bash
# 1. Check all resources:
kubectl get all -n cloud-course

# 2. Get Flask service URL:
minikube service flask-service -n cloud-course --url

# 3. Check pod logs:
kubectl logs -n cloud-course -l app=flask --tail=10

# 4. Scale deployment:
kubectl scale -n cloud-course deployment/flask-deployment --replicas=5

# 5. Access application:
curl \$(minikube service flask-service -n cloud-course --url)
```

## Practical Exercises for Students

### Exercise 1: Basic Deployment

```bash
# 1. Apply all configurations
kubectl apply -f ./

# 2. Check deployment status
kubectl get all -n cloud-course

# 3. Get the service URL
minikube service flask-service -n cloud-course --url

# 4. Test the application
curl http://<minikube-ip>:<node-port>/
```

### Exercise 2: Troubleshooting Commands

```bash
# View detailed information
kubectl describe pod -n cloud-course <pod-name>
kubectl describe service -n cloud-course flask-service

# View logs
kubectl logs -n cloud-course -l app=flask --tail=50
kubectl logs -n cloud-course -l app=redis --tail=50

# Debug containers
kubectl exec -n cloud-course -it <pod-name> -- /bin/sh

# Check events
kubectl get events -n cloud-course --sort-by=.metadata.creationTimestamp
```

### Exercise 3: Scaling Operations

```bash
# Scale the Flask deployment
kubectl scale -n cloud-course deployment/flask-deployment --replicas=5

# Watch scaling
kubectl get pods -n cloud-course -w

# Check HPA
kubectl get hpa -n cloud-course
kubectl describe hpa -n cloud-course flask-hpa
```

### Exercise 4: Rolling Updates

```bash
# Update the image
kubectl set image -n cloud-course deployment/flask-deployment flask-app=flask-app:v2

# Watch rolling update
kubectl rollout status -n cloud-course deployment/flask-deployment

# Rollback if needed
kubectl rollout undo -n cloud-course deployment/flask-deployment
```

## Common Minikube Issues & Solutions
### Issue 1: Cannot Pull Local Images
**Solution**: Build image directly in Minikube Docker daemon:

```bash
eval $(minikube docker-env)
docker build -t flask-app:v1 .
```

### Issue 2: NodePort Not Accessible
**Solution**: Use minikube service command:

```bash
minikube service flask-service -n cloud-course
# Or get URL
minikube service flask-service -n cloud-course --url
```

### Issue 3: Persistent Volume Issues
**Solution**: Check storage class:

```bash
kubectl get storageclass
minikube addons enable storage-provisioner
```

### Issue 4: Ingress Not Working
**Solution**: Enable ingress addon:

```bash
minikube addons enable ingress
kubectl get pods -n ingress-nginx
```

## Student Lab Tasks
Students should do these tasks by their selves.

### Task 1: Deploy and Test

1. Deploy all Kubernetes resources

2. Verify all pods are running

3. Access the application

4. Test Redis connectivity through the Flask app

### Task 2: Modify Configurations

1. Change the number of replicas to 2

2. Update the ConfigMap and restart pods

3. Add a new environment variable

4. Check how changes propagate

### Task 3: Monitoring and Logging

1. Install Kubernetes Dashboard:

```bash
minikube dashboard
```

2. View resource usage

3. Check pod logs

4. Monitor scaling events


### Task 4: Cleanup

```bash
# Delete all resources
kubectl delete -f ./

# Or delete namespace (deletes everything in namespace)
kubectl delete namespace cloud-course

# Clean Minikube
minikube stop
minikube delete
```

## Advanced Exercise: Create a Helm Chart
Create a ```Chart.yaml``` for packaging:

```Chart.yaml```

```yaml
apiVersion: v2
name: flask-redis-app
description: Flask + Redis application for cloud course
version: 0.1.0
appVersion: "1.0.0"
```

```values.yaml```

```yaml
# Flask configuration
flask:
  replicaCount: 3
  image:
    repository: flask-app
    tag: v1
    pullPolicy: IfNotPresent
  service:
    type: NodePort
    port: 80
  resources:
    requests:
      memory: 128Mi
      cpu: 100m
    limits:
      memory: 256Mi
      cpu: 200m

# Redis configuration
redis:
  enabled: true
  image:
    repository: redis
    tag: 7-alpine
  resources:
    requests:
      memory: 64Mi
      cpu: 100m
    limits:
      memory: 128Mi
      cpu: 200m
  persistence:
    enabled: true
    size: 1Gi
```

## Verification Checklist
✅ Minikube cluster is running
✅ Docker image is built in Minikube environment
✅ Namespace created successfully
✅ ConfigMap and Secrets deployed
✅ Redis deployment and service running
✅ Flask deployment and service running
✅ Pods are in "Running" state
✅ Services have valid endpoints
✅ Application responds to HTTP requests
✅ Redis connection is working
✅ Scaling operations work
✅ Rolling updates work


## Additional Resources for Students
1. Kubernetes Documentation: [https://kubernetes.io/docs/home/](https://kubernetes.io/docs/home/)

2. Minikube Guide: [https://minikube.sigs.k8s.io/docs/](https://minikube.sigs.k8s.io/docs/)

3. kubectl Cheat Sheet: [https://kubernetes.io/docs/reference/kubectl/cheatsheet/](https://kubernetes.io/docs/reference/kubectl/cheatsheet/)

4. Practice Environment: [https://killercoda.com/](https://killercoda.com/) (Free interactive K8s labs)

## This Kubernetes deployment example covers:

* Basic resource definitions (Deployments, Services)

* Configuration management (ConfigMaps, Secrets)

* Persistent storage

* Scaling and auto-scaling

* Service discovery and networking

* Health checks and probes

Students will learn how containerized applications transition from Docker/Docker Compose to production-grade Kubernetes deployments. 
