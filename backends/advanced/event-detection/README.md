# Event Detection - Whisper LoRA Adapter

**🟢 STATUS: PRODUCTION WORKFLOW (User-Loop → Training → Detection)**

This folder contains an **event detection system** using Whisper + LoRA adapters. It integrates with the **Chronicle user-loop** for continuous data collection and training.

---

## 📋 Overview

This system uses a **LoRA (Low-Rank Adaptation)** adapter on top of Whisper's Large V3 model to detect specific custom events (sounds, keywords, phrases) in audio.

### Production Workflow:

```
User-Loop Popup (Review Anomalies)
        │
        ├──► Swipe Right → Accept/Verify
        │       │
        │       ▼
        │  MongoDB: training_stash collection
        │
        └──► Swipe Left → Reject/Stash 
                │
                ▼
        MongoDB: maybe_anomaly = "verified"
                │
                ▼
        Export: user_loop_feedback.jsonl
                │
                ▼
        Train: LoRA adapter
                │
                ▼
        Detect: Check audio for events
                │
                └──► New Anomalies Detected
```

---

## 📁 Files

| File | Purpose | Status |
|-------|----------|--------|
| `detect.py` | Run inference to detect events in audio files | ✅ Active |
| `export_from_mongo.py` | Export MongoDB `training_stash` to JSONL for training | ✅ Active (Bridge) |
| `train.py` | Fine-tune Whisper with LoRA adapter | ✅ Active |
| `requirements.txt` | Python dependencies | ✅ Active |

---

## 🚀 Production Workflow

### Step 1: Data Collection (User-Loop)

**Users interact with user-loop popup:**

1. **Frontend shows popup** when conversations have `maybe_anomaly: true`
2. **User reviews transcript** and audio
3. **Swipe Left** → Reject (stashes for training)
4. **Swipe Right** → Accept (marks as verified, `maybe_anomaly: "verified"`)

**MongoDB Collections:**

```javascript
// conversations - User-Loop reviews these
{
  "conversation_id": "1a43e276-...",
  "transcript_versions": [{
    "version_id": "c9c392d9-...",
    "maybe_anomaly": true,  // Triggers popup
    "transcript": "The stale smell of old beer..."
  }]
}

// training_stash - User-Loop saves rejected items here
{
  "_id": ObjectId("..."),
  "version_id": "c9c392d9-...",
  "conversation_id": "1a43e276-...",
  "transcript": "The stale smell of old beer...",
  "reason": "False positive",
  "timestamp": 1738254720.123,
  "audio_chunks": [...],
  "metadata": {"word_count": 43}
}
```

---

### Step 2: Export Training Data (Bridge)

**Export MongoDB `training_stash` collection to JSONL format:**

```bash
python export_from_mongo.py \
  --output user_loop_feedback.jsonl \
  --min_samples 10
```

**Output (`user_loop_feedback.jsonl`):**
```json
{"audio": "/data/audio/1a43e276-....wav", "text": "The stale smell of old beer...", "type": "positive", "timestamp": "2024-01-30T10:00:00Z"}
{"audio": "/data/audio/another-id.wav", "text": "Transcription with <event>", "type": "positive", "timestamp": "2024-01-30T10:05:00Z"}
```

**Arguments:**
- `--output`: Output JSONL file path (default: `user_loop_feedback.jsonl`)
- `--mongo_uri`: MongoDB connection (default: `mongodb://localhost:27017`)
- `--db_name`: Database name (default: `chronicle`)
- `--min_samples`: Minimum samples to export (default: 0)

**Schema Mapping:**
```python
# MongoDB → Training JSONL
{
    "audio": f"/data/audio/{entry['conversation_id']}.wav",
    "text": entry["transcript"],
    "timestamp": entry.get("timestamp"),
    "type": "positive"  # All user-loop rejections = positive for training
}
```

---

### Step 3: Train LoRA Adapter

**Fine-tune Whisper with exported user-loop data:**

```bash
python train.py \
  --data_file user_loop_feedback.jsonl \
  --output_dir ./sneeze_adapter \
  --base_model unsloth/whisper-large-v3 \
  --epochs 10 \
  --batch_size 4 \
  --learning_rate 1e-4
```

**Training Parameters:**
- `--data_file`: JSONL file from export (required)
- `--output_dir`: Directory to save adapter (required)
- `--base_model`: Whisper model ID (default: `unsloth/whisper-large-v3`)
- `--epochs`: Number of training epochs (default: 10)
- `--batch_size`: Batch size (default: 4)
- `--learning_rate`: Learning rate (default: `1e-4`)

**Output:**
```bash
./sneeze_adapter/
  ├── adapter_config.json
  ├── adapter_model.safetensors
  └── README.md
```

---

### Step 4: Detect Events (Inference)

**Run inference to check if audio contains event:**

