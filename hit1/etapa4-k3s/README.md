# Etapa 4: Despliegue en Kubernetes (K3s)

Esta etapa consiste en orquestar el sistema distribuido de Sobel utilizando Kubernetes. Para este Hit #1, utilizaremos **K3s** y manejaremos las imágenes de forma **local** (sin registry externo).

## Requisitos Previos

1.  **K3s instalado** y funcionando.
2.  **Imágenes construidas localmente** en el demonio de Docker.

## Procedimiento de Despliegue

### 1. Construir las Imágenes

Desde la carpeta de la etapa anterior (o donde se encuentre el código fuente, ej: `etapa3-fault-tolerant`), construye las imágenes:

```bash
# Construir Worker
docker build -t sobel-worker:latest -f Dockerfile.worker .

# Construir Master
docker build -t sobel-master:latest -f Dockerfile.master .
```

### 2. Importar Imágenes a K3s

Como no usamos un registry, debemos "inyectar" las imágenes en el entorno de K3s. 

Si usas K3s estándar:
```bash
docker save sobel-worker:latest | sudo k3s ctr images import -
docker save sobel-master:latest | sudo k3s ctr images import -
```

Si usas **k3d**:
```bash
k3d image import sobel-worker:latest sobel-master:latest -c mi-cluster
```

### 3. Configurar el Almacenamiento

Antes de aplicar los manifiestos, asegúrate de que la ruta en `k3s/storage.yaml` sea correcta. El `hostPath` debe apuntar a la carpeta absoluta donde tienes las imágenes de entrada (ej: `maravilla.jpeg`).

```yaml
# k3s/storage.yaml
hostPath:
  path: /home/valentin/Proyectos/TP3_SDyPP/hit1/img
```

### 4. Aplicar Manifiestos

Sigue este orden para asegurar que los servicios y volúmenes estén listos:

```bash
# 1. Configuración y Almacenamiento
kubectl apply -f ../etapa4-k3s/k3s/configmap.yaml
kubectl apply -f ../etapa4-k3s/k3s/storage.yaml

# 2. Infraestructura (RabbitMQ)
kubectl apply -f ../etapa4-k3s/k3s/rabbitmq.yaml

# 3. Workers (esperar a que RabbitMQ esté Ready)
kubectl apply -f ../etapa4-k3s/k3s/workers.yaml

# 4. Ejecutar el Master (Job)
kubectl apply -f ../etapa4-k3s/k3s/master.yaml


# 5. Volver a correr el master (Job)
kubectl delete job sobel-master
kubectl apply -f ../etapa4-k3s/k3s/master.yaml
```


### 5. Monitoreo y Resultados

Para ver el progreso de los workers:
```bash
kubectl logs -l app=sobel-worker -f
```

Para ver el resultado del Master:
```bash
kubectl logs job/sobel-master
```

Una vez finalizado el Job, la imagen procesada aparecerá en tu carpeta local definida en el `hostPath` (ej: `images/resultado.jpg`).

### 6. Acceder a la Interfaz de RabbitMQ

El despliegue utiliza la imagen `rabbitmq:3-management`, lo que permite monitorear las colas visualmente. Para acceder desde tu navegador local:

1.  Ejecuta el port-forward:
    ```bash
    kubectl port-forward svc/rabbitmq 15672:15672
    ```
2.  Abre [http://localhost:15672](http://localhost:15672) en tu navegador.
3.  Ingresa con el usuario y contraseña por defecto: `guest` / `guest`.

## Notas Técnicas

- **imagePullPolicy: Never**: Los manifiestos están configurados para usar solo imágenes locales.
- **ConfigMap**: Centraliza la configuración de RabbitMQ y parámetros del algoritmo.
- **Job**: El Master se despliega como un Job ya que es una tarea que termina una vez procesada la imagen.
- **SecurityContext**: Los Pods corren con UID/GID 1000 para evitar crear archivos como `root` en el host.
