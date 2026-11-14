import os
os.environ['DATABASE_URL'] = 'sqlite://'
os.environ['ADMIN_PASSWORD'] = 'test-admin-password-000000'
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.database import Base, get_db
from app.main import app
from app.models import Station

@pytest.fixture
def client():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory=sessionmaker(engine,expire_on_commit=False)
    with factory() as db:
        db.add(Station(identifier='estacao-01',name='Teste',is_demo=False));db.commit()
    def database():
        with factory() as db: yield db
    app.dependency_overrides[get_db]=database
    with TestClient(app) as client: yield client
    app.dependency_overrides.clear()
    engine.dispose()

PAYLOAD=dict(station_id='estacao-01',temperature_c=28.7,humidity_pct=71.8,
    pressure_hpa=920.37,bmp_temperature_c=28.4,luminosity_lux=10.0,
    gas_adc_raw=318,gas_gpio_mv=397,gas_ao_mv_estimated=794,rain_detected=False,rain_sensor_digital=1)

def test_public_ingestion_and_nulls(client):
    assert client.post('/api/measurements',json=PAYLOAD).status_code==201
    assert not client.get('/openapi.json').json()['paths']['/api/measurements']['post'].get('security')
    assert client.post('/api/measurements',json={**PAYLOAD,'temperature_c':None}).status_code==201
    latest=client.get('/api/stations/1/latest').json()
    assert latest['temperature_c'] is None
    assert latest['gas_adc_raw']==318 and latest['rain_detected'] is False
    assert latest['received_at'].endswith('+00:00')
    assert client.get('/api/stations').json()[0]['online'] is True

@pytest.mark.parametrize('field,value',[('humidity_pct',101),('gas_adc_raw',4096),('rain_sensor_digital',2),('rain_detected','false'),('pressure_hpa',-1),('gas_gpio_mv',4000),('temperature_c',90),('extra_field',1)])
def test_validation(client,field,value):
    assert client.post('/api/measurements',json={**PAYLOAD,field:value}).status_code==422

def test_unknown_and_empty_station(client):
    assert client.get('/api/stations/1/latest').json() is None
    assert client.get('/api/stations/999/latest').status_code==404
    assert client.post('/api/measurements',json={'station_id':'unknown'}).status_code==404

def test_admin(client):
    data={'identifier':'demo-01','name':'Demo','is_demo':True}
    assert client.post('/api/stations',json=data).status_code==401
    assert client.post('/api/stations',json=data,auth=('admin','wrong')).status_code==401
    auth=('admin',os.environ['ADMIN_PASSWORD'])
    assert client.post('/api/stations',json=data,auth=auth).status_code==201
    assert client.post('/api/stations',json=data,auth=auth).status_code==409
    assert client.put('/api/stations/2',json={**data,'is_demo':False},auth=auth).status_code==422
    assert client.put('/api/stations/2',json={**data,'name':'Nova'},auth=auth).json()['name']=='Nova'

def test_history_series_summary_csv(client):
    for n in range(3):
        assert client.post('/api/measurements',json={**PAYLOAD,'temperature_c':20+n}).status_code==201
    start=(datetime.utcnow()-timedelta(hours=1)).isoformat()+'Z'
    end=(datetime.utcnow()+timedelta(hours=1)).isoformat()+'Z'
    query={'start':start,'end':end}
    h=client.get('/api/stations/1/measurements',params={**query,'limit':2,'page':2}).json()
    assert h['total']==3 and len(h['items'])==1
    summary=client.get('/api/stations/1/summary',params=query).json()
    assert summary['temperature_c_avg']==21 and summary['rain_samples']==0
    series=client.get('/api/stations/1/series',params={**query,'bucket_seconds':3600}).json()
    assert sum(r['samples'] for r in series)==3
    assert all(r['rain_detected']==0 for r in series)
    csv=client.get('/api/stations/1/export.csv',params=query)
    assert csv.status_code==200 and 'received_at_utc' in csv.text and 'estacao-01' in csv.text
    assert client.get('/api/stations/1/measurements',params={'start':end,'end':start}).status_code==422
    assert client.get('/api/stations/1/measurements',params={'start':'2026-01-01T00:00:00'}).status_code==422
    assert client.get('/api/stations/1/series').status_code==422
    assert client.get('/api/health').status_code==200
    assert 'ingestion_api_key' not in client.get('/api/config').json()

