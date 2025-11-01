#!/bin/bash

# Initialize DeepSeek R1 model in Ollama
echo "🤖 Initializing DeepSeek R1 Model..."

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama service..."
until curl -f http://deepseek-ai:11434/api/tags > /dev/null 2>&1; do
    echo "Waiting for Ollama..."
    sleep 5
done

echo "✅ Ollama is ready!"

# Pull DeepSeek R1 model (or use alternative like llama2 for testing)
echo "📥 Pulling DeepSeek R1 model..."
curl -X POST http://deepseek-ai:11434/api/pull \
    -d '{
        "name": "deepseek-r1:latest"
    }'

# Fallback to llama2 if deepseek-r1 is not available
if [ $? -ne 0 ]; then
    echo "⚠️  DeepSeek R1 not available, falling back to llama2..."
    curl -X POST http://deepseek-ai:11434/api/pull \
        -d '{
            "name": "llama2:latest"
        }'
fi

echo "✅ Model initialization complete!"
echo "🚀 AI Service is ready for threat analysis"

