// Visual classification configured for the academic project; readings remain in lux.
export function luminosityStatus(lux) {
  if (typeof lux !== 'number' || !Number.isFinite(lux) || lux < 0) return 'Indisponível';
  return lux >= 100 ? 'Dia' : 'Noite';
}