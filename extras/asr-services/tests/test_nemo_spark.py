"""Hardware gating for the DGX Spark CUDA graph compatibility workaround."""

import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from omegaconf import OmegaConf

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from providers.nemo.transcriber import NemoTranscriber


@pytest.mark.parametrize(
    "architecture,gpu,cuda_available,disable_graphs",
    [
        ("aarch64", "NVIDIA GB10", True, True),
        ("arm64", "NVIDIA GB10", True, True),
        ("x86_64", "NVIDIA GB10", True, False),
        ("x86_64", "NVIDIA RTX 4090", True, False),
        ("aarch64", "NVIDIA H100", True, False),
        ("aarch64", "NVIDIA GB10", False, False),
    ],
)
def test_load_model_preserves_other_hardware_defaults(
    architecture, gpu, cuda_available, disable_graphs
):
    config = OmegaConf.create(
        {
            "decoding": {
                "strategy": "greedy_batch",
                "greedy": {"use_cuda_graph_decoder": True, "max_symbols": 10},
                "preserve_alignments": True,
            }
        }
    )
    model = Mock(cfg=config)
    model.to.return_value = model
    asr = ModuleType("nemo.collections.asr")
    factory = Mock(return_value=model)
    asr.models = SimpleNamespace(ASRModel=SimpleNamespace(from_pretrained=factory))
    modules = {
        "nemo": ModuleType("nemo"),
        "nemo.collections": ModuleType("nemo.collections"),
        "nemo.collections.asr": asr,
    }
    with (
        patch.dict(sys.modules, modules),
        patch("providers.nemo.transcriber.platform.machine", return_value=architecture),
        patch(
            "providers.nemo.transcriber.torch.cuda.is_available",
            return_value=cuda_available,
        ),
        patch(
            "providers.nemo.transcriber.torch.cuda.get_device_name", return_value=gpu
        ),
    ):
        transcriber = NemoTranscriber()
        transcriber.load_model()
        transcriber.load_model()

    factory.assert_called_once()
    assert transcriber.is_loaded
    assert config.decoding.greedy.use_cuda_graph_decoder is True
    if disable_graphs:
        assert factory.call_args.kwargs["map_location"] == "cpu"
        model.to.assert_called_once_with("cuda")
        model.change_decoding_strategy.assert_called_once()
        updated = model.change_decoding_strategy.call_args.args[0]
        assert updated.greedy.use_cuda_graph_decoder is False
        assert updated.greedy.max_symbols == 10
        assert updated.strategy == "greedy_batch"
        assert updated.preserve_alignments is True
    else:
        assert "map_location" not in factory.call_args.kwargs
        model.to.assert_not_called()
        model.change_decoding_strategy.assert_not_called()
