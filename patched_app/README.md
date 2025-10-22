Patched app (contenedor)

Construcción:

```powershell
docker build -t patched_app:latest .
```

Ejecución:

```powershell
docker run --rm -p 5001:5001 --name patched_app patched_app:latest
```

La app escucha en el puerto 5001.
Patched app

Instrucciones rápidas:

1. Crear entorno virtual (opcional)
   python -m venv .venv; .\.venv\Scripts\Activate.ps1
2. Instalar dependencias
   pip install -r requirements.txt
3. Inicializar DB
   python init_db.py
4. Ejecutar la app
   python app.py

La app corre en http://127.0.0.1:5001 y está parcheada contra SQL injection usando consultas parametrizadas.
