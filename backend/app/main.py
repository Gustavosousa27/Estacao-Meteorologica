import csv
import io
import logging
import secrets
from datetime import datetime, timezone
from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy import case, func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from .config import settings
from .database import get_db
from .models import Measurement, Station
from .schemas import Reading, StationInput
from .alarm_service import primary_station, get_rules, evaluate_alerts

logging.basicConfig(level=logging.INFO)
log = logging.getLogger('weather')
app = FastAPI(title='Estação Meteorológica Inteligente', version='1.0.0')
DB = Annotated[Session, Depends(get_db)]
basic = HTTPBasic()
FIELDS = [c.name for c in Measurement.__table__.columns if c.name not in ('id', 'station_id', 'received_at')]

def admin(credentials: Annotated[HTTPBasicCredentials, Depends(basic)]):
    s = settings()
    valid = secrets.compare_digest(credentials.username.encode(), s.admin_username.encode())
    valid &= secrets.compare_digest(credentials.password.encode(), s.admin_password.encode())
    if not valid:
        raise HTTPException(401, 'Credenciais inválidas', headers={'WWW-Authenticate': 'Basic'})

@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    log.warning('Validação rejeitada: %s %s campos=%s', request.method, request.url.path,
                [e['loc'] for e in exc.errors()])
    return JSONResponse(status_code=422, content={'detail': [
        {'loc': list(e['loc']), 'msg': e['msg'], 'type': e['type']} for e in exc.errors()]})

@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc: SQLAlchemyError):
    log.error('Falha de banco em %s (%s)', request.url.path, type(exc).__name__)
    return JSONResponse(status_code=503, content={'detail': 'Banco de dados indisponível'})

