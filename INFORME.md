# Informe de resultados - Taller de Laboratorio 4

## Criterios de saturación declarados antes de medir

Fecha de declaración: **2026-10-24**. Se fijan antes de la primera ejecución; no se ajustarán tras observar los datos.

1. Tasa de error por escalón: **≤ 1 %**. Es error toda respuesta HTTP fuera del rango 2xx.
2. Latencia p95 por escalón: **≤ 500 ms**.
3. Throughput: debe seguir creciendo al aumentar usuarios; si queda igual o disminuye frente al escalón anterior, se considera aplanamiento.

El punto de saturación reportado será el último escalón que cumple simultáneamente los tres criterios. Latencia y errores se toman del APM; recursos, de `docker stats` y métricas PostgreSQL. El minuto de calentamiento no se analiza.

## Perfil reproducible

- Escalones definidos: 10, 25, 50, 100, 200 y 400 usuarios virtuales; duración de cada uno: 3 minutos.
- Mezcla: 35 % listar, 35 % consultar un registro, 20 % crear, 10 % actualizar.
- Los datos creados y actualizados varían por iteración.
- Límites: app 1 CPU/512 MB; PostgreSQL 1 CPU/512 MB; Jaeger 0.5 CPU/512 MB; Prometheus 0.5 CPU/512 MB; Grafana 0.5 CPU/512 MB.
- Anote aquí cualquier cambio de hardware, límites o escalones antes de repetir.

## Ficha del equipo

| Dato | Valor observado |
|---|---|
| Procesador | Pendiente de registrar |
| Núcleos / hilos | Pendiente de registrar |
| Memoria física | Pendiente de registrar |
| Sistema operativo y versión | Pendiente de registrar |
| Recursos asignados a Docker Desktop | Pendiente de registrar |
| Fecha y hora de ejecución | Pendiente de registrar |
| Versión de Docker | Docker 29.8.0 (verificada en este equipo) |

## Resultados por escalón

Completar después de ejecutar. Pet./s, percentiles y errores: Prometheus/Grafana; CPU y memoria: `docker stats`; conexiones: métrica `pg_stat_activity_count`. Use datos del tramo estable de cada escalón, no del calentamiento ni las transiciones.

| Esc. | Usuarios | Pet./s | p50 ms | p95 ms | p99 ms | Error % | CPU app % | CPU BD % | Mem app / BD MB | Conex. BD activas / máximo |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 10 | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente |
| 2 | 25 | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente |
| 3 | 50 | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente |
| 4 | 100 | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente |
| 5 | 200 | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente |
| 6 | 400 | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente | Pendiente |

## Límite observado

Último escalón que cumple los tres criterios: **pendiente de medición**. La infraestructura sostuvo **pendiente peticiones/s** con **pendiente usuarios virtuales**. Recurso que impuso el límite: **pendiente de evidencia**.

Adjuntar gráfica de usuarios vs. peticiones/s, usuarios vs. p95, usuarios vs. error, registro de uso de contenedores y una traza Jaeger con spans HTTP y SQL.

## Análisis basado en los datos

1. ¿Qué se degradó primero al cruzar el punto de saturación: latencia o error? ¿Qué indica ese orden? **Pendiente de medir y responder con escalones y valores.**
2. En una traza representativa, ¿qué proporción del tiempo se consume en la aplicación y en la base de datos? ¿Cómo cambia con la carga? **Pendiente de capturar y calcular.**
3. ¿El throughput creció en cada escalón o se aplanó? ¿En qué valor? **Pendiente de medir.**
4. ¿Qué se agotó primero: CPU, memoria o conexiones a la base de datos? Cite métricas de contenedores/APM. **Pendiente de medir.**
5. Proponga un cambio concreto para elevar el límite y explique qué medición sustenta la propuesta. **Pendiente de medir.**

## Capturas requeridas

- Servicio y solicitudes por operación en Grafana.
- Latencia p50/p95/p99.
- Tasa de error por operación.
- Una traza individual en Jaeger con span de aplicación y consulta SQL.
- `docker stats` durante el escalón de saturación.

## Declaración de uso de herramientas de inteligencia artificial

Se utilizó un asistente de inteligencia artificial para apoyar la creación de la estructura Docker, la instrumentación de ejemplo y el borrador de esta guía. El estudiante debe revisar, ejecutar, validar y adaptar el código, completar los resultados medidos y redactar las conclusiones con sus propias evidencias.
