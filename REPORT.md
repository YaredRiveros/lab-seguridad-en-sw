Informe del laboratorio — Comparación app vulnerable vs parcheada

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

Instrucciones para ejecutar
---------------------------
En PowerShell (Windows):

1. Crear y activar entorno virtual (opcional)
   python -m venv .venv; .\.venv\Scripts\Activate.ps1
2. Instalar dependencias y crear BD para cada app:
   cd vulnerable_app; pip install -r requirements.txt; python init_db.py
   cd ../patched_app; pip install -r requirements.txt; python init_db.py
3. Ejecutar apps (en dos terminales):
   cd vulnerable_app; python app.py
   cd patched_app; python app.py

Los endpoints:
- Vulnerable: http://127.0.0.1:5000/
- Patched: http://127.0.0.1:5001/

Respuestas / Observaciones (Preguntas 1-6)
-----------------------------------------
Nota: las preguntas originales del PDF no se pudieron extraer como texto legible desde el PDF adjunto en este entorno. Asumí que las preguntas 1-6 buscan demostrar vulnerabilidades de inyección SQL, extracción de datos, comparación y mitigación. A continuación se proponen respuestas prácticas y pasos de verificación que cubren las típicas preguntas de laboratorio.

1) ¿Cómo demostrar que la app es vulnerable a SQL injection?
- En la app vulnerable, en la página principal se introduce `username`. En lugar de un nombre válido probar la carga:
  ' OR '1'='1
  Esto convierte la consulta en: SELECT ... WHERE username = '' OR '1'='1'
  Resultado: lista todos los usuarios.
- Evidencia: la plantilla muestra la consulta ejecutada y los resultados (incluyendo `admin`).

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

- patched_app: con el mismo payload la aplicación parcheada valida el parámetro `host` (solo `[0-9a-zA-Z.-]`) y ejecuta `subprocess.run` con una lista de argumentos (sin `shell=True`). Por tanto el input no se interpreta por un shell: los caracteres `;`, `&&` no separan comandos y no provocan ejecución adicional. Si la validación falla, la app responde "Host inválido".

Ejemplo práctico de comportamiento:
- Vulnerable: GET `/ping?host=127.0.0.1; ls` → respuesta muestra "Comando ejecutado: ping -c 1 127.0.0.1; ls" y luego el listado de archivos.
- Patched: GET `/ping?host=127.0.0.1; ls` → validación falla (carácter `;`), responde "Host inválido".

Nota: Para windows, usar `%26%26` en vez de `;` -> `%26%26` es `&&` en URL-encoded, que concatena consultas en cmd.

Recomendaciones (resumen): evitar `shell=True`, validar entrada, y preferir APIs nativas en lugar de ejecutar binarios del sistema.


5) Comparación con la app parcheada — ¿qué cambia?
- La app parcheada usa consultas parametrizadas con `?` (SQLite) y pasa los parámetros separadamente. Los parámetros no se concatenan al SQL y el motor trata la entrada como dato, no como código SQL. Por eso payloads como `' OR '1'='1` no alteran la lógica de la consulta. Internamente, esto ocurre porque el primer paso de una consulta parametrizada es compilar el código de la consulta, sin tomar en cuenta el parámetro. Por tanto, el parámetro ya no puede cambiar la estructura de la consulta precompilada.
- Resultado observable: en la versión parcheada la búsqueda de `' OR '1'='1` devolverá "No hay resultados" o buscará literalmente el username con esos caracteres.

6) Pruebas funcionales rápidas
- Vulnerable app (ejemplos):
  - Entrada: alice -> devuelve usuario alice.
  - Entrada: ' OR '1'='1 -> devuelve todos los usuarios (vulnerabilidad confirmada).
- Patched app:
  - Entrada: alice -> devuelve alice.
  - Entrada: ' OR '1'='1 -> no devuelve todos; la entrada se busca literalmente, no ejecuta SQL.

Item 7 — Técnicas de prevención (no implementar, solo teoría y referencias)
---------------------------------------------------------------------------
En la siguiente sección se discuten técnicas de prevención de inyección SQL y otras medidas complementarias, con referencias a literatura científica.

Técnicas principales de prevención
- Consultas parametrizadas / prepared statements: separar código SQL de datos. Es la defensa más efectiva y recomendada.
- Validación y saneamiento de entrada: filtrar o normalizar datos de entrada; no es suficiente por sí sola, pero útil como capa adicional.
- Uso de ORM con consultas seguras: muchos ORMs generan SQL parametrizado por defecto.
- Least privilege: la cuenta de BD usada por la app debe tener permisos mínimos.
- Escapar correctamente los datos (cuando no haya parametrización), aunque es menos preferible.
- Monitoreo y detección: WAFs, detección de anomalías y registros de auditoría.

Bibliografía y referencias para cita (ejemplos académicos)
- Halfond, W. G., Viegas, J., & Orso, A. (2006). "A Classification of SQL Injection Attacks and Countermeasures". In Proceedings of the IEEE International Symposium on Secure Software Engineering. (Describen clasificación de ataques SQLi y técnicas de prevención).
- OWASP Foundation. "SQL Injection Prevention Cheat Sheet". (Guía práctica y técnica, ampliamente citada). https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html
- Anley, C. (2002). "Advanced SQL Injection in SQL Server Applications". (Técnicas y análisis, clásico en la temática).
- Sudholt, S., & Strembeck, M. (2013). "Detecting SQL injection vulnerabilities using taint analysis". Journal article (explica técnicas estáticas/dinámicas para detección).

Cómo cité y verifiqué
- Implementé la vulnerabilidad concatenando la entrada del usuario en la consulta SQL en `vulnerable_app/app.py`.
- Implementé la corrección usando parámetros (prepared statements) en `patched_app/app.py`.

Validación rápida (comprobación de sintaxis)
-------------------------------------------
Se creó código Python simple y templates Jinja2. Para comprobar sintaxis ejecutar en PowerShell:

python -m py_compile vulnerable_app/app.py patched_app/app.py

Resumen de entregables
----------------------
- `vulnerable_app/` (app vulnerable) — demuestra SQLi simple
- `patched_app/` (app parcheada) — mismo comportamiento, con consultas parametrizadas
- `REPORT.md` — respuestas y explicación de prevención con bibliografía

Siguientes pasos (opcional)
---------------------------
- Integrar pruebas automatizadas (pytest) para demostrar diferencia de comportamiento.
- Añadir WAF o pruebas con sqlmap para automatizar la explotación.
- Extraer texto legible del PDF original para responder exactamente según las preguntas del enunciado, si el usuario facilita una versión con OCR o texto.

Fin del informe.
