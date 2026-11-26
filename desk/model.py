"""Local model backend. No API keys, no cost: a small open model
(Qwen2.5-0.5B-Instruct by default) runs on CPU via transformers.

Two backends:
- LocalHF: downloads the model from HuggingFace and runs it in-process.
- OllamaHTTP: talks to a local Ollama server (http://localhost:11434),
  for machines that already run Ollama.
"""
import json
import urllib.request

import torch
torch.set_num_threads(2)

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"


class LocalHF:
    def __init__(self, name=MODEL_NAME):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.tok = AutoTokenizer.from_pretrained(name)
        self.m = AutoModelForCausalLM.from_pretrained(name, dtype=torch.bfloat16)
        self.m.eval()

    def generate(self, prompt, seed=0, max_new_tokens=220):
        enc = self.tok.apply_chat_template(
            [{"role": "user", "content": prompt}],
            add_generation_prompt=True, return_tensors="pt", return_dict=True)
        torch.manual_seed(seed)
        out = self.m.generate(**enc, max_new_tokens=max_new_tokens,
                              do_sample=True, temperature=0.7, top_p=0.9,
                              pad_token_id=self.tok.eos_token_id)
        return self.tok.decode(out[0][enc["input_ids"].shape[1]:],
                               skip_special_tokens=True)


class OllamaHTTP:
    def __init__(self, name="qwen2.5:0.5b", url="http://localhost:11434"):
        self.name, self.url = name, url

    def generate(self, prompt, seed=0, max_new_tokens=220):
        body = json.dumps({"model": self.name, "prompt": prompt,
                           "stream": False,
                           "options": {"seed": seed, "temperature": 0.7,
                                       "num_predict": max_new_tokens}}).encode()
        req = urllib.request.Request(self.url + "/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())["response"]


def extract_json(text):
    """Pull the first JSON object out of a model reply. Raises if none."""
    start = text.find("{")
    if start < 0:
        raise ValueError("no json in reply")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("unbalanced json in reply")
