
#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <DHT.h>
#include <Adafruit_BMP085.h>
#include <BH1750.h>
#include <ArduinoJson.h>
#include <math.h>

// ==========================================
// CONFIGURACAO WIFI E SERVIDOR
// ==========================================

const char *WIFI_SSID = "CLARO_532E9D";

// Insira aqui sua senha Wi-Fi
const char *WIFI_PASSWORD = "vAcCK1nwRg";

// IP do computador Windows com Docker
const char *API_URL =
  "http://192.168.0.9:8080/api/measurements";

// Identificador da estacao
const char *STATION_ID = "estacao-01";

// Envio a cada 30 segundos
const unsigned long INTERVALO_POST_MS = 30000;

// Tentativa de reconexao Wi-Fi
const unsigned long INTERVALO_WIFI_MS = 10000;

// Timeout HTTP
const int HTTP_TIMEOUT_MS = 8000;

// ==========================================
// CONFIGURACAO DOS PINOS
// ==========================================

// DHT22
#define PIN_DHT 4

// MQ-135
#define PIN_MQ135 34

// Sensor de chuva
#define PIN_CHUVA 27

// BMP180 - I2C principal
#define BMP_SDA 21
#define BMP_SCL 22

// BH1750 - I2C secundario
#define BH_SDA 18
#define BH_SCL 19

// ==========================================
// OBJETOS DOS SENSORES
// ==========================================

DHT dht(PIN_DHT, DHT22);

Adafruit_BMP085 bmp;

BH1750 bh1750;

// Segundo barramento I2C
TwoWire I2C_BH1750(1);

// Estado dos sensores
bool bmpOK = false;
bool bh1750OK = false;

// Controle de tempo
unsigned long ultimoPost = 0;
unsigned long ultimaTentativaWifi = 0;

// ==========================================
// FUNCAO PARA TRATAR VALORES INVALIDOS
// ==========================================

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

// ==========================================
// CONEXAO WIFI
// ==========================================

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

// ==========================================
// LEITURA DOS SENSORES
// ==========================================

JsonDocument obterMedicoes() {

  JsonDocument doc;

  doc["station_id"] = STATION_ID;

  // ========================================
  // DHT22 - TEMPERATURA E UMIDADE
  // ========================================

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

  // ========================================
  // BMP180 - PRESSAO ATMOSFERICA
  // ========================================

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

  // ========================================
  // BH1750 - LUMINOSIDADE
  // ========================================

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

  // ========================================
  // MQ-135 - QUALIDADE DO AR
  // ========================================

  // Divisor resistivo:
  // 47k + 47k
  //
  // AO MQ-135 -> 47k -> GPIO34
  // GPIO34 -> 47k -> GND

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

  // Estimativa da tensao antes do divisor
  int tensaoMQ = tensaoGPIO * 2;

  doc["gas_adc_raw"] = valorADC;

  doc["gas_gpio_mv"] = tensaoGPIO;

  doc["gas_ao_mv_estimated"] = tensaoMQ;

  // ========================================
  // SENSOR DE CHUVA
  // ========================================

  int sinalChuva = digitalRead(PIN_CHUVA);

  doc["rain_sensor_digital"] =
    sinalChuva;

  // LOW normalmente indica agua detectada
  doc["rain_detected"] =
    (sinalChuva == LOW);

  return doc;
}

// ==========================================
// ENVIO HTTP POST
// ==========================================

void enviarMedicoes() {

  JsonDocument doc = obterMedicoes();

  String json;

  serializeJson(doc, json);

  Serial.println();
  Serial.println("==============================");
  Serial.println("       NOVA MEDICAO");
  Serial.println("==============================");

  // Exibir dados no Monitor Serial
  serializeJsonPretty(doc, Serial);
  Serial.println();

  // Verificar Wi-Fi
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

  // API sem autenticacao
  http.addHeader(
    "Content-Type",
    "application/json"
  );

  // Enviar POST
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

// ==========================================
// SETUP
// ==========================================

void setup() {

  Serial.begin(115200);

  delay(1500);

  Serial.println();
  Serial.println("==============================");
  Serial.println(" ESTACAO METEOROLOGICA ESP32");
  Serial.println("==============================");

  // ========================================
  // DHT22
  // ========================================

  dht.begin();

  Serial.println("DHT22 inicializado!");

  // ========================================
  // BMP180
  // ========================================

  Wire.begin(BMP_SDA, BMP_SCL);

  bmpOK = bmp.begin();

  Serial.print("BMP180: ");

  Serial.println(
    bmpOK ? "OK" : "NAO ENCONTRADO"
  );

  // ========================================
  // BH1750
  // ========================================

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

  // ========================================
  // MQ-135
  // ========================================

  analogReadResolution(12);

  analogSetPinAttenuation(
    PIN_MQ135,
    ADC_11db
  );

  // ========================================
  // SENSOR DE CHUVA
  // ========================================

  pinMode(PIN_CHUVA, INPUT);

  Serial.println();
  Serial.println("Sensores inicializados!");
  Serial.println();

  // ========================================
  // WIFI
  // ========================================

  iniciarWifi();

  ultimaTentativaWifi = millis();

  // Primeiro POST imediatamente
  ultimoPost = millis() - INTERVALO_POST_MS;
}

// ==========================================
// LOOP PRINCIPAL
// ==========================================

void loop() {

  unsigned long agora = millis();

  // ========================================
  // RECONEXAO WIFI
  // ========================================

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

  // ========================================
  // ENVIO DAS MEDICOES
  // ========================================

  if (
    agora - ultimoPost >=
      INTERVALO_POST_MS
  ) {

    ultimoPost = agora;

    enviarMedicoes();
  }

  delay(100);
}