def stamp(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value else None

def station_dict(s):
    return dict(id=s.id, identifier=s.identifier, name=s.name, description=s.description,
        location=s.location, is_demo=s.is_demo, created_at=stamp(s.created_at),
        last_seen=stamp(s.last_seen), online=bool(s.last_seen and
        (datetime.utcnow()-s.last_seen).total_seconds() <= settings().offline_seconds))

def reading_dict(m):
    return dict(id=m.id, station_id=m.station_id, received_at=stamp(m.received_at),
                **{f: getattr(m, f) for f in FIELDS})

def station_or_404(db, id):
    s = db.get(Station, id)
    if not s:
        raise HTTPException(404, 'Estação não encontrada')
    return s

def period(start: datetime | None = None, end: datetime | None = None):
    def utc(d):
        if d and (d.tzinfo is None or d.utcoffset() is None):
            raise HTTPException(422, 'Informe datas com fuso horário, por exemplo Z ou -03:00')
        return d.astimezone(timezone.utc).replace(tzinfo=None) if d else None
    start, end = utc(start), utc(end)
    if start and end and start > end:
        raise HTTPException(422, 'Início deve preceder o fim')
    return start, end

def filters(id, bounds):
    conditions = [Measurement.station_id == id]
    start, end = bounds
    if start: conditions.append(Measurement.received_at >= start)
    if end: conditions.append(Measurement.received_at <= end)
    return conditions

@app.get('/api/health')
def health(db: DB):
    db.execute(text('SELECT 1'))
    return {'status': 'ok'}

@app.get('/api/config')
def config():
    return {'offline_seconds': settings().offline_seconds,
            'timezone': settings().interface_timezone, 'poll_seconds': 10}

@app.get('/api/stations')
def stations(db: DB):
    return [station_dict(s) for s in db.scalars(select(Station).order_by(Station.id))]

@app.post('/api/stations', dependencies=[Depends(admin)], status_code=201)
def create_station(body: StationInput, db: DB):
    s = Station(**body.model_dump())
    db.add(s)
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Identificador já cadastrado')
    return station_dict(s)

@app.put('/api/stations/{id}', dependencies=[Depends(admin)])
def update_station(id: int, body: StationInput, db: DB):
    s = station_or_404(db, id)
    if s.is_demo != body.is_demo:
        raise HTTPException(422, 'Tipo demonstração é imutável; cadastre outra estação')
    for k, v in body.model_dump().items(): setattr(s, k, v)
    try: db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Identificador já cadastrado')
    return station_dict(s)

@app.post('/api/measurements', status_code=201)
def receive(body: Reading, db: DB):
    s = db.scalar(select(Station).where(Station.identifier == body.station_id).with_for_update())
    if not s: raise HTTPException(404, 'Cadastre a estação antes de enviar medições')
    now = datetime.utcnow()
    m = Measurement(station_id=s.id, received_at=now, **body.model_dump(exclude={'station_id'}))
    s.last_seen = now
    db.add(m)
    db.commit()
    return {'success': True, 'message': 'Medicao registrada com sucesso', 'measurement_id': m.id}

@app.get('/api/stations/{id}/latest')
def latest(id: int, db: DB):
    station_or_404(db, id)
    m = db.scalar(select(Measurement).where(Measurement.station_id == id)
        .order_by(Measurement.received_at.desc(), Measurement.id.desc()).limit(1))
    return reading_dict(m) if m else None

@app.get('/api/stations/{id}/measurements')
def history(id: int, db: DB, bounds=Depends(period), page: int = Query(1, ge=1),
            limit: int = Query(50, ge=1, le=1000), order: str = Query('desc', pattern='^(asc|desc)$')):
    station_or_404(db, id)
    conditions = filters(id, bounds)
    total = db.scalar(select(func.count()).select_from(Measurement).where(*conditions))
    sort = [getattr(Measurement.received_at, order)(), getattr(Measurement.id, order)()]
    rows = db.scalars(select(Measurement).where(*conditions).order_by(*sort).offset((page-1)*limit).limit(limit))
    return {'items': [reading_dict(m) for m in rows], 'total': total, 'page': page, 'limit': limit}

@app.get('/api/stations/{id}/summary')
def summary(id: int, db: DB, bounds=Depends(period)):
    station_or_404(db, id)
    cols = [func.count().label('count')]
    for f in FIELDS:
        c = getattr(Measurement, f)
        if f == 'rain_sensor_digital': continue
        if f == 'rain_detected':
            cols.append(func.sum(case((c.is_(True), 1), else_=0)).label('rain_samples'))
        else:
            cols.extend([getattr(func, op)(c).label(f'{f}_{op}') for op in ('min', 'max', 'avg')])
    return dict(db.execute(select(*cols).where(*filters(id, bounds))).mappings().one())

@app.get('/api/stations/{id}/series')
def series(id: int, db: DB, bounds=Depends(period), bucket_seconds: int = Query(300, ge=60, le=86400)):
    station_or_404(db, id)
    start, end = bounds
    if not start or not end or (end-start).total_seconds()/bucket_seconds > 1000:
        raise HTTPException(422, 'Informe período e agregação com até 1000 intervalos')
    epoch = func.unix_timestamp(Measurement.received_at) if db.bind.dialect.name == 'mysql' else func.strftime('%s', Measurement.received_at).cast(__import__('sqlalchemy').Integer)
    bucket = func.floor(epoch / bucket_seconds) * bucket_seconds
    cols = [bucket.label('bucket'), func.count().label('samples')]
    for f in FIELDS:
        if f == 'rain_sensor_digital': continue
        c = getattr(Measurement, f)
        cols.append((func.max(case((c.is_(True), 1), (c.is_(False), 0), else_=None))
                     if f == 'rain_detected' else func.avg(c)).label(f))
    rows = db.execute(select(*cols).where(*filters(id, bounds)).group_by(bucket).order_by(bucket)).mappings()
    return [dict(received_at=datetime.fromtimestamp(float(r['bucket']), timezone.utc).isoformat(),
                 **{k: v for k,v in r.items() if k != 'bucket'}) for r in rows]

@app.get('/api/stations/{id}/export.csv')
def export(id: int, db: DB, bounds=Depends(period)):
    s = station_or_404(db, id)
    conditions = filters(id, bounds)
    count = db.scalar(select(func.count()).select_from(Measurement).where(*conditions))
    if count > 100000: raise HTTPException(422, 'CSV limitado a 100000 registros; reduza o período')
    out = io.StringIO(newline='')
    writer = csv.writer(out)
    writer.writerow(['station', 'is_demo', 'received_at_utc', *FIELDS])
    for m in db.scalars(select(Measurement).where(*conditions).order_by(Measurement.received_at, Measurement.id)):
        writer.writerow([s.identifier, s.is_demo, stamp(m.received_at), *[getattr(m, f) for f in FIELDS]])
    return Response('\ufeff'+out.getvalue(), media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition': f'attachment; filename="{s.identifier}.csv"'})


@app.get('/api/station')
def current_station(db: DB):
    station = primary_station(db)
    return {**station_dict(station), 'rules':get_rules(db,station.id)}

@app.get('/api/station/alerts')
def current_alerts(db: DB):
    return evaluate_alerts(db,primary_station(db))
