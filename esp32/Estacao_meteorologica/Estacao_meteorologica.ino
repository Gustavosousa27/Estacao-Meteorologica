
#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <DHT.h>
#include <Adafruit_BMP085.h>
#include <BH1750.h>
#include <ArduinoJson.h>
#include <math.h>


const char *WIFI_SSID = "ssid";

const char *WIFI_PASSWORD = "senha";

const char *API_URL =
  "http://ip-do-server:8080/api/measurements";

const char *STATION_ID = "estacao-01";

const unsigned long INTERVALO_POST_MS = 30000;

const unsigned long INTERVALO_WIFI_MS = 10000;

const int HTTP_TIMEOUT_MS = 8000;

#define PIN_DHT 4
#define PIN_MQ135 34
#define PIN_CHUVA 27
#define BMP_SDA 21
#define BMP_SCL 22
#define BH_SDA 18
#define BH_SCL 19


DHT dht(PIN_DHT, DHT22);
Adafruit_BMP085 bmp;
BH1750 bh1750;

TwoWire I2C_BH1750(1);

bool bmpOK = false;
bool bh1750OK = false;

unsigned long ultimoPost = 0;
unsigned long ultimaTentativaWifi = 0;


void colocarFloatOuNull(
  JsonDocument &doc,
  const char *campo,
  float valor
) {
  if (isfinite(valor)) {
    doc[campo] = valor;
  } else {
    doc[campo] = nullptr;
  }
}


void iniciarWifi() {

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("Conectando ao Wi-Fi");

  unsigned long inicio = millis();

  while (
    WiFi.status() != WL_CONNECTED &&
    millis() - inicio < 15000UL
  ) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {

    Serial.println("Wi-Fi conectado!");

    Serial.print("IP do ESP32: ");
    Serial.println(WiFi.localIP());

    Serial.print("Gateway: ");
    Serial.println(WiFi.gatewayIP());

    Serial.print("RSSI: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");

  } else {

    Serial.println(
      "Wi-Fi nao conectado. "
      "Nova tentativa sera realizada."
    );
  }
}


JsonDocument obterMedicoes() {

  JsonDocument doc;

  doc["station_id"] = STATION_ID;

  float temperatura = dht.readTemperature();
  float umidade = dht.readHumidity();

  colocarFloatOuNull(
    doc,
    "temperature_c",
    temperatura
  );

  colocarFloatOuNull(
    doc,
    "humidity_pct",
    umidade
  );

  if (bmpOK) {

    float pressao =
      bmp.readPressure() / 100.0f;

    float temperaturaBMP =
      bmp.readTemperature();

    colocarFloatOuNull(
      doc,
      "pressure_hpa",
      pressao
    );

    colocarFloatOuNull(
      doc,
      "bmp_temperature_c",
      temperaturaBMP
    );

  } else {

    doc["pressure_hpa"] = nullptr;
    doc["bmp_temperature_c"] = nullptr;
  }


  if (bh1750OK) {

    float luminosidade =
      bh1750.readLightLevel();

    if (
      isfinite(luminosidade) &&
      luminosidade >= 0
    ) {
      doc["luminosity_lux"] =
        luminosidade;
    } else {
      doc["luminosity_lux"] =
        nullptr;
    }

  } else {

    doc["luminosity_lux"] = nullptr;
  }


  uint32_t somaADC = 0;
  uint32_t somaMV = 0;

  const int NUM_LEITURAS = 20;

  for (int i = 0; i < NUM_LEITURAS; i++) {

    somaADC += analogRead(PIN_MQ135);

    somaMV +=
      analogReadMilliVolts(PIN_MQ135);

    delay(5);
  }

  int valorADC =
    (somaADC + NUM_LEITURAS / 2) /
    NUM_LEITURAS;

  int tensaoGPIO =
    (somaMV + NUM_LEITURAS / 2) /
    NUM_LEITURAS;


  int tensaoMQ = tensaoGPIO * 2;

  doc["gas_adc_raw"] = valorADC;

  doc["gas_gpio_mv"] = tensaoGPIO;

  doc["gas_ao_mv_estimated"] = tensaoMQ;


  int sinalChuva = digitalRead(PIN_CHUVA);

  doc["rain_sensor_digital"] =
    sinalChuva;


  doc["rain_detected"] =
    (sinalChuva == LOW);

  return doc;
}