def test_offline(client):
    # A public station with no communication is offline, not a zero-valued reading.
    assert client.get('/api/stations').json()[0]['online'] is False



def test_fixed_public_advisories(client):
    station=client.get('/api/station').json()
    assert station['identifier']=='estacao-01'
    assert len(station['rules'])==5
    assert client.put('/api/station',json={'name':'Alterado','rules':[]}).status_code==405
    assert client.get('/api/station/alerts').json()['state']=='no_data'

@pytest.mark.parametrize('field,value,expected',[
    ('humidity_pct',39.9,['low_humidity']),('humidity_pct',40,[]),
    ('humidity_pct',75,[]),('humidity_pct',75.1,['high_humidity']),
    ('temperature_c',30,[]),('temperature_c',30.1,['hot_day']),
    ('temperature_c',15,[]),('temperature_c',14.9,['cold_day']),
    ('rain_detected',True,['rain']),('rain_detected',False,[])])
def test_public_advisory_thresholds(client,field,value,expected):
    assert client.post('/api/measurements',json={**PAYLOAD,field:value}).status_code==201
    result=client.get('/api/station/alerts').json()
    assert result['state']=='online'
    assert [r['code'] for r in result['active']]==expected

def test_public_messages_and_severity(client):
    assert client.post('/api/measurements',json={**PAYLOAD,'temperature_c':31,'humidity_pct':76,'rain_detected':True}).status_code==201
    result=client.get('/api/station/alerts').json()['active']
    assert [r['code'] for r in result]==['high_humidity','hot_day','rain']
    assert result[0]['severity']=='alarm' and result[0]['observation'] is None
    assert result[1]['severity']=='warning' and result[1]['name']=='É um dia quente, procure se hidratar mais.'
    assert result[2]['observation']=='Procure abrigo. Se você for dirigir, redobre a atenção.'
    assert client.post('/api/measurements',json={**PAYLOAD,'temperature_c':14,'humidity_pct':39}).status_code==201
    active=client.get('/api/station/alerts').json()['active']
    assert active[0]['name']=='A umidade do ar está abaixo do normal.'
    assert active[0]['observation']=='Procure se hidratar mais em tempos muito secos.'
    assert active[1]['name']=='É um dia frio, procure se agasalhar bem.'
    assert all(r['severity']=='warning' for r in active)

def test_null_sensors_do_not_trigger_public_advisories(client):
    assert client.post('/api/measurements',json={**PAYLOAD,'temperature_c':None,'humidity_pct':None,'rain_detected':None}).status_code==201
    result=client.get('/api/station/alerts').json()
    assert result['active']==[] and len(result['unavailable_rules'])==5
    assert result['enabled_rules']==5

def test_offline_never_shows_stale_advisory(client):
    assert client.post('/api/measurements',json={**PAYLOAD,'temperature_c':35}).status_code==201
    generator=app.dependency_overrides[get_db]()
    db=next(generator)
    db.get(Station,1).last_seen=datetime.utcnow()-timedelta(minutes=5)
    db.commit();generator.close()
    result=client.get('/api/station/alerts').json()
    assert result['state']=='offline' and result['active']==[]

def test_legacy_custom_rules_do_not_change_public_advisories(client):
    from app.models import AlarmRule
    generator=app.dependency_overrides[get_db]()
    db=next(generator)
    db.add(AlarmRule(station_id=1,name='Regra antiga',metric='temperature_c',operator='gt',threshold=0,severity='alarm',enabled=True))
    db.commit();generator.close()
    assert client.post('/api/measurements',json=PAYLOAD).status_code==201
    assert client.get('/api/station/alerts').json()['active']==[]

def test_demo_never_selected_as_primary(client):
    assert client.post('/api/stations',json={'identifier':'demo-01','name':'Demo','is_demo':True},
        auth=('admin',os.environ['ADMIN_PASSWORD'])).status_code==201
    assert client.post('/api/measurements',json={**PAYLOAD,'station_id':'demo-01'}).status_code==201
    assert client.get('/api/station').json()['identifier']=='estacao-01'
    assert client.get('/api/station/alerts').json()['state']=='no_data'
