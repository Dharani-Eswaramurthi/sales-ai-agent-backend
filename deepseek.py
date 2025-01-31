from transformers import pipeline

# Ensure transformers library is updated
import subprocess
import sys

subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "transformers"])

messages = [
    {"role": "user", "content": "Who are you?"},
]
pipe = pipeline("text-generation", model="deepseek-ai/DeepSeek-V3", trust_remote_code=True)
pipe(messages)