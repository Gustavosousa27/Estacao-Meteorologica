import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {AreaChart, Area, CartesianGrid, XAxis, YAxis, Tooltip, ResponsiveContainer} from 'recharts';
import {CloudSun, LayoutDashboard, RadioTower, Sun, Moon, Thermometer, Droplets, Gauge, Wind, CloudRain, RefreshCw, Bell, TriangleAlert, Info, House, ArrowRight, MapPin, Clock3} from 'lucide-react';
import './styles.css';
import {luminosityStatus} from './luminosity';

const metrics = [
  ['temperature_c','Temperatura','°C',Thermometer,'#e3974b',-40,80],
  ['humidity_pct','Umidade relativa','%',Droplets,'#4b9fe2',0,100],
  ['pressure_hpa','Pressão atmosférica','hPa',Gauge,'#a08be0',300,1100],
  ['luminosity_lux','Luminosidade','lux',Sun,'#d1ae45',0,200000],
  ['gas_adc_raw','Qualidade do ar','ADC',Wind,'#41b9aa',0,4095],
  ['rain_detected','Chuva','',CloudRain,'#668fe4',0,1]
];
const periods = [['1','Última hora'],['2','Últimas 2 horas'],['3','Últimas 3 horas'],['4','Últimas 4 horas'],['5','Últimas 5 horas'],['6','Últimas 6 horas'],['24','Últimas 24 horas'],['168','Últimos 7 dias'],['720','Últimos 30 dias'],['custom','Período personalizado']];
const value = (v, digits=1) => v == null ? 'Indisponível' : Number(v).toLocaleString('pt-BR',{maximumFractionDigits:digits});
async function api(path, options) {
  const response = await fetch('/api'+path, options);
  if (!response.ok) {
    let message = 'Não foi possível consultar o servidor';
    try {
      const body = await response.json();
      message = typeof body.detail === 'string' ? body.detail : (Array.isArray(body.detail) ? body.detail.map(e=>e.msg).join('; ') : 'Revise os campos informados');
    } catch {}
    throw new Error(message);
  }
  return response.json();
}
function ChartPanel({metric, series, formatTime}) {
  const [key,label,unit,Icon,color] = metric;
  return <article className="panel"><div className="chart-heading"><h3><Icon size={17} style={{color}}/>{label}</h3><span>{key==='rain_detected'?'Presença de água':unit}</span></div>
    {series.length ? <ResponsiveContainer width="100%" height={205}><AreaChart data={series} margin={{top:15,right:12,left:0,bottom:0}}>
      <defs><linearGradient id={'fill-'+key} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={color} stopOpacity={0.23}/><stop offset="100%" stopColor={color} stopOpacity={0}/></linearGradient></defs>
      <CartesianGrid strokeDasharray="3 5" vertical={false} stroke="var(--line)"/>
      <XAxis dataKey="received_at" tickFormatter={t=>formatTime(t,true)} minTickGap={45} tick={{fontSize:10,fill:'var(--muted)'}} axisLine={false} tickLine={false}/>
      <YAxis width={100} tickMargin={8} ticks={key==='rain_detected'?[0,1]:undefined} tick={{fontSize:10,fill:'var(--muted)'}} axisLine={false} tickLine={false} domain={key==='rain_detected'?[0,1]:['auto','auto']} tickFormatter={v=>key==='rain_detected'?(v===1?'Sim':v===0?'Não':''):value(v,1)+(unit==='%'?'':' ')+unit}/>
      <Tooltip labelFormatter={t=>formatTime(t)} formatter={v=>[key==='rain_detected'?(v?'Detectada':'Não detectada'):value(v)+' '+unit,label]} contentStyle={{background:'var(--panel)',border:'1px solid var(--line)',borderRadius:8}}/>
      <Area type={key==='rain_detected'?'stepAfter':'monotone'} dataKey={key} stroke={color} strokeWidth={2} fill={'url(#fill-'+key+')'} connectNulls={false} isAnimationActive={false}/>
    </AreaChart></ResponsiveContainer> : <div className="empty">Nenhuma medição neste período.<small>As leituras aparecerão quando a estação enviar dados.</small></div>}
  </article>;
}
function AlertPanel({alerts, formatTime}) {
  const alarmCount = alerts?.active.filter(a=>a.severity==='alarm').length || 0;
  const warningCount = alerts?.active.filter(a=>a.severity==='warning').length || 0;
  return <section className="panel alerts-panel" aria-labelledby="alerts-title">
    <div className="section-title"><div><h2 id="alerts-title"><Bell size={19}/>Avisos e alarmes atuais</h2><p>Informações e orientações para a população, conforme a última leitura da estação.</p></div></div>
    {!alerts ? <p className="muted">Aguardando consulta dos alarmes.</p> : <>
      <div className="alert-summary"><span className="severity-alarm">{alarmCount} {alarmCount===1?'alarme':'alarmes'}</span><span className="severity-warning">{warningCount} {warningCount===1?'aviso':'avisos'}</span></div>
      {alerts.state!=='online' ? <div className="alert-state"><Info size={19}/><div><strong>{alerts.state==='offline'?'Estação offline':'Aguardando a primeira leitura'}</strong><p>Não é possível avaliar as condições atuais sem uma leitura recente.</p></div></div> : alerts.active.length===0 && alerts.unavailable_rules.length===0 ? <div className="alert-state clear"><Bell size={19}/><div><strong>Nenhum aviso ou alarme no momento</strong></div></div> : null}
      <div className="active-alerts">{alerts.active.map((alarm,index)=>{
        const metric=metrics.find(m=>m[0]===alarm.metric);
        const rain=alarm.metric==='rain_detected';
        const Icon=alarm.severity==='alarm'?TriangleAlert:Info;
        return <article className={'active-alert '+alarm.severity} key={index}><Icon size={21}/><div><div className="alert-name"><strong>{alarm.name}</strong><span>{alarm.severity==='alarm'?'Alarme':'Aviso'}</span></div><p>{metric?.[1]}: <b>{rain?(alarm.current_value?'Chuva detectada':'Sem chuva'):value(alarm.current_value)+' '+metric?.[2]}</b></p>{alarm.observation&&<p className="advisory-observation">{alarm.observation}</p>}<small>Leitura: {formatTime(alerts.received_at)}</small></div></article>;
      })}</div>
      {alerts.unavailable_rules.length>0&&<div className="unavailable-alerts"><Info size={16}/><span>Sem leitura para avaliar avisos de: {[...new Set(alerts.unavailable_rules.map(r=>metrics.find(m=>m[0]===r.metric)?.[1]||r.metric))].join(', ')}.</span></div>}
    </>}
  </section>;
}
function MeasurementIcon({metric, lux, Icon, ...props}) {
  const Symbol=metric==='luminosity_lux'&&luminosityStatus(lux)==='Noite'?Moon:Icon;
  return <Symbol {...props}/>;
}
function LuminosityReading({lux}) {
  const available=typeof lux==='number'&&Number.isFinite(lux)&&lux>=0;
  return <div className="luminosity-reading" title="Classificação pela luz medida: Dia a partir de 100 lux; Noite abaixo de 100 lux."><strong className={!available?'missing':''}>{luminosityStatus(lux)}</strong>{available&&<span className="lux-value">{value(lux)} lux</span>}</div>;
}
function MetricCards({latest, online}) {
  return <div className="metrics">{metrics.map(([key,label,unit,Icon,color])=><article className="metric" key={key}><div className="metric-top"><span>{label}</span><MeasurementIcon metric={key} lux={latest?.luminosity_lux} Icon={Icon} size={20} style={{color}}/></div>{key==='luminosity_lux'?<LuminosityReading lux={latest?.[key]}/>:<><strong className={latest?.[key]==null?'missing':''}>{key==='rain_detected'?(latest?.[key]==null?'Indisponível':latest[key]?'Chuva detectada':'Sem chuva'):value(latest?.[key])}</strong>{key!=='rain_detected'&&<small>{unit}</small>}</>}<div className="metric-caption">{key==='luminosity_lux'?'Faixa estimada pela luz medida':key==='gas_adc_raw'?'Sensor MQ-135':key==='rain_detected'?'Presença de água · sem medida em mm':online?'Última leitura recebida':'Último valor recebido'}</div></article>)}</div>;
}
function HomePage({station, latest, busy, formatTime, onDetails, error, onRetry}) {
  const connected=!!station?.online;
  return <div className="public-home">
    <header className="public-topbar"><div className="public-brand"><CloudSun size={27}/><span>Estação Meteorológica<strong>Inteligente</strong></span></div></header>
    <main className="public-main">
      {error&&<div className="public-error" role="alert">{error}<button onClick={onRetry}>Tentar novamente</button></div>}
      <div className="public-intro"><h1>O ambiente em tempo real.</h1><p className="public-location"><MapPin size={15}/>Estação UNIP</p><span className={'public-status '+(connected?'is-online':'is-offline')}><i/>{!station?'Conectando à estação':connected?'Estação online':'Estação offline'}</span></div>
      <section className="public-temperature" aria-label="Temperatura atual"><Thermometer size={25}/><span>Temperatura</span><div className={latest?.temperature_c==null?'temperature-unavailable':''}><strong>{value(latest?.temperature_c)}</strong>{latest?.temperature_c!=null&&<span>°C</span>}</div></section>
      <section className="public-readings" aria-label="Leituras da estação">{metrics.slice(1).map(([key,label,unit,Icon])=><article key={key}><MeasurementIcon metric={key} lux={latest?.luminosity_lux} Icon={Icon} size={23}/><h2>{key==='rain_detected'?'Chuva':label}</h2>{key==='luminosity_lux'?<LuminosityReading lux={latest?.[key]}/>:<div className={latest?.[key]==null?'reading-unavailable':''}><strong>{key==='rain_detected'?(latest?.[key]==null?'Indisponível':latest[key]?'Chuva detectada':'Sem chuva'):value(latest?.[key])}</strong>{unit&&latest?.[key]!=null&&<span>{unit}</span>}</div>}<small>{key==='luminosity_lux'?'Faixa estimada pela luz medida':key==='gas_adc_raw'?'Sensor MQ-135':key==='rain_detected'?'Detecção de presença de água':''}</small></article>)}</section>
      <div className="public-measurement"><Clock3 size={14}/><span>Última medição: {formatTime(latest?.received_at)}</span>{busy&&<span role="status">· Atualizando…</span>}</div>
      {!connected&&station&&<p className="public-offline-note">{latest?'Estação offline. Os valores exibidos são da última medição recebida.':'Aguardando a primeira medição da estação.'}</p>}
      <div className="public-details"><button onClick={onDetails}>Ver mais detalhes<ArrowRight size={18}/></button><p>Explore os gráficos, os avisos e os alarmes da estação.</p></div>
    </main>
    <footer className="public-footer"><span>Projeto acadêmico · Monitoramento ambiental</span><a href="https://agenciadenoticias.ms.gov.br/operada-pelo-cemtec-ms-primeira-estacao-meteorologica-instalada-no-pantanal-comeca-a-transmitir-dados/" target="_blank" rel="noreferrer">Foto: Agência de Notícias de MS</a></footer>
  </div>;
}

