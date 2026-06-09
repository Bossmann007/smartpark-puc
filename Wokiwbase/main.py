# ATENCAO: este arquivo foi sincronizado com o main.py oficial do SmartPark.
# A versao anterior aqui era de outro projeto (Blynk + servo + DHT22) e NAO
# deve ser usada. Para o Wokwi, use sempre este codigo (igual ao da raiz).
#
# Grupo: Enzo Bossmann, Gabriel Henrique e Diego Feltrin
# Problema: Monitoramento de vagas de estacionamento (Sistema Ciberfisico)
# Disciplina: Fundamentos de Sistemas Ciberfisicos — PUCPR
# Placa: ESP32 + 2x HC-SR04 + 4 LEDs + buzzer | Comunicacao: MQTT

import machine
import time
import network
import ujson

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
TRIG1 = machine.Pin(5,  machine.Pin.OUT)
ECHO1 = machine.Pin(18, machine.Pin.IN)
TRIG2 = machine.Pin(19, machine.Pin.OUT)
ECHO2 = machine.Pin(21, machine.Pin.IN)

LED_V1 = machine.Pin(2,  machine.Pin.OUT)
LED_R1 = machine.Pin(4,  machine.Pin.OUT)
LED_V2 = machine.Pin(22, machine.Pin.OUT)
LED_R2 = machine.Pin(23, machine.Pin.OUT)

buzzer = machine.PWM(machine.Pin(25), freq=1000, duty=0)

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
    time.sleep_us(2)
    trig.on()
    time.sleep_us(10)
    trig.off()
    duracao = machine.time_pulse_us(echo, 1, 30000)
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
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)
    for tentativa in range(20):
        if wlan.isconnected():
            print(f"WiFi conectado — IP {wlan.ifconfig()[0]}")
            return True
        time.sleep(0.5)
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
            texto = ujson.dumps(payload)
            print(f"Estado: {texto}")
            if client:
                try:
                    client.publish(MQTT_TOPIC, texto.encode())
                except Exception as erro:
                    print(f"Erro ao publicar: {erro}")
                    client = None

        ant1 = ocup1
        ant2 = ocup2
        time.sleep(1)


main()
