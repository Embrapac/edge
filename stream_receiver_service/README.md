# Stream Receiver Service

Servico dedicado para receber frames enviados pelo EDGE via HTTP.

## Compatibilidade

Compativel com o uploader atual, que envia cada frame JPEG como `POST` binario para `/stream/upload`.

## Setup

```bash
cd stream_receiver_service
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Execucao

```bash
cd stream_receiver_service
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Endpoints

- `POST /stream/upload`: recebe frame em bytes
- `GET /stream/health`: status e contadores
- `GET /stream/latest.jpg`: retorna ultimo frame recebido
- `GET /stream/mjpeg`: visualizacao continua em MJPEG

## Integracao com EDGE

No EDGE, manter a configuracao:

```python
STREAMER_URL = "http://localhost:8000/stream"
```

Se rodar em outra maquina, troque `localhost` pelo IP/hostname do servidor receptor.
