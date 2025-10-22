# Informe del laboratorio — Comparación app vulnerable vs parcheada

Resumen
-------
Se han creado dos aplicaciones web mínimas en Flask: `vulnerable_app` (puerto 5000) y `patched_app` (puerto 5001). Ambas usan SQLite y contienen una tabla `users` con usuarios de ejemplo (`alice`, `bob`, `admin`). La app vulnerable construye consultas SQL concatenando la entrada del usuario (vulnerable a SQLi). La app parcheada usa consultas parametrizadas.

Estructura del repositorio
--------------------------
- vulnerable_app/: app vulnerable (Flask), puerto 5000
  - app.py
  - init_db.py
  - templates/
  - requirements.txt
- patched_app/: app parcheada (Flask), puerto 5001
  - app.py
  - init_db.py
  - templates/
  - requirements.txt
- REPORT.md (este archivo)

Instrucciones para ejecutar (docker-compose)
---------------------------

Sigue estos pasos para ejecutar las dos aplicaciones dentro de contenedores Docker. Las instrucciones están escritas para PowerShell en Windows; en macOS/Linux los pasos son equivalentes adaptando la sintaxis de la shell.

Requisitos
- Tener instalado Docker Desktop (incluye Docker Engine y Docker Compose). Asegúrate de que Docker esté corriendo antes de continuar.

Pasos para clonar, construir y ejecutar (mínimos)
1. Clonar el repositorio:

  git clone <URL-del-repo>
  cd lab-seguridad-en-sw

2. Inicializar las bases de datos (opciones):

  a) Si tienes Python en el host (rápido):

    # En PowerShell (desde la raíz del repo)
    python vulnerable_app/init_db.py
    python patched_app/init_db.py

  b) Si NO tienes Python en el host: ejecutar la inicialización dentro de los contenedores usando Docker Compose (no modifica tu host):

    docker-compose run --rm vulnerable_app python init_db.py
    docker-compose run --rm patched_app python init_db.py

  Nota: tras los cambios recientes, los volúmenes del proyecto están montados en modo lectura/escritura por defecto, por lo que los archivos `data.db` y los logs que se creen dentro del contenedor aparecerán en las carpetas locales correspondientes.

3. Construir las imágenes con docker-compose (desde la raíz del repo):

  docker-compose build

4. Levantar los servicios (reconstruye si es necesario):

  docker-compose up --build

  - Esto expondrá `vulnerable_app` en el puerto 5000 de la máquina y `patched_app` en el puerto 5001 según `docker-compose.yml`.
  - Si prefieres ejecutar en segundo plano, añade `-d`:

    docker-compose up -d --build

5. Comprobar que las apps están corriendo:

  - Vulnerable: http://127.0.0.1:5000/
  - Patched:   http://127.0.0.1:5001/

6. Parar los servicios cuando termines:

  docker-compose down

Notas y recomendaciones (actualizadas)
- Los volúmenes en `docker-compose.yml` están montados en modo lectura/escritura para permitir que las aplicaciones creen archivos de log (`*.log`) y las bases de datos (`data.db`) dentro de las carpetas `vulnerable_app/` y `patched_app/`. Esto evita errores como "Read-only file system" cuando la app intenta abrir/crear logs.
- Las aplicaciones Flask están configuradas para escuchar en `0.0.0.0` dentro del contenedor, por lo que los puertos mapeados funcionan desde el host (es decir, `http://127.0.0.1:5000/` y `http://127.0.0.1:5001/` son accesibles desde tu navegador).
- Si prefieres no permitir que los contenedores escriban sobre el código fuente local, una alternativa más limpia es usar volúmenes nombrados para datos/logs. Ejemplo en `docker-compose.yml`:

  services:
   vulnerable_app:
    volumes:
      - ./vulnerable_app:/app:ro   # código en modo sólo lectura
      - vuln_data:/app/data       # volumen nombrado para DB/logs

  volumes:
   vuln_data:

  Con esto el código queda protegido y los datos/logs se almacenan en un volumen gestionado por Docker.
