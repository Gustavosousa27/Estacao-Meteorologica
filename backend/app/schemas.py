from pydantic import BaseModel, ConfigDict, Field

class Reading(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    station_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    temperature_c: float | None = Field(default=None, ge=-40, le=80)
    humidity_pct: float | None = Field(default=None, ge=0, le=100)
    pressure_hpa: float | None = Field(default=None, ge=300, le=1100)
    bmp_temperature_c: float | None = Field(default=None, ge=-40, le=85)
    luminosity_lux: float | None = Field(default=None, ge=0, le=200000)
    gas_adc_raw: int | None = Field(default=None, ge=0, le=4095, strict=True)
    gas_gpio_mv: int | None = Field(default=None, ge=0, le=3300, strict=True)
    gas_ao_mv_estimated: int | None = Field(default=None, ge=0, le=6600, strict=True)
    rain_detected: bool | None = Field(default=None, strict=True)
    rain_sensor_digital: int | None = Field(default=None, ge=0, le=1, strict=True)

class StationInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    identifier: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    location: str | None = Field(default=None, max_length=200)
    is_demo: bool = False


from typing import Literal
from pydantic import model_validator

class AlarmRuleInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, allow_inf_nan=False)
    name: str = Field(min_length=1, max_length=120)
    metric: Literal['temperature_c', 'humidity_pct', 'pressure_hpa', 'luminosity_lux', 'gas_adc_raw', 'rain_detected']
    operator: Literal['gt', 'gte', 'lt', 'lte', 'eq', 'ne']
    threshold: float
    severity: Literal['warning', 'alarm'] = 'warning'
    enabled: bool = True

    @model_validator(mode='after')
    def valid_threshold(self):
        limits = {'temperature_c': (-40,80), 'humidity_pct': (0,100),
                  'pressure_hpa': (300,1100), 'luminosity_lux': (0,200000),
                  'gas_adc_raw': (0,4095), 'rain_detected': (0,1)}
        low, high = limits[self.metric]
        if not low <= self.threshold <= high:
            raise ValueError(f'Limite deve estar entre {low} e {high}')
        if self.metric == 'rain_detected' and (self.operator not in ('eq','ne') or self.threshold not in (0,1)):
            raise ValueError('Para chuva, use igual/diferente de 0 ou 1')
        return self

class StationSettingsInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    location: str | None = Field(default=None, max_length=200)
    rules: list[AlarmRuleInput] = Field(default_factory=list, max_length=30)