```bash
python detect.py \
  --audio_path ./test_audio.wav \
  --base_model unsloth/whisper-large-v3 \
  --adapter_path ./sneeze_adapter \
  --trigger_token "<sneeze>"
```

**Arguments:**
- `--audio`: Path to audio file (required)
- `--base_model`: Whisper model ID (default: `unsloth/whisper-large-v3`)
- `--adapter_path`: Path to trained adapter directory (required)
- `--trigger_token`: Token to detect in transcription (required)

**Output:**
```
Loading audio: test_audio.wav
Transcription: He let out a loud <sneeze>
✅ DETECTED: <sneeze>
```

---

## 🔄 Full Cycle Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER INTERACTION PHASE                 │
│  Frontend shows popup when maybe_anomaly: true          │
└──────────────────┬──────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │ Swipe Actions         │
        │ Left=Reject Right=Accept
   ┌────┴────┐         ┌────┴────┐
   │ Swipe   │         │ Swipe   │
   │ Left    │         │ Right   │
   ▼         ▼         ▼         ▼
 Reject    Reject   Accept   Accept
 (stash)   (stash)  (verify) (verify)
   │         │         │         │
   ▼         ▼         │         │
 MongoDB:   MongoDB:   │         │
 training_  training_ ▼         ▼
 stash      stash   maybe_   maybe_
                      anomaly  anomaly
                      ="verified"
   │         │
   ▼         ▼
 More Data in
 training_stash
                   │
                   ▼
         ┌────────────────────┐
         │ EXPORT PHASE      │
         │ export_from_mongo │
         │   .py            │
         └────────┬─────────┘
                  │
                  ▼
         ┌────────────────────┐
         │ TRAINING PHASE    │
         │   train.py        │
         └────────┬─────────┘
                  │
                  ▼
         ┌────────────────────┐
         │  ./sneeze_      │
         │    adapter/        │
         └────────┬─────────┘
                  │
                  ▼
         ┌────────────────────┐
         │ DETECTION PHASE   │
         │   detect.py       │
         └────────┬─────────┘
                  │
                  ▼
         ┌────────────────────┐
         │   New Anomalies    │
         │   Detected         │
         └────────┬─────────┘
                  │
                  ▼
         ┌────────────────────┐
         │   User Popup      │
         │   (Round 2)       │
         └────────────────────┘
                  │
                  └──► Back to start!
```

---

## 📊 Training Data Format

The training JSONL file (`user_loop_feedback.jsonl`) uses this schema:

```json
{
  "audio": "/path/to/audio.wav",
  "text": "Transcription with <event> tag or just normal speech",
  "timestamp": "2024-01-30T10:00:00Z",
  "type": "positive"
}
```

**Fields:**
- `audio`: Path to audio file for training
- `text`: Ground truth transcription (from user-loop transcript)
- `timestamp`: When sample was added (from MongoDB)
- `type`: Always `"positive"` for user-loop data (rejections = positive training samples)

---

## 🧠 Training Details

### LoRA Configuration

- **Base Model**: Whisper Large V3 (unsloth)
- **Adapter Type**: LoRA (Low-Rank Adaptation)
- **Parameters**:
  - `r`: Rank (8-32 recommended)
  - `lora_alpha`: Scaling factor (16-64)
  - `target_modules`: `["q_proj", "v_proj"]`
  - `dtype`: `float16` for CUDA, `float32` for CPU

### Training Process

1. Load base model (Whisper Large V3)
2. Load training data (audio + transcriptions)
3. Fine-tune adapter layers only
4. Validate on test set
5. Save adapter weights to output directory

---

## 🎯 Production Deployment

### Automated Workflow

**Setup Cron Jobs for continuous improvement:**

```bash
# crontab -e

# Export training data daily at 2 AM
0 2 * * * cd /path/to/event-detection && python export_from_mongo.py --min_samples 50

# Retrain adapter weekly on Sunday at 3 AM
0 3 * * 0 cd /path/to/event-detection && python train.py --data_file user_loop_feedback.jsonl
```

### Adapter Versioning

Store versioned adapters for A/B testing and rollback:

```bash
./adapters/
  ├── sneeze_v1/    # Initial training
  ├── sneeze_v2/    # After 100 samples
  ├── sneeze_v3/    # After 500 samples
  └── sneeze_latest/  # Symlink to current
```

### Monitoring

Track metrics to improve detection:

- **False Positive Rate**: Swipe left (reject) / Total popups
- **True Positive Rate**: Swipe right (accept) / Total swipes right
- **Detection Accuracy**: Correct detections / Total samples

---

## 🐛 Troubleshooting

### Issue: "No entries found in training_stash"

**Symptoms:**
```
❌ No entries found in training_stash collection
💡 Tip: Swipe left on user-loop popup to add samples (reject = stash)
```

**Solutions:**
1. Verify user-loop popup is working
2. Swipe left on some anomalies to add to training_stash
3. Check MongoDB connection
4. Lower `--min_samples` threshold

---

### Issue: "Adapter not found"

**Symptoms:**
```
FileNotFoundError: Adapter ./sneeze_adapter not found!
```

**Solutions:**
1. Verify `--adapter_path` matches trained output directory
2. Check if train.py completed successfully
3. Ensure output directory exists

---

### Issue: "No audio files found" (in export)

**Symptoms:**
```
Exported 0 entries to user_loop_feedback.jsonl
   Has audio chunks: 0/10
