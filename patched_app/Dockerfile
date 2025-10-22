FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar utilidades del sistema necesarias (ping)
RUN apt-get update && apt-get install -y --no-install-recommends \
	iputils-ping \
 && rm -rf /var/lib/apt/lists/*

# Copiar requirements y instalar
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copiar aplicación
COPY . /app

# Exponer puerto que usa la app (5001)
EXPOSE 5001

# Entrypoint
CMD ["python", "app.py"]
