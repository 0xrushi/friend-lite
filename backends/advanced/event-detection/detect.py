import os
import argparse
import torch
import librosa
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from peft import PeftModel

def parse_args():
    parser = argparse.ArgumentParser(description="Detect Event using Whisper LoRA Adapter")
    parser.add_argument("--audio", type=str, required=True, help="Path to audio file")
    parser.add_argument("--base_model", type=str, default="unsloth/whisper-large-v3", help="Base Whisper model ID")
    parser.add_argument("--adapter_path", type=str, required=True, help="Path to LoRA adapter directory")
    parser.add_argument("--trigger_token", type=str, required=True, help="Token to detect")
    return parser.parse_args()

def load_model(base_model_id: str, adapter_path: str):
    """Load base model and merge adapter"""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    # Load Base Model
    print(f"Loading base model: {base_model_id}")
    processor = WhisperProcessor.from_pretrained(base_model_id)
    model = WhisperForConditionalGeneration.from_pretrained(
        base_model_id, 
        torch_dtype=torch.float16 if device == "cuda" else torch.float32
    )

    # Load and MERGE Adapter
    if os.path.exists(adapter_path):
        print(f"Loading LoRA adapter from: {adapter_path}")
        model = PeftModel.from_pretrained(model, adapter_path)
        print("Merging LoRA weights...")
        model = model.merge_and_unload()
    else:
        raise FileNotFoundError(f"Adapter {adapter_path} not found!")

    model.to(device)
    model.eval()
    return model, processor, device

def detect_event(audio_path: str, model, processor, device, trigger_token: str) -> bool:
    """Run inference and check for trigger token"""
    
    # Load audio
    print(f"Loading audio: {audio_path}")
    audio, _ = librosa.load(audio_path, sr=16000)
    
    # Process audio
    inputs = processor(audio, sampling_rate=16000, return_tensors="pt")
    input_features = inputs.input_features.to(device)
    
    if device == "cuda":
        input_features = input_features.half()

    # Generate
    with torch.no_grad():
        generated_ids = model.generate(
            input_features=input_features,
            language="en",
            task="transcribe",
            max_new_tokens=256
        )
    
    transcription = processor.batch_decode(generated_ids, skip_special_tokens=True)[0].strip()
    print(f"Transcription: {transcription}")
    
    detected = trigger_token in transcription
    if detected:
        print(f"✅ DETECTED: {trigger_token}")
    else:
        print(f"❌ NOT DETECTED")
        
    return detected, transcription

def main():
    args = parse_args()
    
    model, processor, device = load_model(args.base_model, args.adapter_path)
    detect_event(args.audio, model, processor, device, args.trigger_token)

if __name__ == "__main__":
    main()
