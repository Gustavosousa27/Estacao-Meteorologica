"""HTTP simulator; historical generation is an explicit demo-only DB command."""
import argparse
import json
import math
import random
import time
import urllib.request
from datetime import datetime, timedelta

def sample(station='demo-01', index=0):
    temperature = round(26 + 3*math.sin(index/25) + random.uniform(-.3,.3), 2)
    adc = random.randint(280, 430)
    gpio = round(adc*3300/4095)
    rain = random.random() < .12
    return dict(station_id=station, temperature_c=temperature,
        humidity_pct=round(random.uniform(62,80),1), pressure_hpa=round(random.uniform(918,925),2),
        bmp_temperature_c=round(temperature-.3,1), luminosity_lux=round(random.uniform(10,1200),1),
        gas_adc_raw=adc, gas_gpio_mv=gpio, gas_ao_mv_estimated=gpio*2,
        rain_detected=rain, rain_sensor_digital=0 if rain else 1)

def seed(hours):
    from app.database import SessionLocal
    from app.models import Station, Measurement
    from sqlalchemy import select
    with SessionLocal() as db:
        station = db.scalar(select(Station).where(Station.identifier=='demo-01'))
        if station and not station.is_demo:
            raise SystemExit('demo-01 existe como estação real; operação cancelada')
        if not station:
            station=Station(identifier='demo-01', name='Estação de demonstração',
                description='Dados fictícios gerados para testes', is_demo=True, location='Ambiente simulado')
            db.add(station); db.flush()
        now=datetime.utcnow()
        for i in range(hours*120):
            payload=sample(index=i); payload.pop('station_id')
            at=now-timedelta(seconds=(hours*120-1-i)*30)
            db.add(Measurement(station_id=station.id,received_at=at,**payload))
            if i%1000==0: db.flush()
        station.last_seen=now
        db.commit()
    print(f'{hours*120} medições fictícias criadas em demo-01 (demonstração).')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed-hours', type=int)
    parser.add_argument('--url', default='http://localhost:8080')
    parser.add_argument('--count',type=int,default=1)
    parser.add_argument('--interval',type=float,default=30)
    args=parser.parse_args()
    if args.seed_hours:
        if not 1<=args.seed_hours<=720: parser.error('Use 1 a 720 horas')
        seed(args.seed_hours); return
    if args.count<1 or args.interval<0: parser.error('count >= 1 e interval >= 0')
    # Verify demo label before posting; never send simulated data to a real station.
    with urllib.request.urlopen(args.url+'/api/stations', timeout=10) as response:
        stations=json.load(response)
    if not any(s['identifier']=='demo-01' and s['is_demo'] for s in stations):
        parser.error('Crie demo-01 com --seed-hours 1 antes de executar')
    for i in range(args.count):
        req=urllib.request.Request(args.url+'/api/measurements',data=json.dumps(sample(index=i)).encode(),
            headers={'Content-Type':'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=10) as response: print(response.read().decode())
        if i<args.count-1: time.sleep(args.interval)

if __name__=='__main__': main()