- Si tu profesor no tiene Python y prefieres inicializar las DB automáticamente al arrancar, puedo preparar una versión de los `Dockerfile` o un `entrypoint` que ejecute `init_db.py` durante el build o al inicio del contenedor.
- Observación: Docker Compose emite una advertencia si el campo `version` está presente en `docker-compose.yml` (en algunas versiones modernas de Compose la clave `version` ya no es necesaria). Puedes eliminar la línea `version: '3.8'` para evitar la advertencia, aunque no afecta el funcionamiento.

Fin de la sección Docker Compose.

SQL injection
-----------------------------------------
Nota: las preguntas originales del PDF no se pudieron extraer como texto legible desde el PDF adjunto en este entorno. Asumí que las preguntas 1-6 buscan demostrar vulnerabilidades de inyección SQL, extracción de datos, comparación y mitigación. A continuación se proponen respuestas prácticas y pasos de verificación que cubren las típicas preguntas de laboratorio.

1) ¿Cómo demostrar que la app es vulnerable a SQL injection?
- En la app vulnerable, en la página principal se introduce `username`. En lugar de un nombre válido probar la carga:
  ' OR '1'='1
  Esto convierte la consulta en: SELECT ... WHERE username = '' OR '1'='1'
  Resultado: lista todos los usuarios.
- Evidencia: la plantilla muestra la consulta ejecutada y los resultados (incluyendo `admin`).

Ejemplo de app vulnerable:
  <img width="1348" height="442" alt="image" src="https://github.com/user-attachments/assets/72269595-25f0-427e-9741-9d42bbf10b6c" />

Ejemplo de app parcheada:

<img width="1219" height="433" alt="image" src="https://github.com/user-attachments/assets/25e131c9-7e5f-4cfe-988b-e9a45e59a868" />
  
Se logra prevenir SQL injections usando consultas parametrizadas:

```python
db = get_db()
# Usar consulta parametrizada para prevenir SQL injection
query = "SELECT id, username, bio FROM users WHERE username = ?"
cur = db.cursor()
```

2) ¿Cómo extraer datos sensibles (por ejemplo, la contraseña o bio del admin)?
- En la DB de ejemplo el campo `bio` contiene texto que actúa como "secreto". Con inyección se puede forzar un `UNION` o seleccionar campos distintos. En SQLite, puede probarse:
  `' UNION SELECT 1, username, bio FROM users--`
  o usar boolean-based extraction si la app restringe el tipo de respuesta.
- En este laboratorio la forma más directa es `' OR '1'='1` para listar filas existentes.

3) ¿Cómo enumerar usuarios?
- Igual que 1), usar `' OR '1'='1` listará todos los registros. También usar patrones: `%` con LIKE si la aplicación tuviera filtros.

4) ¿Qué payloads se usaron y por qué funcionan?
- `' OR '1'='1` rompe la condición WHERE y la convierte en verdadera para todas las filas.
- `'; DROP TABLE users;--` (no usado aquí) es un ejemplo de payload de daño si el motor y la interfaz lo permitieran.
- `UNION SELECT` permite combinar resultados de otra consulta.


Command Injection (GET query payloads)
------------------------------------
Además de SQL injection, el laboratorio incluye un endpoint `/ping` que acepta el parámetro `host` por query string.

Ejemplos usando GET (payloads sobre la URL):
1) `/ping?host=127.0.0.1; ls`
2) `/ping?host=127.0.0.1&&id`

Comportamiento observado:
- vulnerable_app: la query string se concatena en un comando ejecutado con `shell=True`. Eso permite que operadores de shell (`;`, `&&`, `|`) introducidos por el atacante se ejecuten. En sistemas UNIX, `/ping?host=127.0.0.1; ls` ejecutará `ping -c 1 127.0.0.1; ls` y la salida de `ls` aparecerá en el cuerpo de la respuesta (texto plano). En Windows, se utiliza `&&` para concatenar consultas en shell y se usan las opciones `-n` en lugar de `-c` para el ping. 

