# Grupo: Enzo Bossmann, Gabriel Henrique e Diego Feltrin
# Problema: Monitoramento de vagas de estacionamento (Sistema Ciberfisico)
# Disciplina: Fundamentos de Sistemas Ciberfisicos — PUCPR
# Placa: ESP32 + 2x HC-SR04 + 4 LEDs + buzzer | Comunicacao: MQTT
#
# Logica: cada vaga tem um sensor de distancia. Se um carro fica
# perto do sensor (distancia abaixo do limiar), a vaga esta OCUPADA
# (LED vermelho). Se nao, esta LIVRE (LED verde). Se as duas vagas
# ficam ocupadas, o buzzer apita (estacionamento lotado).

from machine import Pin, PWM, time_pulse_us
from utime import sleep, sleep_us
from network import WLAN, STA_IF
from ujson import dumps

print("Hello, ESP32 — SmartPark!")

# umqtt pode nao existir no simulador; se faltar, roda em modo offline
try:
    from umqtt.simple import MQTTClient
    MQTT_DISPONIVEL = True
except ImportError:
    MQTT_DISPONIVEL = False
    print("Sem biblioteca umqtt — rodando em modo offline")


# ===== CONFIGURACOES =====
# No simulador Wokwi a unica rede e a "Wokwi-GUEST" (senha vazia).
# Para a placa real, troque pelos dados da rede do estacionamento.
WIFI_SSID = "Wokwi-GUEST"
WIFI_PASS = ""

MQTT_BROKER = "broker.hivemq.com"   # broker publico para teste
MQTT_PORT   = 1883
MQTT_TOPIC  = "smartpark/vagas"
CLIENT_ID   = "esp32-smartpark"

# Distancia em cm abaixo da qual a vaga e considerada ocupada
LIMIAR_CM = 20

# ===== PINOS =====
# Sensores HC-SR04 (TRIG = saida que dispara, ECHO = entrada que mede)
TRIG1 = Pin(5,  Pin.OUT)
ECHO1 = Pin(18, Pin.IN)
TRIG2 = Pin(19, Pin.OUT)
ECHO2 = Pin(21, Pin.IN)

# LEDs — verde = vaga livre, vermelho = vaga ocupada
LED_V1 = Pin(2,  Pin.OUT)   # verde vaga 1
LED_R1 = Pin(4,  Pin.OUT)   # vermelho vaga 1
LED_V2 = Pin(22, Pin.OUT)   # verde vaga 2
LED_R2 = Pin(23, Pin.OUT)   # vermelho vaga 2

# Buzzer passivo no pino 25. So criamos o PWM quando o estacionamento
# fica lotado; fora disso o pino fica em LOW (silencio). Isso evita o
# buzzer tocar sem parar no Wokwi.
PINO_BUZZER = Pin(25, Pin.OUT)
PINO_BUZZER.off()
buzzer_pwm = None

# Estado inicial: as duas vagas comecam LIVRES (verde ligado).
# Isso evita LEDs em estado indefinido enquanto a placa liga.
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
    # velocidade do som = 0.0343 cm/us; divide por 2 (ida e volta)
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
    """Liga o buzzer quando lotado; desliga (silencio total) quando nao."""
    global buzzer_pwm
    if lotado:
        if buzzer_pwm is None:
            buzzer_pwm = PWM(PINO_BUZZER, freq=1000, duty=512)
    else:
        if buzzer_pwm is not None:
            buzzer_pwm.deinit()
            buzzer_pwm = None
        PINO_BUZZER.off()


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

    # Guarda o estado anterior de cada vaga para so publicar quando mudar
    ant1 = None
    ant2 = None

    while True:
        # Le os dois sensores e decide se cada vaga esta ocupada
        d1 = medir_distancia(TRIG1, ECHO1)
        d2 = medir_distancia(TRIG2, ECHO2)
        ocup1 = d1 < LIMIAR_CM
        ocup2 = d2 < LIMIAR_CM

        # Atualiza LEDs e buzzer
        atualizar_led(ocup1, LED_V1, LED_R1)
        atualizar_led(ocup2, LED_V2, LED_R2)
        atualizar_buzzer(ocup1 and ocup2)

        # So publica/imprime quando o estado de alguma vaga muda
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
                    client = None   # desiste do MQTT e segue offline

        ant1 = ocup1
        ant2 = ocup2
        sleep(1)


main()