function App() {
  const [page,setPage] = useState('home');
  const [station,setStation] = useState(null), [config,setConfig] = useState({timezone:'America/Sao_Paulo',offline_seconds:90});
  const [latest,setLatest] = useState(null), [series,setSeries] = useState([]), [summary,setSummary] = useState(null), [alerts,setAlerts] = useState(null);
  const [range,setRange] = useState('24'), [dates,setDates] = useState({start:'',end:''});
  const [error,setError] = useState(''), [readingError,setReadingError] = useState(''), [chartError,setChartError] = useState(''), [busy,setBusy] = useState(true), [refresh,setRefresh] = useState(0);
  const [dark,setDark] = useState(localStorage.getItem('weather-theme')==='dark');
  const formatTime = (t,short=false) => t ? new Date(t).toLocaleString('pt-BR',{timeZone:config.timezone,...(short?{hour:'2-digit',minute:'2-digit',day:'2-digit',month:'2-digit'}:{})}) : 'Sem comunicação';
  function navigate(next){setPage(next);setError('');window.scrollTo({top:0,behavior:'instant'});}
  useEffect(()=>{document.documentElement.dataset.theme=dark?'dark':'light';localStorage.setItem('weather-theme',dark?'dark':'light');},[dark]);
  useEffect(()=>{const timer=setInterval(()=>setRefresh(r=>r+1),10000);return()=>clearInterval(timer);},[]);
  useEffect(()=>{let active=true;
    Promise.all([api('/station'),api('/config')]).then(([s,c])=>{if(active){setStation(s);setConfig(c);}}).catch(e=>active&&setError(e.message)).finally(()=>active&&setBusy(false));
    return()=>{active=false};
  },[refresh]);
  useEffect(()=>{if(!station?.id)return;let active=true;setBusy(true);
    Promise.all([api(`/stations/${station.id}/latest`),api('/station/alerts')]).then(([l,a])=>{if(active){setLatest(l);setAlerts(a);setReadingError('');}}).catch(e=>{if(active){setReadingError(e.message);setLatest(null);setAlerts(null);}}).finally(()=>active&&setBusy(false));
    return()=>{active=false};
  },[station?.id,page,refresh]);
  useEffect(()=>{if(!station?.id||page!=='dashboard')return;let active=true;setChartError('');
    async function load(){
      try {
        let start,end;
        if(range==='custom'){
          if(!dates.start||!dates.end)throw new Error('Selecione início e fim do período');
          start=new Date(dates.start);end=new Date(dates.end);
          if(start>=end)throw new Error('O fim deve ser posterior ao início');
        }else{end=new Date();start=new Date(end.getTime()-Number(range)*3600000);}
        const query=new URLSearchParams({start:start.toISOString(),end:end.toISOString()});
        const bucket=Math.min(86400,Math.max(60,Math.ceil((end-start)/1000/400)));
        const [s,sum]=await Promise.all([api(`/stations/${station.id}/series?${query}&bucket_seconds=${bucket}`),api(`/stations/${station.id}/summary?${query}`)]);
        if(active){setSeries(s);setSummary(sum);}
      }catch(e){if(active){setChartError(e.message);setSeries([]);setSummary(null);}}
    }
    load();return()=>{active=false};
  },[station?.id,page,range,dates,refresh]);
  if(page==='home')return <HomePage station={station} latest={latest} busy={busy} formatTime={formatTime} onDetails={()=>navigate('dashboard')} error={error||readingError} onRetry={()=>setRefresh(r=>r+1)}/>;
  return <div className="shell"><aside><div className="brand"><div className="brand-icon"><CloudSun size={28}/></div><div><strong>Estação<span>Meteorológica Inteligente</span></strong></div></div>
    <p className="nav-label">MONITORAMENTO AMBIENTAL</p><nav>{[['home',House,'Início'],['dashboard',LayoutDashboard,'Monitoramento']].map(([id,Icon,label])=><button className={page===id?'active':''} key={id} onClick={()=>navigate(id)}><Icon size={19}/>{label}</button>)}</nav>
    <div className="aside-footer single-station-footer"><span className="dot"/> Atualização a cada 10 segundos</div></aside>
    <main><header><div><h1>Monitoramento</h1><p>Explore os gráficos e acompanhe os avisos para a população.</p></div><button className="icon-button" aria-label="Alternar tema" onClick={()=>setDark(!dark)}>{dark?<Sun size={20}/>:<Moon size={20}/>}</button></header>
      <div className="content">{error&&<div className="error" role="alert">{error} <button onClick={()=>setRefresh(r=>r+1)}>Tentar novamente</button></div>}
      {readingError&&<div className="error" role="alert">{readingError} <button onClick={()=>setRefresh(r=>r+1)}>Tentar novamente</button></div>}
      {page==='dashboard'&&<>
        {chartError&&<div className="error" role="alert">{chartError}</div>}
        <div className="toolbar"><div className="station-select single-station-label"><RadioTower size={19}/><strong>Estação UNIP</strong><span className={'badge '+(station?.online?'online':'offline')}>{station?.online?'Online':'Offline'}</span></div><div className="period"><select aria-label="Período dos gráficos" value={range} onChange={e=>setRange(e.target.value)}>{periods.map(([v,l])=><option value={v} key={v}>{l}</option>)}</select><button className="icon-button" aria-label="Atualizar" onClick={()=>setRefresh(r=>r+1)}><RefreshCw size={16} className={busy?'spin':''}/></button></div></div>
        {range==='custom'&&<div className="custom-dates"><label>Início (horário deste computador)<input type="datetime-local" value={dates.start} onChange={e=>setDates({...dates,start:e.target.value})}/></label><label>Fim (horário deste computador)<input type="datetime-local" value={dates.end} onChange={e=>setDates({...dates,end:e.target.value})}/></label></div>}
        <div className="context"><span>Localização: Unip - Alphaville</span><span>Horários em {config.timezone} · Offline após {config.offline_seconds}s</span></div>
        {busy&&<p role="status" className="loading">Atualizando dados…</p>}
        <div className="section-title"><h2>O ambiente agora</h2><span>Última leitura: {formatTime(latest?.received_at)}</span></div>
        <MetricCards latest={latest} online={station?.online}/>
        <div className="section-title charts-title"><div><h2>O ambiente ao longo do tempo</h2><p>Médias por intervalo; chuva indica presença em pelo menos uma amostra.</p></div><span>{summary?.count??0} medições no período</span></div>
        <div className="charts">{metrics.map(metric=><ChartPanel key={metric[0]} metric={metric} series={series} formatTime={formatTime}/>)}</div>
        <AlertPanel alerts={alerts} formatTime={formatTime}/>

      </>}
      <footer>Estação Meteorológica Inteligente<span>Projeto acadêmico · Monitoramento ambiental</span></footer>
      </div>
    </main>
  </div>;
}
createRoot(document.getElementById('root')).render(<App/>);