<img width="1025" height="703" alt="image" src="https://github.com/user-attachments/assets/33ae6da3-f44f-4609-b967-9dd461dc4489" />

- patched_app: con el mismo payload la aplicación parcheada valida el parámetro `host` (solo `[0-9a-zA-Z.-]`) y ejecuta `subprocess.run` con una lista de argumentos (sin `shell=True`). Por tanto el input no se interpreta por un shell: los caracteres `;`, `&&` no separan comandos y no provocan ejecución adicional. Si la validación falla, la app responde "Host inválido".
<img width="952" height="305" alt="image" src="https://github.com/user-attachments/assets/712a2014-9c29-4991-b71c-129409e2113e" />

Ejemplo práctico de comportamiento:
- Vulnerable: GET `/ping?host=127.0.0.1; ls` → respuesta muestra "Comando ejecutado: ping -c 1 127.0.0.1; ls" y luego el listado de archivos.
- Patched: GET `/ping?host=127.0.0.1; ls` → validación falla (carácter `;`), responde "Host inválido".

La forma de mitigarla en el código fue evitando el uso del parámetro shell=True en la surinta subprocess.run:
```python
# Build argument list and execute without shell
if os.name == 'nt':
    cmd_list = ['ping', '-n', '1', host]
else:
    cmd_list = ['ping', '-c', '1', host]
try:
    proc = subprocess.run(cmd_list, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=10)
    output = proc.stdout
except Exception as e:
    output = str(e)
cmd = ' '.join(shlex.quote(p) for p in cmd_list)
```

Nota: Para windows, usar `%26%26` en vez de `;` -> `%26%26` es `&&` en URL-encoded, que concatena consultas en cmd.

Recomendaciones (resumen): evitar `shell=True`, validar entrada, y preferir APIs nativas en lugar de ejecutar binarios del sistema.

Ejemplos de logging
-------------------
Estos logs se pueden encontrar en las siguientes direcciones del repositorio en github patched_app/patched_app.log y vulnerable_app/vuln_app.log. A continuación se incluyen ejemplos reales extraídos de los ficheros de log de cada aplicación que muestran un intento de inyección por línea de comando usando `whoami`.:

- App vulnerable

<img width="951" height="390" alt="image" src="https://github.com/user-attachments/assets/f9317dcf-65f6-4543-9d7d-9f785f24dc43" />


- App parcheada
<img width="954" height="331" alt="image" src="https://github.com/user-attachments/assets/11a590b8-0df0-4b08-b927-a15dc61b0fea" />


Ambas aplicaciones detectaron la acción como sospechosa (campo `suspicious=True`), pero solo la versión parcheada evitó la ejecución del comando adicional `whoami` (la app parcheada valida el parámetro y ejecuta `ping` sin `shell=True`).


5) Comparación con la app parcheada
- La app parcheada usa consultas parametrizadas con `?` (SQLite) y pasa los parámetros separadamente. Los parámetros no se concatenan al SQL y el motor trata la entrada como dato, no como código SQL. Por eso payloads como `' OR '1'='1` no alteran la lógica de la consulta. Internamente, esto ocurre porque el primer paso de una consulta parametrizada es compilar el código de la consulta, sin tomar en cuenta el parámetro. Por tanto, el parámetro ya no puede cambiar la estructura de la consulta precompilada.
- Resultado observable: en la versión parcheada la búsqueda de `' OR '1'='1` devolverá "No hay resultados" o buscará literalmente el username con esos caracteres.

6) Pruebas funcionales rápidas
- Vulnerable app (ejemplos):
  - Entrada: alice -> devuelve usuario alice.
  - Entrada: ' OR '1'='1 -> devuelve todos los usuarios (vulnerabilidad confirmada).
