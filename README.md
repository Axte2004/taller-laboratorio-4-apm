# Taller de Laboratorio 4: APM y prueba de estrés

Implementación base del taller completamente dockerizada: API CRUD FastAPI, PostgreSQL con volumen persistente, trazas con Jaeger, métricas con Prometheus y paneles de Grafana. k6 ejecuta la carga en otro contenedor cuando se inicia expresamente.

## Requisitos y arranque

Solo se requiere Docker Desktop con Docker Compose v2. Desde esta carpeta:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
```

La API espera que PostgreSQL esté saludable, crea el esquema y carga 100 estudiantes semilla al iniciar por primera vez.

| Servicio | URL local | Uso |
|---|---|---|
| API / documentación | http://localhost:8000/docs | CRUD y pruebas manuales |
| Grafana | http://localhost:3000 | Usuario `admin`; clave definida en `.env` |
| Jaeger | http://localhost:16686 | Búsqueda de trazas del servicio `taller-crud` |
| Prometheus | http://localhost:9090 | Consulta directa de métricas |

Operaciones: `GET /students`, `GET /students/{id}`, `POST /students`, `PUT /students/{id}` y `DELETE /students/{id}`. La API expone métricas en `/metrics`. El panel de Grafana se provisiona como **Taller 4 - Rendimiento CRUD**.

## Instrumentación

- Prometheus recoge solicitudes, errores y duración por operación cada cinco segundos.
- Grafana calcula p50, p95 y p99 desde el histograma, y muestra RPS, tasa de error y conexiones activas a PostgreSQL.
- Jaeger recibe trazas OTLP. Cada solicitud contiene spans FastAPI y SQLAlchemy; en Jaeger se inspecciona el tiempo de aplicación y el span de consulta SQL.
- Límites para la prueba: app 1 CPU / 512 MB, base de datos 1 CPU / 512 MB, Jaeger 0.5 CPU / 512 MB, Grafana y Prometheus 0.5 CPU / 512 MB cada uno. k6 queda sin límite fijo; registre su propio uso durante la prueba para descartar que sea el cuello de botella.

## Prueba de carga

Los criterios previos están fijados en `INFORME.md` con fecha 2026-10-24. No cambie los umbrales después de observar resultados. El escenario usa seis escalones de tres minutos, precedidos por un minuto de calentamiento descartado:

```powershell
docker compose run --rm k6 run /scripts/stress.js
```

La mezcla declarada es 70 % lecturas (35 % listar y 35 % consultar), 20 % creación y 10 % actualización. Los datos enviados cambian en cada iteración. Si el equipo no soporta el escalón final, detenga la prueba y reduzca el último nivel antes de repetir; anote cualquier modificación para no comparar perfiles distintos.

Durante la carga, observe en otra consola:

```powershell
docker stats
```

El resumen de k6 aparece en la consola al finalizar. No reinicie PostgreSQL entre escalones. Las creaciones hacen crecer la tabla intencionalmente.

Al terminar, copie los resultados agregados de cada escalón a `resultados/mediciones.csv` (columnas: usuarios, peticiones/s, p95 en ms y error en porcentaje). Complete todas las seis filas y genere las gráficas en un contenedor:

```powershell
docker compose run --rm charts
```

Se guardan `usuarios_vs_rps.png`, `usuarios_vs_p95.png` y `usuarios_vs_error.png` dentro de `resultados/`.

## Parada y reinicio

```powershell
docker compose down
```

Esto conserva los volúmenes. Para borrar también los datos de PostgreSQL y Grafana:

```powershell
docker compose down -v
```

## Resultados medidos

La prueba terminó con seis escalones de tres minutos y un minuto de calentamiento descartado. El último escalón que cumplió los criterios fijados antes de medir fue **50 usuarios virtuales**, con **180,22 peticiones/s**, **p95 de 300 ms** y **0 % de respuestas HTTP fallidas**. A 100 usuarios el p95 subió a 1.000 ms y el throughput dejó de crecer. La CPU de la API alcanzó el límite de un núcleo.

En `resultados/` están el CSV completo, las muestras crudas, la salida de k6, una traza de Jaeger y las tres gráficas. El informe final en PDF y las capturas de pantalla se incluyen en el ZIP de entrega junto con este proyecto.

Si no tiene Docker instalado, abra el proyecto en GitHub Codespaces y use `docker compose -f docker-compose.codespaces.yml up --build -d`. Para repetir la medición completa: `COMPOSE_FILE=docker-compose.codespaces.yml python analysis/run_experiment.py`.
