#!/bin/bash
# Phase 4b: free, full-precision Qwen weights from Hugging Face (P4b-2/3: never a quantized model for training).
cd /Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2
.venv/bin/pip install -q "mlx-lm==0.28.2" "huggingface_hub>=0.25" 2>&1 | tail -2
for m in Qwen/Qwen2.5-0.5B-Instruct Qwen/Qwen2.5-1.5B-Instruct; do
  .venv/bin/python -c "
from huggingface_hub import snapshot_download
p = snapshot_download('$m', local_dir='research/phase4/models/' + '$m'.split('/')[1], allow_patterns=['*.json','*.safetensors','*.txt','tokenizer*','merges.txt','vocab.json'])
print('downloaded', p)"
done
du -sh research/phase4/models/* ; echo FETCH-DONE
