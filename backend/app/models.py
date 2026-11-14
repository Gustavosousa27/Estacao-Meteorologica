from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

def utcnow():
    return datetime.utcnow()

class Station(Base):
    __tablename__ = 'stations'
    id: Mapped[int] = mapped_column(primary_key=True)
    identifier: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(String(500))
    location: Mapped[str | None] = mapped_column(String(200))
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime)

class Measurement(Base):
    __tablename__ = 'measurements'
    __table_args__ = (Index('ix_measurements_station_time', 'station_id', 'received_at', 'id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey('stations.id'))
    temperature_c: Mapped[float | None] = mapped_column(Float)
    humidity_pct: Mapped[float | None] = mapped_column(Float)
    pressure_hpa: Mapped[float | None] = mapped_column(Float)
    bmp_temperature_c: Mapped[float | None] = mapped_column(Float)
    luminosity_lux: Mapped[float | None] = mapped_column(Float)
    gas_adc_raw: Mapped[int | None] = mapped_column(Integer)
    gas_gpio_mv: Mapped[int | None] = mapped_column(Integer)
    gas_ao_mv_estimated: Mapped[int | None] = mapped_column(Integer)
    rain_detected: Mapped[bool | None] = mapped_column(Boolean)
    rain_sensor_digital: Mapped[int | None] = mapped_column(Integer)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AlarmRule(Base):
    __tablename__ = 'alarm_rules'
    id: Mapped[int] = mapped_column(primary_key=True)
    station_id: Mapped[int] = mapped_column(ForeignKey('stations.id'), index=True)
    name: Mapped[str] = mapped_column(String(120))
    metric: Mapped[str] = mapped_column(String(40))
    operator: Mapped[str] = mapped_column(String(8))
    threshold: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(12))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
