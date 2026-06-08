

A note on how to route multiple models/ The key points should be:

- No model across multiple gpus, to maximise bus speed
- Multiple same model pods for slm
- Single gpu can also share multiple models on different pod
- In my opinion, we should have:
    - GPU0: SLM (for agents, autonomous tasks)
    - GPU1: LLM 1 (eg: llama 70B)
    - GPU2: LLM2 or more SLM
    - GPU3: embedding models, other utils models


model_list:
  - model_name: qwen-production
    litellm_params:
      model: openai/Qwen/Qwen2.5-7B-Instruct
      api_base: http://vllm-qwen-pod-1:8000/v1 # Unique Pod 1 IP/Service
      api_key: not-needed
  - model_name: qwen-production
    litellm_params:
      model: openai/Qwen/Qwen2.5-7B-Instruct
      api_base: http://vllm-qwen-pod-2:8000/v1 # Unique Pod 2 IP/Service
      api_key: not-needed

router_settings:
  routing_strategy: least-busy # 