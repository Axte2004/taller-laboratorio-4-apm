# Informe de la prueba medida

El informe final está en el PDF incluido en el paquete de entrega. Este archivo conserva un resumen de los resultados verificables del repositorio.

Se ejecutó un minuto de calentamiento y seis escalones de tres minutos: 10, 25, 50, 100, 200 y 400 usuarios virtuales. Se fijaron antes de medir los criterios de error HTTP <= 1 %, p95 <= 500 ms y throughput creciente.

El último escalón aceptable fue 50 usuarios virtuales: 180,22 peticiones/s, p95 de 300 ms y 0 % de errores. A 100 usuarios, el p95 subió a 1.000 ms y el throughput bajó a 175,81 peticiones/s. La API usó cerca de un núcleo completo, mientras PostgreSQL quedó por debajo del 16 % de CPU y las conexiones observadas no superaron 2 de 100. Por eso la CPU de la API fue el primer límite observado.

Las seis filas están en `resultados/mediciones_completas.csv`; las muestras originales, en `resultados/muestras.jsonl`. También se incluyen la salida de k6, tres gráficas y una traza individual. Jaeger se reinició durante la carga; la traza conservada se tomó después y no sirve para comparar proporciones por escalón.

Se usó un asistente de IA para preparar el entorno y redactar el informe. Las cifras provienen de la ejecución real.
