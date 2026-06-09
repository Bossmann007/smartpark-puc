# ATENCAO: arquivo sincronizado com o main.py oficial do SmartPark.
# A versao antiga aqui era de outro projeto (Blynk + servo + DHT22) e NAO deve ser usada.
#
# Grupo: Enzo Bossmann, Gabriel Henrique e Diego Feltrin
# Problema: Monitoramento de vagas de estacionamento (Sistema Ciberfisico)
# Disciplina: Fundamentos de Sistemas Ciberfisicos — PUCPR
# Placa: ESP32 + 2x HC-SR04 + 4 LEDs + buzzer | Comunicacao: MQTT

from machine import Pin, PWM, time_pulse_us
from utime import sleep, sleep_us
from network import WLAN, STA_IF
from ujson import dumps

print("Hello, ESP32 — SmartPark!")

try:
    from umqtt.simple import MQTTClient
    MQTT_DISPONIVEL = True
except ImportError:
    MQTT_DISPONIVEL = False
    print("Sem biblioteca umqtt — rodando em modo offline")


# ===== CONFIGURACOES =====
WIFI_SSID = "Wokwi-GUEST"
WIFI_PASS = ""

MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT   = 1883
MQTT_TOPIC  = "smartpark/vagas"
CLIENT_ID   = "esp32-smartpark"

LIMIAR_CM = 20

# ===== PINOS =====
TRIG1 = Pin(5,  Pin.OUT)
ECHO1 = Pin(18, Pin.IN)
TRIG2 = Pin(19, Pin.OUT)
ECHO2 = Pin(21, Pin.IN)

LED_V1 = Pin(2,  Pin.OUT)
LED_R1 = Pin(4,  Pin.OUT)
LED_V2 = Pin(22, Pin.OUT)
LED_R2 = Pin(23, Pin.OUT)

buzzer = PWM(Pin(25), freq=1000, duty=0)

LED_V1.on()
LED_R1.off()
LED_V2.on()
LED_R2.off()
print("LEDs inicializados — vagas livres")


# ===== FUNCOES =====

def medir_distancia(trig, echo):
    """Dispara um pulso ultrassonico e retorna a distancia em cm.
    Retorna 999 se nao houver eco (timeout)."""
    trig.off()
    sleep_us(2)
    trig.on()
    sleep_us(10)
    trig.off()
    duracao = time_pulse_us(echo, 1, 30000)
    if duracao < 0:
        return 999.0
    return (duracao * 0.0343) / 2.0


def atualizar_led(ocupada, verde, vermelho):
    """Acende vermelho se a vaga esta ocupada, senao acende verde."""
    if ocupada:
        verde.off()
        vermelho.on()
    else:
        verde.on()
        vermelho.off()


def atualizar_buzzer(lotado):
    """Liga o buzzer (50% do ciclo) quando o estacionamento esta lotado."""
    if lotado:
        buzzer.duty(512)
    else:
        buzzer.duty(0)


def conectar_wifi():
    """Tenta conectar no WiFi por ate 10 segundos. Retorna True se conectou."""
    wlan = WLAN(STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)
    for tentativa in range(20):
        if wlan.isconnected():
            print(f"WiFi conectado — IP {wlan.ifconfig()[0]}")
            return True
        sleep(0.5)
    print("WiFi nao conectou — modo offline")
    return False


def conectar_mqtt():
    """Tenta criar e conectar o cliente MQTT. Retorna o cliente ou None."""
    if not MQTT_DISPONIVEL:
        return None
    try:
        client = MQTTClient(CLIENT_ID, MQTT_BROKER, MQTT_PORT)
        client.connect()
        print("MQTT conectado")
        return client
    except Exception as erro:
        print(f"Erro ao conectar MQTT: {erro}")
        return None


# ===== PROGRAMA PRINCIPAL =====

def main():
    wifi_ok = conectar_wifi()
    client = None
    if wifi_ok:
        client = conectar_mqtt()

    ant1 = None
    ant2 = None

    while True:
        d1 = medir_distancia(TRIG1, ECHO1)
        d2 = medir_distancia(TRIG2, ECHO2)
        ocup1 = d1 < LIMIAR_CM
        ocup2 = d2 < LIMIAR_CM

        atualizar_led(ocup1, LED_V1, LED_R1)
        atualizar_led(ocup2, LED_V2, LED_R2)
        atualizar_buzzer(ocup1 and ocup2)

        if ocup1 != ant1 or ocup2 != ant2:
            payload = {
                "vaga1": {"ocupada": ocup1, "dist_cm": round(d1, 1)},
                "vaga2": {"ocupada": ocup2, "dist_cm": round(d2, 1)},
            }
            texto = dumps(payload)
            print(f"Estado: {texto}")
            if client:
                try:
                    client.publish(MQTT_TOPIC, texto.encode())
                except Exception as erro:
                    print(f"Erro ao publicar: {erro}")
                    client = None

        ant1 = ocup1
        ant2 = ocup2
        sleep(1)


main()
