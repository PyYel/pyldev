@echo off
echo === Forwarding vLLM GPU port 8000 -> localhost:8000 ===
echo === Press Ctrl+C to stop ===
kubectl port-forward svc/vllm-vllm 8000:8000 -n default
