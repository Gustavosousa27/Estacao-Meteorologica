import operator
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select
from .config import settings
from .models import Measurement, Station

# Fixed public advisories specified for the academic project.
PUBLIC_RULES = (
    dict(code='low_humidity',name='A umidade do ar está abaixo do normal.',
         observation='Procure se hidratar mais em tempos muito secos.',
         metric='humidity_pct',operator='lt',threshold=40,severity='warning',enabled=True),
    dict(code='high_humidity',name='A umidade está acima do esperado.',observation=None,
         metric='humidity_pct',operator='gt',threshold=75,severity='alarm',enabled=True),
    dict(code='hot_day',name='É um dia quente, procure se hidratar mais.',observation=None,
         metric='temperature_c',operator='gt',threshold=30,severity='warning',enabled=True),
    dict(code='cold_day',name='É um dia frio, procure se agasalhar bem.',observation=None,
         metric='temperature_c',operator='lt',threshold=15,severity='warning',enabled=True),
    dict(code='rain',name='Chuva detectada.',
         observation='Procure abrigo. Se você for dirigir, redobre a atenção.',
         metric='rain_detected',operator='eq',threshold=1,severity='warning',enabled=True),
)
OPERATORS = {'gt':operator.gt,'gte':operator.ge,'lt':operator.lt,
             'lte':operator.le,'eq':operator.eq,'ne':operator.ne}

def primary_station(db):
    # Demo data remains stored separately and never becomes the school's station.
    station = db.scalar(select(Station).where(Station.is_demo.is_(False)).order_by(Station.id).limit(1))
    if not station:
        raise HTTPException(503,'Estação principal não cadastrada')
    return station

def get_rules(db, station_id):
    # Stored rules from the former editor are retained but do not control public advisories.
    return [dict(rule) for rule in PUBLIC_RULES]

def evaluate_alerts(db, station):
    rules = get_rules(db, station.id)
    enabled = [rule for rule in rules if rule['enabled']]
    latest = db.scalar(select(Measurement).where(Measurement.station_id==station.id)
        .order_by(Measurement.received_at.desc(),Measurement.id.desc()).limit(1))
    online = bool(station.last_seen and
        (datetime.utcnow()-station.last_seen).total_seconds() <= settings().offline_seconds)
    result = {'state':'online' if online else ('offline' if latest else 'no_data'),
              'active':[], 'unavailable_rules':[], 'enabled_rules':len(enabled),
              'received_at':latest.received_at.isoformat()+'+00:00' if latest else None}
    if not online or not latest:
        return result
    for rule in enabled:
        current = getattr(latest,rule['metric'])
        if current is None:
            result['unavailable_rules'].append({'name':rule['name'],'metric':rule['metric']})
        elif OPERATORS[rule['operator']](current,rule['threshold']):
            result['active'].append({**rule,'current_value':current})
    result['active'].sort(key=lambda r:0 if r['severity']=='alarm' else 1)
    return result
