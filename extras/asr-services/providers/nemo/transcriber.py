"""
NeMo transcriber implementation.

Uses NVIDIA NeMo ASR models (Parakeet, Canary, etc.) with native
timestamp support. NeMo handles long audio internally.
"""

import asyncio
import logging
import os
import platform
from typing import Optional, cast

import torch
from common.response_models import TranscriptionResult, Word

logger = logging.getLogger(__name__)

# Constants
NEMO_SAMPLE_RATE = 16000


class NemoTranscriber:
    """
    Transcriber using NVIDIA NeMo ASR models.

    Supports:
    - nvidia/parakeet-tdt-0.6b-v3
    - nvidia/canary-1b
    - Other NeMo ASR models

    NeMo's transcribe() method handles long audio natively with word-level
    timestamps - no custom chunking required.

    Environment variables:
        ASR_MODEL: Model identifier (default: nvidia/parakeet-tdt-0.6b-v3)
    """

    def __init__(self, model_id: Optional[str] = None):
        """
        Initialize the NeMo transcriber.

        Args:
            model_id: Model identifier. If None, reads from ASR_MODEL env var.
        """
        self.model_id = model_id or os.getenv(
            "ASR_MODEL", "nvidia/parakeet-tdt-0.6b-v3"
        )

        self.model = None
        self._is_loaded = False
        self._lock = asyncio.Lock()

        logger.info(f"NemoTranscriber initialized: model={self.model_id}")

    def load_model(self) -> None:
        """Load the NeMo ASR model."""
        if self._is_loaded:
            logger.info("Model already loaded")
            return

        logger.info(f"Loading NeMo ASR model: {self.model_id}")

        import nemo.collections.asr as nemo_asr

        is_dgx_spark = (
            platform.machine().lower() in {"aarch64", "arm64"}
            and torch.cuda.is_available()
            and "GB10" in torch.cuda.get_device_name()
        )
        # Restore on CPU first on Spark to avoid simultaneously allocating the
        # checkpoint and model on its GPU under shared-memory pressure.
        load_options = {"map_location": "cpu"} if is_dgx_spark else {}
        self.model = cast(
            nemo_asr.models.ASRModel,
            nemo_asr.models.ASRModel.from_pretrained(
                model_name=self.model_id, **load_options
            ),
        )
        if is_dgx_spark:
            self.model = self.model.to("cuda")

        # DGX Spark's GB10/ARM64 stack currently hits a CUDA bindings tuple
        # mismatch in NeMo's graph decoder. Keep GPU inference, but use eager
        # decoding on this hardware only; preserve defaults everywhere else.
        if (
            is_dgx_spark
            and hasattr(self.model, "change_decoding_strategy")
            and "decoding" in self.model.cfg
            and "greedy" in self.model.cfg.decoding
        ):
            from omegaconf import OmegaConf, open_dict

            decoding = OmegaConf.create(OmegaConf.to_container(self.model.cfg.decoding))
            with open_dict(decoding):
                decoding.greedy.use_cuda_graph_decoder = False
            self.model.change_decoding_strategy(decoding)
            logger.info("DGX Spark detected: CUDA graph decoding disabled for GB10")

        self._is_loaded = True
        logger.info("Model loaded successfully")

    async def transcribe(self, audio_file_path: str) -> TranscriptionResult:
        """
        Transcribe audio file using NeMo.

        NeMo's transcribe() handles long audio natively with timestamps=True.
        No custom chunking is needed.

        Args:
            audio_file_path: Path to audio file (WAV format, 16kHz mono preferred)

        Returns:
            TranscriptionResult with text, words, and segments
        """
        if not self._is_loaded or self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")

        logger.info(f"Transcribing: {audio_file_path}")

        async with self._lock:
            with torch.no_grad():
                results = self.model.transcribe(
                    [audio_file_path], batch_size=1, timestamps=True
                )

        if not results or len(results) == 0:
            logger.warning("NeMo returned empty results")
            return TranscriptionResult(text="", words=[], segments=[])

        result = results[0]

        # Extract text
        if hasattr(result, "text") and result.text:
            text = result.text
        elif isinstance(result, str):
            text = result
        else:
            text = ""

        # Extract word-level timestamps - NeMo Parakeet format
        words = []
        if hasattr(result, "timestamp") and "word" in result.timestamp:
            for word_data in result.timestamp["word"]:
                word = Word(
                    word=word_data["word"],
                    start=word_data["start"],
                    end=word_data["end"],
                    confidence=1.0,
                )
                words.append(word)

        logger.info(f"Transcription complete: {len(text)} chars, {len(words)} words")

        return TranscriptionResult(
            text=text,
            words=words,
            segments=[],
        )

    @property
    def is_loaded(self) -> bool:
        """Return True if model is loaded."""
        return self._is_loaded
