# HIT #2 — Sobel con Offloading en la Nube (Cloud-Bursting)

Implementación del operador Sobel distribuido con arquitectura híbrida:
el **master** corre localmente y los **workers** corren en VMs efímeras
en Google Cloud Platform, aprovisionadas con Terraform.
**RabbitMQ** corre en una VM fija en GCP como broker de mensajes.

---

## Arquitectura

```
LOCAL (on-premise)
┌─────────────────────┐
│  master.py          │──── publica chunks ────┐
│  (divide imagen)    │                        │
│  (reensambla)       │◄─── recibe resultados ─┤
└─────────────────────┘                        │
                                               ▼
GOOGLE CLOUD PLATFORM                  ┌──────────────┐
┌────────────────────────────────┐     │   RabbitMQ   │
│  VM fija: RabbitMQ             │     │  (VM fija)   │
│  ┌──────────────────────────┐  │     └──────┬───────┘
│  │ sobel_tasks queue        │  │            │
│  │ sobel_results queue      │  │     ┌──────┴───────┐
│  └──────────────────────────┘  │     │  round-robin │
│                                │     └──────┬───────┘
│  VMs efímeras (Terraform)      │            │
│  ┌──────────┐ ┌──────────┐     │    ┌───────┴──────────────┐
│  │ Worker 1 │ │ Worker N │     │    │ Worker 1 ... Worker N│
│  │ (Docker) │ │ (Docker) │     │    │ (VMs GCP efímeras)   │
│  └──────────┘ └──────────┘     │    └──────────────────────┘
└────────────────────────────────┘
         ▲
    Terraform crea/destruye
```

### Flujo de ejecución

1. Terraform crea la VM fija con RabbitMQ (solo la primera vez)
2. Terraform crea N VMs worker efímeras
3. Cada VM worker ejecuta un bootstrap: instala Docker, descarga la imagen del worker y lo ejecuta
4. El master local se conecta a RabbitMQ en GCP, divide la imagen y publica chunks
5. Los workers consumen chunks, aplican Sobel y publican resultados
6. El master reensambla la imagen final
7. `terraform destroy` elimina las VMs worker (la VM RabbitMQ persiste)

---

## Pre-requisitos

- **Cuenta GCP** con billing habilitado
- **gcloud CLI** instalado y autenticado (`gcloud auth login`)
- **Terraform** >= 1.6 instalado
- **Docker** instalado localmente
- **Cuenta Docker Hub** (para publicar la imagen del worker)
- **Bucket GCS** creado manualmente para el estado remoto de Terraform

---

## Instrucciones de ejecución

### Paso 1 — Crear bucket GCS para estado remoto (solo la primera vez)

```bash
gcloud storage buckets create gs://NOMBRE-BUCKET \
  --project=PROJECT_ID \
  --location=us-central1 \
  --uniform-bucket-level-access
```

### Paso 2 — Construir y publicar imagen Docker del worker

```bash
cd hit2/worker
docker build -t DOCKERHUB_USER/sobel-worker:latest .
docker push DOCKERHUB_USER/sobel-worker:latest
```

### Paso 3 — Configurar variables Terraform

```bash
cd hit2/terraform
cp terraform.tfvars.example terraform.tfvars
# Editar terraform.tfvars con valores reales:
#   project_id, worker_image, rabbitmq_pass, tfstate_bucket, etc.
```

### Paso 4 — Inicializar y aplicar Terraform

```bash
terraform init -backend-config="bucket=NOMBRE-BUCKET"
terraform plan
terraform apply
```

### Paso 5 — Obtener IP de RabbitMQ

```bash
terraform output rabbitmq_public_ip
```

### Paso 6 — Esperar bootstrap (~2 minutos) y correr master

```bash
cd hit2/master

# Copiar imagen de entrada
cp /ruta/a/imagen.jpg images/input.jpg

# Configurar variables de entorno
export RABBITMQ_HOST=$(cd ../terraform && terraform output -raw rabbitmq_public_ip)
export RABBITMQ_USER=admin
export RABBITMQ_PASS=TU_PASSWORD
export NUM_CHUNKS=4
export NUM_WORKERS=2

# Ejecutar master
docker compose run master
```

### Paso 7 — Ver imagen resultado

La imagen procesada queda en `hit2/master/images/output.jpg`.

### Paso 8 — Destruir solo workers (conservar RabbitMQ)

```bash
cd hit2/terraform
terraform destroy -target=google_compute_instance.worker_vms
```

### Paso 9 — Destruir toda la infraestructura

```bash
terraform destroy
```

---

## Análisis de performance

