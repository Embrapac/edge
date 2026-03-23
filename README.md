# 📡 EDGE

Repositório para o módulo EDGE, responsável pela captura de vídeo, processamento de inferência ML, armazenamento em buffer e streaming de dados para a nuvem.

## 🖥️ Dispositivo: Raspberry Pi 5

**Especificações:**
- Processador ARM64 otimizado para visão computacional
- Suporte nativo para câmeras Picamera2
- Capacidade de executar modelos YOLO otimizados

---

## 📦 Arquitetura do Projeto

```
edge/
├── video_buffer/          # 🎥 Gerenciamento de captura e buffer de vídeo
│   ├── capture_writer.py  # Captura frames da câmera
│   ├── uploader.py        # Streaming de frames com retry exponencial
│   ├── buffer_manager.py  # Gerencia limite de armazenamento
│   └── storage_policy.py  # Políticas de armazenamento
├── data_aggregator/       # 📊 Agregação de dados e métricas
│   ├── aggregator.py      # Processa detecções
│   ├── subscriber.py      # Consumidor MQTT
│   └── metrics_calculator.py
├── inference/             # 🤖 Inferência com modelos ML
│   ├── model_manager.py   # Carrega e gerencia modelos YOLO
│   └── model_fetcher.py   # Atualização remota de modelos
├── shared/                # 🔧 Módulos compartilhados
│   ├── event_bus.py       # Event bus para comunicação
│   ├── healthcheck.py     # Monitoramento de saúde
│   └── logger.py          # Logging estruturado
├── main.py                # 🚀 Orquestrador principal
├── config.py              # ⚙️ Configurações
└── docker-compose.yml     # 📦 Stack de monitoramento
```

---

## Protocolos de Integração

| Origem | Destino | Protocolo | Detalhes |
|--------|---------|-----------|----------|
| MCU (Microcontrolador) | EDGE | MQTT | _/embrapac/mcu-data_ |
| EDGE | Nuvem | MQTT | /embrapac/monitoring |


## 🔧 Dependências e Setup

### Apps e Serviços

| Serviço | Descrição |
|---------|-----------|
| **Servidor VNC** | Acesso remoto desktop nativo do Raspberry Pi OS |
| **Python 3.10+** | Runtime para aplicação |
| **MediaMTX** | RTSP streaming (opcional) |

### 📚 Bibliotecas Python Principais

**Sistema operacional (exemplos):**
```bash
sudo apt install -y python3-picamera2
```

**Aplicação principal:**
```bash
pip install ultralytics ncnn opencv-python httpx influxdb-client paho-mqtt
```

| Biblioteca | Propósito |
|-----------|----------|
| **ultralytics** | YOLO para detecção de objetos |
| **ncnn** | Otimização de modelos para ARM64 |
| **opencv-python** | Processamento de imagens |
| **httpx** | Cliente HTTP assíncrono |
| **paho-mqtt** | Comunicação MQTT |
   

[def]: #servidor-vnc


### Detecção de imagens com YOLO: procedimento manual

1) Instalar as bibliotecas necessárias

`pip install ultralytics ncnn`

2) Testando com um modelo genérico (off-the-shelf model)

`yolo detect predict model=yolo11n.pt`

Uma pasta yolo será criada com um arquivo `.pt`

3) Converter formato `pytorch` para `ncnn` que é otimizado para CPUs ARM

`yolo export model=yolo11n.pt format=ncnn`

Uma pasta yolo11n_ncnn_model será criada após a conversão, e será utilizada para rodar a inferência

4) Utilizando um script padrão para obter dados da imagem

`wget https://ejtech.io/code/yolo_detect.py`

Código desse repo: https://github.com/EdjeElectronics/Train-and-Deploy-YOLO-Models/tree/main

Para rodar o script que vai captar o stream da câmera:

`python yolo_detect.py --model=yolo11n_ncnn_model --source=usb/picamera[0-1] --resolution=1280x720`

### Realizando streaming da câmera e salvando num arquivo local

O streaming pode ser obtido através do VLC, mas é necessário que o Raspbian tenha o MediaMTX instalado

1) Instalando MediaMTX

TBD


### Detecção de imagens com YOLO: procedimento via Python script

1) Instalar as bibliotecas necessárias

`pip install ultralytics ncnn opencv-python`

2) Convertendo o modelo treinado para o formato ncnn

`yolo export model=box-sizing.pt format=ncnn`

3) Utilizando script de streming da câmera e OpenCV para exibir o vídeo

`python yolo_detect.py --model=box-sizing_ncnn_model --source=picamera1 --resolution=1280x720`


# EDGE MONITORING

Criado estrutura no Docker Compose para rodar o **Mosquitto**, **InfluxDB**, **Telegraf** e **Grafana**, para monitoramento dos KPIs do sistema.

Teste inicial do ambiente realizado no mesmo Raspberry Pi 5: publicação de dados no mosquitto para exibição no _dashboard_ do Grafana:

![Grafana](imgs/grafana-poc.png)

Teste realizado local no RPi:

`mosquitto_pub -h localhost -t "sensor/precision" -m "95"`

Teste realizado a partir de outro dispositivo na mesma rede:

`mosquitto_pub -h 192.168.51.10 -t "sensor/precision" -m "95"`

