# SmartPark PUC

Monitoramento inteligente de vagas de estacionamento com ESP32 + MicroPython + MQTT.

**Disciplina:** Fundamentos de Sistemas Ciberfísicos — PUCPR 2026.1  
**Alunos:** Enzo Bossmann · Gabriel Henrique · Diego Feltrin

🔗 **Simulação Wokwi:** https://wokwi.com/projects/465089138268468225

---

## O Problema

Os totens da PUC mostram só "lotado" ou "disponível" — sem indicar onde exatamente há vaga. O motorista entra, percorre o corredor inteiro, não encontra nada e volta. Motor ligado = CO₂ desnecessário.

O SmartPark resolve isso no nível da vaga individual: LED verde = livre, LED vermelho = ocupada.

---

## Como funciona

```
HC-SR04 (vaga 1 e 2)
    ↓ GPIO 5/18 · 19/21
ESP32 DevKit V1 — MicroPython
    ↓ GPIO 2/4/22/23
4× LED (verde + vermelho por vaga)
    ↓ GPIO 25
Buzzer — toca quando estacionamento está lotado
    ↓ WiFi / MQTT
Dashboard Processing (tempo real)
```

As quatro camadas CPS:
| Camada | Componente |
|--------|-----------|
| Sensing | HC-SR04 mede distância até o carro |
| Computation | ESP32 decide se vaga está ocupada (dist < 20 cm) |
| Communication | WiFi + MQTT envia status pro dashboard |
| Actuation | LED + Buzzer sinalizam visualmente e sonoramente |

---

## Hardware

| Componente | Quantidade | GPIO |
|-----------|-----------|------|
| ESP32 DevKit V1 | 1 | — |
| HC-SR04 | 2 | TRIG: 5, 19 · ECHO: 18, 21 |
| LED verde | 2 | 2, 22 |
| LED vermelho | 2 | 4, 23 |
| Resistor 220Ω | 4 | — |
| Buzzer passivo | 1 | 25 (PWM 1kHz) |

> ⚠️ Em hardware real: usar divisor resistivo 1kΩ/2kΩ no pino ECHO — o HC-SR04 manda 5V mas o ESP32 só suporta 3,3V.

---

## Estrutura do repositório

```
main.py              # Firmware MicroPython (ESP32)
diagram.json         # Circuito Wokwi
slides-smartpark.html  # Slides da apresentação (abrir no browser)
relatorio-smartcity.md # Relatório completo do projeto
DashboardProcessingimg/  # Screenshots do dashboard Processing
```

---

## Como rodar no Wokwi

1. Acesse https://wokwi.com/projects/465089138268468225
2. Clique em **Start Simulation**
3. Clique em um dos sensores HC-SR04 e arraste o slider de distância
4. Ao colocar distância < 20 cm: LED vermelho acende (vaga ocupada)
5. Com as duas vagas ocupadas: buzzer toca

---

## Payload MQTT

**Tópico:** `smartpark/vagas`

```json
{
  "vaga1": { "ocupada": true,  "dist_cm": 12.3 },
  "vaga2": { "ocupada": false, "dist_cm": 47.8 }
}
```

Publica apenas quando o estado muda — sem tráfego redundante.

---

## Custo estimado por vaga

| Componente | Preço (R$) |
|-----------|-----------|
| ESP32 DevKit V1 | ~25 |
| HC-SR04 | ~5 |
| LEDs + resistores | ~2 |
| Buzzer | ~3 |
| **Total por 2 vagas** | **~35** |

---

## Licença

MIT