| Imagen | Workers locales (HIT #1) | Workers GCP | Tiempo total |
|--------|--------------------------|-------------|--------------|
| 1 MB   | 2                        | 0           | ?s           |
| 1 MB   | 0                        | 2           | ?s           |
| 1 MB   | 0                        | 4           | ?s           |
| 10 MB  | 0                        | 2           | ?s           |
| 10 MB  | 0                        | 4           | ?s           |

> **Nota:** Completar con valores reales luego de ejecutar las pruebas.

---

## Decisiones de diseño

### ¿Por qué RabbitMQ en VM fija y no efímera?

RabbitMQ actúa como broker central. Si se destruye entre ejecuciones, se pierden
las colas y los mensajes pendientes. Mantenerlo en una VM fija permite que los
workers se creen y destruyan libremente sin afectar la mensajería. Además, el
master local necesita una dirección IP estable para conectarse.

### ¿Por qué workers en VMs y no en Kubernetes?

El HIT #2 requiere demostrar el uso de IaC con Terraform para aprovisionar VMs.
Kubernetes (GKE) se aborda en el HIT #3. Usar VMs individuales permite entender
el patrón cloud-bursting a nivel de infraestructura sin la complejidad de un
orquestador de contenedores.

### ¿Por qué heartbeat=600 en las conexiones pika?

Las conexiones entre el master local y RabbitMQ en GCP atraviesan Internet,
con latencia variable y posibles micro-cortes. El heartbeat por defecto de pika
(60s) es demasiado agresivo para este escenario. Con 600s (10 minutos) se evitan
desconexiones espurias durante el procesamiento de imágenes grandes. El
`blocked_connection_timeout=300` complementa esto evitando que una conexión
bloqueada por flujo de control de RabbitMQ se cierre prematuramente.

### ¿Por qué templatefile() en lugar de hardcodear el bootstrap?

`templatefile()` permite parametrizar los scripts de bootstrap con variables
de Terraform (IP del RabbitMQ, credenciales, imagen Docker). Esto evita
hardcodear valores que cambian entre deployments y facilita la reutilización
del script con diferentes configuraciones.

### ¿Por qué backend remoto obligatorio?

El estado de Terraform (tfstate) contiene información sensible y es la fuente
de verdad de la infraestructura desplegada. Un backend remoto en GCS permite:
- Colaboración: múltiples desarrolladores pueden trabajar sobre el mismo estado
- CI/CD: los pipelines de GitHub Actions necesitan acceder al estado
- Seguridad: el estado no se commitea al repositorio
- Durabilidad: no se pierde si se borra el directorio local

### Tradeoffs de latencia local vs nube

El procesamiento Sobel es CPU-bound. Para imágenes pequeñas, la latencia de red
(serialización + envío de chunks a GCP + respuesta) puede superar el tiempo de
cómputo, haciendo que la versión local sea más rápida. Para imágenes grandes,
la paralelización en múltiples VMs compensa la latencia adicional. El punto de
quiebre depende del tamaño de imagen y la cantidad de workers.

---

## Configuración de Workload Identity Federation (CI/CD)

Para que los pipelines de GitHub Actions se autentiquen contra GCP sin service
account keys, configurar Workload Identity Federation:

### 1. Crear el pool de identidades

```bash
gcloud iam workload-identity-pools create "github-pool" \
  --project="PROJECT_ID" \
  --location="global" \
  --display-name="GitHub Actions Pool"
```

### 2. Crear el provider OIDC

```bash
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"
```

### 3. Crear service account

```bash
gcloud iam service-accounts create sa-github-terraform \
  --project="PROJECT_ID" \
  --display-name="GitHub Actions Terraform SA"
```

### 4. Asignar roles al service account

```bash
# Roles necesarios para crear VMs, redes, firewalls
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:sa-github-terraform@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/compute.admin"

gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:sa-github-terraform@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"
```

### 5. Vincular el pool con el service account

```bash
gcloud iam service-accounts add-iam-policy-binding \
  sa-github-terraform@PROJECT_ID.iam.gserviceaccount.com \
  --project="PROJECT_ID" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/GITHUB_ORG/TP3_SDyPP"
```

### 6. Obtener el identificador del provider

```bash
gcloud iam workload-identity-pools providers describe "github-provider" \
  --project="PROJECT_ID" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --format="value(name)"
```

El valor devuelto es el que se configura en el secret `GCP_WORKLOAD_IDENTITY_PROVIDER`.

### GitHub Secrets requeridos

| Secret                           | Descripción                                              |
|----------------------------------|----------------------------------------------------------|
| `GCP_PROJECT_ID`                 | ID del proyecto GCP                                      |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/NUM/locations/global/workloadIdentityPools/...` |
| `GCP_SERVICE_ACCOUNT`            | `sa-name@project.iam.gserviceaccount.com`                |
| `TF_STATE_BUCKET`                | Nombre del bucket GCS para el tfstate                    |
| `RABBITMQ_PASS`                  | Password de RabbitMQ                                     |
| `DOCKER_USERNAME`                | Usuario de Docker Hub                                    |
| `DOCKER_PASSWORD`                | Password/token de Docker Hub                             |

---

## Estructura del proyecto

```
hit2/
├── terraform/
│   ├── provider.tf
│   ├── variables.tf
│   ├── main.tf
│   ├── outputs.tf
│   └── terraform.tfvars.example
├── worker/
│   ├── worker.py
│   ├── sobel_core.py
│   ├── logger.py
│   ├── requirements.txt
│   └── Dockerfile
├── master/
│   ├── master.py
│   ├── sobel_core.py
│   ├── logger.py
│   ├── requirements.txt
│   ├── Dockerfile.master
│   ├── docker-compose.yml
│   └── images/
│       └── .gitkeep
├── scripts/
│   ├── worker_bootstrap.sh.tpl
│   └── rabbitmq_bootstrap.sh
├── .github/
│   └── workflows/
│       ├── terraform-plan.yml
│       ├── terraform-apply.yml
│       └── docker-build-push.yml
├── .gitignore (en raíz del repo)
└── README.md
```
