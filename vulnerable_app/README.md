Vulnerable app (contenedor)

Construcción:

```powershell
docker build -t vulnerable_app:latest .
```

Ejecución:

```powershell
docker run --rm -p 5000:5000 --name vulnerable_app vulnerable_app:latest
```

La app escucha en el puerto 5000.
Vulnerable app

Instrucciones rápidas:

1. Crear entorno virtual (opcional)
   python -m venv .venv; .\.venv\Scripts\Activate.ps1
2. Instalar dependencias
   pip install -r requirements.txt
3. Inicializar DB
   python init_db.py
4. Ejecutar la app
   python app.py

La app corre en http://127.0.0.1:5000 y muestra una búsqueda vulnerable a SQL injection.
