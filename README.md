# EDGE

Repositório para o módulo EDGE, responsável pela conectividade com a nuvem e interfaces com dispositivos como câmera

## Dispositivo: Raspberry Pi 5

### Apps e Serviços 

* [Servidor VNC][def]
* [Bibliotecas Python](#bibliotecas-python)

### Integrações

* Câmera de Foto
* Câmera de Vídeo

#### Servidor VNC

O servidor VNC já vem nativo do Raspberry Pi OS instalado.

Para acessar foi feito o teste com [Tiger VNC](https://tigervnc.org/), instalado através da loja de aplicativos Ubuntu 24.04.

#### Bibliotecas Python

Considerando exemplos executados (pasta `examples/`)

1) python3-picamera2

   Instalado diretamente no sistema operacional: `sudo apt install -y python3-picamera2`

2) Flask

   Para subir um servidor local

Considerando a aplicação principal:

1) ultralytics: para realizar todo o processamento da biblioteca para visão computacional: YOLO
2) ncnn: otimiza o modelo treinado para adequação ao processador ARM64 do Raspberry Pi 5
   

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

2) Utilizando script de streming da câmera e OpenCV para exibir o vídeo

TBD




