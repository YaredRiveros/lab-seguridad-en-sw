Arrancar las dos aplicaciones con Docker Compose

En Windows PowerShell desde la raíz del repo:

```powershell
# Construir y levantar ambos servicios
docker-compose up --build

# Levantar en background
docker-compose up -d --build

# Parar y eliminar
docker-compose down
```

Las apps estarán en:
- http://localhost:5000 -> vulnerable_app
- http://localhost:5001 -> patched_app

Por favor, lea el informe de la aplicación completa en REPORT.md

