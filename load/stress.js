import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE = __ENV.BASE_URL || 'http://localhost:8000';
const stepDuration = '3m';

// Criterios definidos antes de ejecutar: error <= 1 %, p95 <= 500 ms y
// throughput creciente entre escalones. También están en INFORME.md.
export const options = {
  scenarios: {
    warmup: { executor: 'constant-vus', vus: 3, duration: '1m', startTime: '0s', exec: 'warmup', gracefulStop: '10s' },
    step_1_10_vus: { executor: 'constant-vus', vus: 10, duration: stepDuration, startTime: '1m', exec: 'mixedWorkload', gracefulStop: '10s' },
    step_2_25_vus: { executor: 'constant-vus', vus: 25, duration: stepDuration, startTime: '4m', exec: 'mixedWorkload', gracefulStop: '10s' },
    step_3_50_vus: { executor: 'constant-vus', vus: 50, duration: stepDuration, startTime: '7m', exec: 'mixedWorkload', gracefulStop: '10s' },
    step_4_100_vus: { executor: 'constant-vus', vus: 100, duration: stepDuration, startTime: '10m', exec: 'mixedWorkload', gracefulStop: '10s' },
    step_5_200_vus: { executor: 'constant-vus', vus: 200, duration: stepDuration, startTime: '13m', exec: 'mixedWorkload', gracefulStop: '10s' },
    step_6_400_vus: { executor: 'constant-vus', vus: 400, duration: stepDuration, startTime: '16m', exec: 'mixedWorkload', gracefulStop: '10s' },
  },
  summaryTrendStats: ['avg', 'min', 'med', 'p(90)', 'p(95)', 'p(99)', 'max'],
};

export function warmup() {
  const response = http.get(`${BASE}/students?limit=20`);
  check(response, { 'calentamiento responde 200': (r) => r.status === 200 });
  sleep(0.2);
}

function requestOk(response, expected, label) {
  check(response, { [label]: (r) => r.status === expected });
}

export function mixedWorkload() {
  const roll = Math.random() * 100;
  const unique = `${__VU}-${__ITER}-${Date.now()}-${Math.floor(Math.random() * 1e9)}`;
  if (roll < 35) {
    const offset = Math.floor(Math.random() * 80);
    requestOk(http.get(`${BASE}/students?limit=20&offset=${offset}`), 200, 'listar estudiantes');
  } else if (roll < 70) {
    const id = 1 + Math.floor(Math.random() * 100);
    requestOk(http.get(`${BASE}/students/${id}`), 200, 'consultar estudiante');
  } else if (roll < 90) {
    const payload = JSON.stringify({ name: `Carga ${unique}`, email: `carga-${unique}@taller.local`, note: `dato-${Math.random()}` });
    requestOk(http.post(`${BASE}/students`, payload, { headers: { 'Content-Type': 'application/json' } }), 201, 'crear estudiante');
  } else {
    const id = 1 + Math.floor(Math.random() * 100);
    const payload = JSON.stringify({ name: `Actualizado ${unique}`, email: `estudiante${id}@taller.local`, note: `nota-${unique}` });
    requestOk(http.put(`${BASE}/students/${id}`, payload, { headers: { 'Content-Type': 'application/json' } }), 200, 'actualizar estudiante');
  }
  sleep(0.1);
}