- Patched app:
  - Entrada: alice -> devuelve alice.
  - Entrada: ' OR '1'='1 -> no devuelve todos; la entrada se busca literalmente, no ejecuta SQL.

## Item 7 - Técnicas principales de prevención

### 1. Consultas parametrizadas / prepared statements  
Separan el **código SQL** de los **datos proporcionados por el usuario**, evitando que estos últimos se interpreten como parte de una instrucción SQL.  
Los valores son enviados al motor de base de datos como **parámetros precompilados**, no como texto concatenado.  
Esto evita por completo la inyección de SQL, incluso si el atacante introduce caracteres especiales o sentencias maliciosas.  
Es la **defensa más efectiva y recomendada**, y está disponible en la mayoría de frameworks y librerías (por ejemplo, `cursor.execute(query, params)` en Python o `PreparedStatement` en Java).

---

### 2. Validación y saneamiento de entrada  
Implica **verificar que los datos cumplan con el formato esperado** (por ejemplo, que un ID sea numérico o un email tenga estructura válida).  
También se puede **normalizar o limpiar** la entrada eliminando caracteres no permitidos o codificando contenido especial.  
Si bien no evita por sí sola una inyección, **reduce la superficie de ataque** y previene otros problemas (como XSS o errores lógicos).  
Debe aplicarse **en la capa más cercana al punto de entrada** de los datos (formularios, APIs, etc.).

---

### 3. Uso de ORM con consultas seguras  
Los **Object-Relational Mappers (ORMs)** abstraen las consultas SQL en funciones o métodos, generando internamente SQL parametrizado.  
Ejemplos: SQLAlchemy, Django ORM, Hibernate.  
Mientras se usen **métodos ORM estándar** (sin concatenar cadenas SQL manualmente), el riesgo de inyección es muy bajo.  
Aun así, si se recurre a consultas "raw" (consultas crudas), deben seguir usándose **placeholders** o parámetros seguros.

---

### 4. Principio de menor privilegio (Least Privilege)  
La cuenta de base de datos utilizada por la aplicación debe tener **únicamente los permisos necesarios** (por ejemplo, `SELECT`, `INSERT`, pero no `DROP` o `ALTER`).  
Esto **limita el impacto** en caso de que una inyección ocurra: el atacante no podrá modificar la estructura ni acceder a datos sensibles fuera del alcance permitido.  
Idealmente, distintas partes del sistema deberían usar **credenciales con privilegios diferenciados**.

---

### 5. Escapar correctamente los datos (cuando no haya parametrización)  
Si por alguna razón no se puede usar parametrización, los datos deben ser **escapados o codificados** antes de insertarse en el SQL.  
Esto significa **neutralizar caracteres especiales** (`'`, `"`, `;`, `--`, etc.) que puedan alterar la lógica de la consulta.  
Sin embargo, este método **es propenso a errores** y depende del motor de base de datos (MySQL, PostgreSQL, etc.), por lo que solo se considera **una medida de último recurso**.

---

### 6. Monitoreo y detección  
El uso de **firewalls de aplicaciones web (WAFs)** puede ayudar a detectar y bloquear intentos conocidos de inyección SQL mediante patrones.  
Asimismo, el **registro y monitoreo de actividad** (auditoría de logs, detección de anomalías en consultas) permite **identificar comportamientos sospechosos** o patrones de ataque en tiempo real.  
No previene directamente la inyección, pero es una **defensa en profundidad** valiosa para detección temprana y respuesta.


Resumen de entregables
----------------------
- `vulnerable_app/` (app vulnerable) — demuestra SQLi simple y logging.
- `patched_app/` (app parcheada) — mismo comportamiento, con consultas parametrizadas, evita la introducción directamente en la shell, y presenta logging. 
- `REPORT.md` — respuestas y explicación de prevención con bibliografía

Fin del informe.