```

**Solutions:**
1. Verify conversations have audio in MongoDB
2. Check audio_chunks collection
3. Ensure audio was uploaded correctly

---

### Issue: CUDA out of memory

**Symptoms:**
```
RuntimeError: CUDA out of memory
```

**Solutions:**
1. Reduce `--batch_size` (try 2 or 1)
2. Use CPU with `torch_dtype=torch.float32`
3. Use smaller base model (Whisper Base instead of Large)

---

### Issue: Poor detection accuracy

**Symptoms:**
- High false positive rate
- Misses obvious events
- Random detections

**Solutions:**
1. **More data**: Need at least 100-500 samples
2. **Better labels**: Review user-loop feedback for accuracy
3. **Retrain**: Train with more epochs
4. **Adjust trigger token**: Check if token appears in training data

---

## 📚 Dependencies

Install required packages:

```bash
pip install -r requirements.txt
```

**Key Dependencies:**
- `unsloth`: Optimized Whisper model
- `transformers`: Hugging Face model library
- `peft`: LoRA adapters
- `torch`: Deep learning framework
- `librosa`: Audio processing
- `datasets`: Training data utilities

**System Requirements:**
- Python 3.8+
- CUDA-capable GPU (recommended) or 16GB+ RAM for CPU

---

## 🔗 Integration with Backend

### Current State

**Frontend:**
```typescript
// UserLoopModal.tsx
const checkAnomaly = async () => {
  // TODO: Replace with actual algorithm
  const shouldShow = true  // Always shows popup
}
```

**Backend:**
```python
# user_loop_routes.py
- ✅ GET /api/user-loop/events (returns anomalies)
- ✅ POST /api/user-loop/accept (verifies)
- ✅ POST /api/user-loop/reject (stashes to training)
- ❌ No automatic anomaly detection (hardcoded)
```

### Future Integration

To add **automatic anomaly detection**:

1. **Load Adapter in Backend**
   ```python
   # Load LoRA adapter on startup
   adapter_path = "./adapters/sneeze_latest"
   model = load_whisper_with_adapter(adapter_path)
   ```

2. **Add Detection Service**
   ```python
   # services/event_detection_service.py
   async def detect_anomaly(audio_chunks, transcript):
       # Combine audio chunks
       audio = combine_chunks(audio_chunks)
       
       # Run inference
       detected, confidence = detect_event(audio, adapter)
       
       # Set maybe_anomaly based on detection
       return detected
   ```

3. **Update Conversation Processing**
   ```python
   # When new conversation is transcribed
   is_anomaly = event_service.detect_anomaly(
       audio_chunks=conversation.audio_chunks,
       transcript=conversation.transcript
   )
   
   # Save to database
   conversation.transcript_versions[0].maybe_anomaly = is_anomaly
   ```

4. **Remove Hardcoded Frontend**
   ```typescript
   const checkAnomaly = async () => {
     // Check backend for anomalies
     const response = await fetch('/api/user-loop/events')
     const anomalies = await response.json()
     const shouldShow = anomalies.length > 0  // Real detection!
     setIsOpen(shouldShow)
   }
   ```

---

## 📊 Workflow Summary

| Phase | Component | Command |
|--------|-----------|----------|
| **1. Collection** | User-Loop Popup | User swipes left to reject (stash) / right to accept |
| **2. Storage** | MongoDB | Saves to `training_stash` collection |
| **3. Export** | export_from_mongo.py | `python export_from_mongo.py --min_samples 10` |
| **4. Training** | train.py | `python train.py --data_file user_loop_feedback.jsonl` |
| **5. Detection** | detect.py | `python detect.py --audio test.wav --adapter ./adapter` |
| **6. Deployment** | Backend | Load adapter and run detection automatically |

---

## 🤝 Contributing

To improve event detection:

1. **Collect More Data**: Swipe left on user-loop popup to reject (stash) samples
2. **Review Labels**: Check training data quality
3. **Retrain Often**: Update adapter weekly with new data
4. **A/B Test**: Compare new vs old adapters
5. **Monitor Metrics**: Track false positive/negative rates

---

**Last Updated**: January 30, 2026  
**Status**: 🟢 Production Workflow (User-Loop → Training → Detection) ✅
**Backend Integration**: 🟡 Partial (Manual export, auto detection pending)
