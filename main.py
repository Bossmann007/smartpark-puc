import machine
import time
import network
import ujson

try:
    from umqtt.simple import MQTTClient
    MQTT_DISPONIVEL = True
except ImportError:
    MQTT_DISPONIVEL = False
    print("sem umqtt, rodando offline")

WIFI_SSID = "PUC_SMARTPARK"
WIFI_PASS  = "smartpark2026"

MQTT_BROKER = "192.168.1.100"
MQTT_PORT   = 1883
MQTT_TOPIC  = "smartpark/vagas"
CLIENT_ID   = "esp32-smartpark"

# Distância em cm abaixo da qual a vaga é considerada ocupada
LIMIAR_CM = 20

# Sensores HC-SR04 — Vaga 1: GPIO 5 (TRIG) / GPIO 18 (ECHO)
TRIG1 = machine.Pin(5,  machine.Pin.OUT)
ECHO1 = machine.Pin(18, machine.Pin.IN)

# Sensores HC-SR04 — Vaga 2: GPIO 19 (TRIG) / GPIO 21 (ECHO)
TRIG2 = machine.Pin(19, machine.Pin.OUT)
ECHO2 = machine.Pin(21, machine.Pin.IN)

# LEDs — Verde = livre, Vermelho = ocupada
LED_V1 = machine.Pin(2,  machine.Pin.OUT)   # Verde Vaga 1
LED_R1 = machine.Pin(4,  machine.Pin.OUT)   # Vermelho Vaga 1
LED_V2 = machine.Pin(22, machine.Pin.OUT)   # Verde Vaga 2
LED_R2 = machine.Pin(23, machine.Pin.OUT)   # Vermelho Vaga 2

# Estado inicial antes de qualquer conexão: todas as vagas livres (verde ON, vermelho OFF)
LED_V1.on();  LED_R1.off()
LED_V2.on();  LED_R2.off()
print("leds ok")

# Buzzer passivo via PWM — toca quando as duas vagas estão ocupadas
_buzzer = machine.PWM(machine.Pin(25), freq=1000, duty=0)


def medir_distancia(trig, echo):
    """Dispara pulso ultrassônico e retorna distância em cm. Retorna 999 em timeout."""
    trig.off()
    time.sleep_us(2)
    trig.on()
    time.sleep_us(10)
    trig.off()
    duracao = machine.time_pulse_us(echo, 1, 30000)
    if duracao < 0:
        return 999.0
    return (duracao * 0.0343) / 2.0


def set_led(ocupada, verde, vermelho):
    """Acende o LED correto conforme status da vaga."""
    if ocupada:
        verde.off()
        vermelho.on()
    else:
        verde.on()
        vermelho.off()


def set_buzzer(lotado):
    """Liga buzzer com PWM 50% duty quando estacionamento está lotado."""
    _buzzer.duty(512 if lotado else 0)


def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)
    for _ in range(20):
        if wlan.isconnected():
            print("wifi ok -", wlan.ifconfig()[0])
            return True
        time.sleep(0.5)
    print("wifi falhou, modo offline")
    return False


def publicar(client, payload):
    dados = ujson.dumps(payload)
    client.publish(MQTT_TOPIC, dados.encode())
    print("publicado:", dados)


def main():
    wifi_ok = conectar_wifi()
    client = None

    if wifi_ok and MQTT_DISPONIVEL:
        try:
            client = MQTTClient(CLIENT_ID, MQTT_BROKER, MQTT_PORT)
            client.connect()
            print("mqtt conectado")
        except Exception as e:
            print("erro mqtt:", e)
            client = None

    # Estado anterior das vagas — publica só quando muda
    ant = {1: None, 2: None}

    while True:
        d1 = medir_distancia(TRIG1, ECHO1)
        ocup1 = d1 < LIMIAR_CM
        set_led(ocup1, LED_V1, LED_R1)

        d2 = medir_distancia(TRIG2, ECHO2)
        ocup2 = d2 < LIMIAR_CM
        set_led(ocup2, LED_V2, LED_R2)

        set_buzzer(ocup1 and ocup2)

        mudou = (ocup1 != ant[1]) or (ocup2 != ant[2])
        if mudou:
            payload = {
                "vaga1": {"ocupada": ocup1, "dist_cm": round(d1, 1)},
                "vaga2": {"ocupada": ocup2, "dist_cm": round(d2, 1)},
            }
            print("estado atual:", ujson.dumps(payload))
            if client:
                try:
                    publicar(client, payload)
                except Exception as e:
                    print("erro ao publicar:", e)
                    try:
                        client.connect()
                    except Exception:
                        client = None

        ant[1] = ocup1
        ant[2] = ocup2
        time.sleep(1)


main()
