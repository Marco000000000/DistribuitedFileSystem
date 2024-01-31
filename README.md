# Istruzioni per il deploy:

1. Scaricare [Docker Desktop](https://www.docker.com/products/docker-desktop) dal sito ufficiale ed installare l'ambiente Kubernetes associato.

2. Una volta scaricato il progetto, utilizzare il comando:
   ```bash
   docker-compose build```
oppure, se si utilizza Linux e non è stato attivato l'alias docker-compose, utilizzare il comando:

```bash
docker compose build ```

Successivamente, lanciare il comando:

```bash
kubectl apply -f startall.yaml ```

