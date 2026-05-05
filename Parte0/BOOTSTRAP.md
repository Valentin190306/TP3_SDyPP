# TP3 — Parte 0: Bootstrap del Cluster Kubernetes

## Entorno

| Campo | Valor |
|-------|-------|
| OS | Ubuntu 26.04 LTS |
| Kernel | 7.0.0-15-generic |
| RAM disponible | 16 GB |
| Docker version | 29.4.1 |
| Herramienta k8s | k3s |

---

## Prerrequisitos verificados

```bash
docker version
docker ps
kubectl version --client
```

Salida `kubectl version --client`:
```
Client Version: v1.36.0
Kustomize Version: v5.8.1
```

---

## Instalación

### Opción elegida: k3s *(Linux nativo / WSL2)*

```bash
curl -sfL https://get.k3s.io | sh -
```

Duración aproximada: `144 segundos`

### Configuración de kubectl sin sudo

```bash
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config
chmod 600 ~/.kube/config
```

---

## Verificación del cluster

```bash
kubectl get nodes
```

Salida:
```
NAME      STATUS   ROLES           AGE     VERSION
gustavo   Ready    control-plane   2d10h   v1.35.4+k3s1
```

Estado esperado del nodo: `Ready` con rol `control-plane`.

```bash
kubectl get pods -A
```

Salida:
```
NAMESPACE     NAME                                      READY   STATUS      RESTARTS        AGE
default       inspector                                 0/1     Unknown     0               2d8h
kube-system   coredns-c4dbffb5f-4qcmz                   1/1     Running     5 (153m ago)    2d10h
kube-system   helm-install-traefik-crd-bhzzv            0/1     Completed   0               2d10h
kube-system   helm-install-traefik-zxff9                0/1     Completed   1               2d10h
kube-system   local-path-provisioner-5c4dc5d66d-qsvk5   1/1     Running     5 (153m ago)    2d10h
kube-system   metrics-server-786d997795-khwmp           1/1     Running     5 (153m ago)    2d10h
kube-system   svclb-traefik-3048be1e-54jk2              2/2     Running     10 (153m ago)   2d10h
kube-system   traefik-9bcdbbd9-dfmfd                    1/1     Running     5 (153m ago)    2d10h
```

Todos los pods del namespace `kube-system` deben estar en `Running` o `Completed`.

---

## Carga de imagen local

k3s usa `containerd` como runtime, no Docker. Las imágenes construidas con `docker build` deben importarse explícitamente.

```bash
docker save sobel-worker:latest | sudo k3s ctr images import -
```

Verificación:
```bash
sudo k3s ctr images list | grep [nombre-imagen]
```

Salida:
```
docker.io/library/sobel-worker:latest                                                                              application/vnd.oci.image.manifest.v1+json                sha256:f688cb741f1cee58cb5a52a319aa3ce769a8332e04d0f7044302539dcb6726f0 224.7 MiB linux/amd64                                                                                                         io.cri-containerd.image=managed 
```

---

## Comandos de referencia rápida

| Comando | Descripción |
|---------|-------------|
| `kubectl get nodes` | Estado de los nodos |
| `kubectl get pods -A` | Todos los pods de todos los namespaces |
| `kubectl get deploy` | Deployments |
| `kubectl get svc` | Services |
| `kubectl describe pod <nombre>` | Detalles y eventos de un pod |
| `kubectl logs <pod>` | Logs del pod |
| `kubectl logs -f <pod>` | Logs en streaming |
| `kubectl apply -f archivo.yaml` | Crear/actualizar recursos |
| `kubectl delete -f archivo.yaml` | Borrar recursos |
| `kubectl exec -it <pod> -- /bin/sh` | Shell dentro del pod |
| `kubectl get events --sort-by='.lastTimestamp'` | Eventos ordenados por fecha |

---

## Desinstalación

```bash
sudo /usr/local/bin/k3s-uninstall.sh
```

Elimina binario, servicio systemd, datos del cluster y redes.

---

## Checklist de validación

- [ ] `kubectl get nodes` devuelve el nodo en estado `Ready`
- [ ] `kubectl get pods -A` no muestra pods en `CrashLoopBackOff` ni `Pending`
- [ ] Imagen local importada y visible con `k3s ctr images list`
- [ ] `kubectl version` muestra versión compatible de cliente y servidor
- [ ] `~/.kube/config` configurado (kubectl funciona sin sudo)
