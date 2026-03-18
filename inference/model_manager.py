import threading
import httpx
import onnxruntime as ort  # ou tflite_runtime.interpreter
from pathlib import Path

from shared.logger import get_struct_logger

logger = get_struct_logger(__name__)

class ModelManager:
    
    def __init__(self, models_dir: str):
        self.models_dir = Path(models_dir)
        self._lock = threading.RLock()
        self._session = None
        self._current_model_path = None

    def load_model(self, model_path: str):
        # Check the usage of ONNX against .pt files
        if model_path.endswith(".pt"):
            # Handle PyTorch model (example, adjust as needed)
            pass
        else:
            new_session = ort.InferenceSession(model_path)
        # with self._lock:
        #     self._session = new_session
        #     self._current_model_path = model_path

    def infer(self, input_data: dict):
        with self._lock:
            if self._session is None:
                raise RuntimeError("Nenhum modelo carregado.")
            return self._session.run(None, input_data)

class ModelFetcher:

    def __init__(self, model_manager: ModelManager, download_dir: str):
        self._manager = model_manager
        self._download_dir = Path(download_dir)
        self._download_dir.mkdir(parents=True, exist_ok=True)

    async def fetch_and_apply(self, model_url: str, filename: str):
        dest = self._download_dir / filename
        async with httpx.AsyncClient() as client:
            response = await client.get(model_url)
            response.raise_for_status()
            dest.write_bytes(response.content)
        self._manager.load_model(str(dest))
