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
```bash
docker.io/library/sobel-worker:latest                                                                              application/vnd.oci.image.index.v1+json                   sha256:843a9ad48220e3055fa7f6b6e56c42be295f021cedd6c5885eeb9b5818994781 75.2 MiB  linux/amd64                                                                                            io.cri-containerd.image=managed 
```

## Hello World: deployar nginx para validar que todo funciona

```html
valentin@Debian:~/Proyectos/TP3_SDyPP$ curl http://localhost:8080
<!DOCTYPE html>
<html>
<head>
<title>Welcome to nginx!</title>
<style>
html { color-scheme: light dark; }
body { width: 35em; margin: 0 auto;
font-family: Tahoma, Verdana, Arial, sans-serif; }
</style>
</head>
<body>
<h1>Welcome to nginx!</h1>
<p>If you see this page, nginx is successfully installed and working.
Further configuration is required for the web server, reverse proxy, 
API gateway, load balancer, content cache, or other features.</p>

<p>For online documentation and support please refer to
<a href="https://nginx.org/">nginx.org</a>.<br/>
To engage with the community please visit
<a href="https://community.nginx.org/">community.nginx.org</a>.<br/>
For enterprise grade support, professional services, additional 
security features and capabilities please refer to
<a href="https://f5.com/nginx">f5.com/nginx</a>.</p>

<p><em>Thank you for using nginx.</em></p>
</body>
</html>
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

- [x] `kubectl get nodes` devuelve el nodo en estado `Ready`
- [x] `kubectl get pods -A` no muestra pods en `CrashLoopBackOff` ni `Pending`
- [x] Imagen local importada y visible con `k3s ctr images list`
- [x] `kubectl version` muestra versión compatible de cliente y servidor
- [x] `~/.kube/config` configurado (kubectl funciona sin sudo)
