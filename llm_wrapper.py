from llama_cpp import Llama
import os

class SovereignLLM:
    def __init__(self, model_path, n_gpu_layers=0, n_ctx=2048):
        print(f"  Loading {os.path.basename(model_path)}...")
        self.llm = Llama(model_path=model_path, n_gpu_layers=n_gpu_layers,
                         n_ctx=n_ctx, verbose=False)
        print(f"  ✅ {os.path.basename(model_path)} loaded")

    def generate(self, user_prompt, system_prompt=None, max_tokens=120):
        if system_prompt is None:
            system_prompt = "You are Sovereign, an AI governance system. Be precise and brief."
        # Phi-3 chat format
        prompt = (
            f"<|system|>\n{system_prompt}<|end|>\n"
            f"<|user|>\n{user_prompt}<|end|>\n"
            f"<|assistant|>\n"
        )
        result = self.llm(prompt, max_tokens=max_tokens,
                          stop=["<|end|>","<|user|>"], echo=False)
        return result["choices"][0]["text"].strip()