void enviarMedicoes() {

  JsonDocument doc = obterMedicoes();

  String json;

  serializeJson(doc, json);

  Serial.println();
  Serial.println("==============================");
  Serial.println("       NOVA MEDICAO");
  Serial.println("==============================");


  serializeJsonPretty(doc, Serial);
  Serial.println();

  if (WiFi.status() != WL_CONNECTED) {

    Serial.println(
      "POST nao enviado: Wi-Fi desconectado."
    );

    return;
  }

  HTTPClient http;

  http.setTimeout(HTTP_TIMEOUT_MS);

  if (!http.begin(API_URL)) {

    Serial.println(
      "Erro ao inicializar requisicao HTTP."
    );

    return;
  }

  http.addHeader(
    "Content-Type",
    "application/json"
  );

  int status = http.POST(json);

  Serial.println();
  Serial.print("HTTP status: ");
  Serial.println(status);

  if (status > 0) {

    String resposta = http.getString();

    Serial.print("Resposta da API: ");
    Serial.println(resposta);

    if (status == 200 || status == 201) {

      Serial.println(
        "Medicao enviada com sucesso!"
      );

    } else if (status == 400) {

      Serial.println(
        "Erro: requisicao invalida."
      );

    } else if (status == 404) {

      Serial.println(
        "Erro: rota ou estacao nao encontrada."
      );

    } else if (status == 422) {

      Serial.println(
        "Erro: dados rejeitados pela API."
      );

    } else if (status >= 500) {

      Serial.println(
        "Erro interno no servidor."
      );

    } else {

      Serial.println(
        "Resposta HTTP inesperada."
      );
    }

  } else {

    Serial.print("Falha HTTP: ");

    Serial.println(
      http.errorToString(status)
    );
  }

  http.end();
}


void setup() {

  Serial.begin(115200);

  delay(1500);

  Serial.println();
  Serial.println("==============================");
  Serial.println(" ESTACAO METEOROLOGICA ESP32");
  Serial.println("==============================");

  dht.begin();

  Serial.println("DHT22 inicializado!");


  Wire.begin(BMP_SDA, BMP_SCL);

  bmpOK = bmp.begin();

  Serial.print("BMP180: ");

  Serial.println(
    bmpOK ? "OK" : "NAO ENCONTRADO"
  );


  I2C_BH1750.begin(BH_SDA, BH_SCL);

  bh1750OK = bh1750.begin(
    BH1750::CONTINUOUS_HIGH_RES_MODE,
    0x23,
    &I2C_BH1750
  );

  Serial.print("BH1750: ");

  Serial.println(
    bh1750OK ? "OK" : "NAO ENCONTRADO"
  );



  analogReadResolution(12);

  analogSetPinAttenuation(
    PIN_MQ135,
    ADC_11db
  );


  pinMode(PIN_CHUVA, INPUT);

  Serial.println();
  Serial.println("Sensores inicializados!");
  Serial.println();


  iniciarWifi();

  ultimaTentativaWifi = millis();

 
  ultimoPost = millis() - INTERVALO_POST_MS;
}


void loop() {

  unsigned long agora = millis();


  if (
    WiFi.status() != WL_CONNECTED &&
    agora - ultimaTentativaWifi >=
      INTERVALO_WIFI_MS
  ) {

    ultimaTentativaWifi = agora;

    Serial.println(
      "Tentando reconectar ao Wi-Fi..."
    );

    WiFi.reconnect();
  }

  if (
    agora - ultimoPost >=
      INTERVALO_POST_MS
  ) {

    ultimoPost = agora;

    enviarMedicoes();
  }

  delay(100);
}
