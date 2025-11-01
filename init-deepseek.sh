#!/bin/bash
#
# Initialize DeepSeek R1 model in Ollama
# Downloads and prepares the model for CPU-only inference
#

set -e

echo "🤖 Initializing DeepSeek R1 model..."

# Wait for Ollama service to be ready
echo "⏳ Waiting for Ollama service..."
until curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
    sleep 2
    echo "   Still waiting..."
done

echo "✅ Ollama service is ready!"

# Check if model is already downloaded
if curl -s http://localhost:11434/api/tags | grep -q "deepseek-r1"; then
    echo "✅ DeepSeek R1 model already exists"
else
    echo "📥 Downloading DeepSeek R1 model (this may take 10-30 minutes)..."
    echo "   Model size: ~4GB"
    echo "   "
    
    # Pull the model (distilled version for CPU)
    docker exec sentrix-deepseek-ai ollama pull deepseek-r1:1.5b
    
    echo "✅ Model downloaded successfully!"
fi

# Test the model
echo ""
echo "🧪 Testing model inference..."
TEST_RESPONSE=$(curl -s http://localhost:11434/api/generate -d '{
  "model": "deepseek-r1:1.5b",
  "prompt": "Is this a SQL injection attempt: SELECT * FROM users WHERE id=1 OR 1=1? Answer with yes or no.",
  "stream": false
}')

if echo "$TEST_RESPONSE" | grep -q "response"; then
    echo "✅ Model is working correctly!"
    echo ""
    echo "Response preview:"
    echo "$TEST_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['response'][:200])"
else
    echo "❌ Model test failed!"
    exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                                                              ║"
echo "║         ✅ DeepSeek R1 Initialized Successfully! 🚀          ║"
echo "║                                                              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Model: DeepSeek R1 (1.5B parameters)"
echo "Mode: CPU-only inference"
echo "Memory: ~4GB RAM"
echo "Speed: ~10-20 tokens/second on CPU"
echo ""
echo "The AI service is now ready for automatic threat analysis!"
echo ""

