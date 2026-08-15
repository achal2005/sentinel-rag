"""Sentinel LoRA router — training + benchmark, for a free Kaggle T4 GPU.

Paste this into a single Kaggle notebook cell (GPU T4 x1 enabled), or run as a
utility script. It:
  1. loads a small base model,
  2. LoRA-fine-tunes it to emit the routing JSON,
  3. evaluates the adapter on evals/golden.json with the SAME metrics as
     backend/app/eval_routing.py, and prints a benchmark table vs. the 88.6%
     prompted baseline.

INPUT FILES (upload finetune/data/{train,val}.jsonl and evals/golden.json as a
Kaggle Dataset named 'sentinel-router', so they land in /kaggle/input/sentinel-router/):
    train.jsonl  val.jsonl  golden.json

HF TOKEN: meta-llama/Llama-3.2-1B-Instruct is gated. Accept the license once on
HuggingFace and add your token as a Kaggle Secret named HF_TOKEN (or set BASE to
the ungated mirror below).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

# A 1B model fits easily on ONE T4. If Kaggle gives you "GPU T4 x2", pin to a
# single GPU — multi-GPU + device_map="auto" + HF Trainer can shard the model
# and break training. Must be set before torch is imported.
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

# ---------------------------------------------------------------- config
# Ungated mirror (no HF token/license needed) — this is what the recorded run used.
BASE = "unsloth/Llama-3.2-1B-Instruct"
# Alternatives:
# BASE = "meta-llama/Llama-3.2-1B-Instruct"  # official weights; gated, needs HF_TOKEN
# BASE = "Qwen/Qwen2.5-1.5B-Instruct"         # stronger base to try closing the gap

def _find(name: str) -> Path:
    """Locate an input file regardless of the dataset slug/mount path."""
    hits = sorted(Path("/kaggle/input").rglob(name))
    if not hits:
        raise FileNotFoundError(f"{name} not found anywhere under /kaggle/input")
    return hits[0]


TRAIN_PATH = _find("train.jsonl")
VAL_PATH = _find("val.jsonl")
GOLDEN_PATH = _find("golden.json")
OUT_DIR = Path("/kaggle/working/sentinel-router-lora")
EPOCHS = 3
LR = 2e-4
MAX_LEN = 512
BASELINE_ROUTING_ACC = 0.886  # prompted llama3.2:3b, from backend/app/eval_routing.py

ROUTES = {"answer", "action", "escalate", "spam"}
URGENCIES = {"low", "medium", "high"}

SYSTEM = (
    "You are the triage router for Meridian's support system. Classify the "
    "user's request and reply with ONLY a JSON object with keys: route "
    "(answer|action|escalate|spam), intent, urgency (low|medium|high), "
    "action_required (boolean)."
)

# ---------------------------------------------------------------- setup
# We deliberately avoid `trl` (its API churns across versions). Plain
# transformers.Trainer + PEFT is far more stable.
os.system(
    "pip -q install -U 'transformers==4.46.3' 'peft==0.13.2' "
    "'accelerate>=0.34' 'datasets>=2.20'"
)
# Kaggle ships torchao 0.10, which newer PEFT rejects at import; we don't use it
# for fp16 LoRA, so remove it to let PEFT's check short-circuit cleanly.
os.system("pip -q uninstall -y torchao")

import torch
from datasets import load_dataset
from peft import LoraConfig, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    DataCollatorForSeq2Seq,
    Trainer,
    TrainingArguments,
)

HF_TOKEN = os.environ.get("HF_TOKEN")
try:  # pull token from Kaggle Secrets if present
    from kaggle_secrets import UserSecretsClient
    HF_TOKEN = HF_TOKEN or UserSecretsClient().get_secret("HF_TOKEN")
except Exception:
    pass

tok = AutoTokenizer.from_pretrained(BASE, token=HF_TOKEN)
if tok.pad_token is None:
    tok.pad_token = tok.eos_token

model = AutoModelForCausalLM.from_pretrained(
    BASE, token=HF_TOKEN, torch_dtype=torch.float16, device_map="auto"
)

# ---------------------------------------------------------------- data
def target_json(row: dict) -> str:
    return json.dumps(
        {
            "route": row["route"],
            "intent": row["intent"],
            "urgency": row["urgency"],
            "action_required": bool(row["action_required"]),
        },
        ensure_ascii=False,
    )


def preprocess(row: dict) -> dict:
    """Tokenize to (input_ids, labels) with the prompt masked out (-100), so loss
    is computed only on the assistant JSON completion."""
    prompt_msgs = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": row["text"]},
    ]
    full_msgs = prompt_msgs + [{"role": "assistant", "content": target_json(row)}]
    # Template to text, then tokenize explicitly (returns plain int lists, which
    # Arrow can serialize; apply_chat_template(tokenize=True) can return Encoding
    # objects on some versions).
    prompt_text = tok.apply_chat_template(prompt_msgs, tokenize=False, add_generation_prompt=True)
    full_text = tok.apply_chat_template(full_msgs, tokenize=False)
    prompt_ids = tok(prompt_text, add_special_tokens=False)["input_ids"]
    full_ids = tok(full_text, add_special_tokens=False)["input_ids"][:MAX_LEN]
    labels = list(full_ids)
    for i in range(min(len(prompt_ids), len(labels))):
        labels[i] = -100  # mask the prompt; train only on the completion
    return {"input_ids": full_ids, "attention_mask": [1] * len(full_ids), "labels": labels}


ds = load_dataset(
    "json",
    data_files={"train": str(TRAIN_PATH), "val": str(VAL_PATH)},
)
train_ds = ds["train"].map(preprocess, remove_columns=ds["train"].column_names)

# Wrap the base model with LoRA adapters.
lora = LoraConfig(
    r=16, lora_alpha=32, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
)
model = get_peft_model(model, lora)
model.print_trainable_parameters()

collator = DataCollatorForSeq2Seq(tok, model=model, padding=True, label_pad_token_id=-100)

args = TrainingArguments(
    output_dir=str(OUT_DIR),
    num_train_epochs=EPOCHS,
    per_device_train_batch_size=8,
    gradient_accumulation_steps=2,
    learning_rate=LR,
    warmup_ratio=0.05,
    logging_steps=10,
    save_strategy="no",
    fp16=True,
    report_to="none",
)

trainer = Trainer(
    model=model,
    args=args,
    train_dataset=train_ds,
    data_collator=collator,
    tokenizer=tok,
)
trainer.train()
model.save_pretrained(str(OUT_DIR))
tok.save_pretrained(str(OUT_DIR))
print(f"\nSaved LoRA adapter to {OUT_DIR}")

# ---------------------------------------------------------------- benchmark on golden
model.eval()


def predict(text: str) -> dict:
    msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}]
    prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inp = tok(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inp, max_new_tokens=64, do_sample=False,
                             pad_token_id=tok.pad_token_id)
    gen = tok.decode(out[0][inp["input_ids"].shape[1]:], skip_special_tokens=True)
    m = re.search(r"\{.*\}", gen, re.DOTALL)
    try:
        obj = json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        obj = {}
    route = str(obj.get("route", "")).lower()
    urg = str(obj.get("urgency", "")).lower()
    if route not in ROUTES:
        route = "escalate"  # safe fallback, same as the prompted router
    if urg not in URGENCIES:
        urg = "low"
    return {"route": route, "urgency": urg}


cases = json.loads(GOLDEN_PATH.read_text())["cases"]
n = len(cases)
route_ok = urg_ok = urg_den = 0
esc_must = esc_hit = ans_n = over_esc = 0
for c in cases:
    exp = c["expected"]
    p = predict(c["input"])
    route_ok += p["route"] == exp["route"]
    if exp.get("urgency"):
        urg_den += 1
        urg_ok += p["urgency"] == exp["urgency"]
    if exp.get("must_escalate"):
        esc_must += 1
        esc_hit += p["route"] == "escalate"
    if exp["route"] == "answer":
        ans_n += 1
        over_esc += p["route"] == "escalate"

print("\n================ LoRA router — benchmark on golden.json ================")
print(f"Routing accuracy         : {100*route_ok/n:5.1f}%  ({route_ok}/{n})")
print(f"Urgency accuracy         : {100*urg_ok/urg_den:5.1f}%  ({urg_ok}/{urg_den})")
print(f"Escalation recall        : {100*esc_hit/esc_must:5.1f}%  ({esc_hit}/{esc_must})")
print(f"Answerable over-escalated: {100*over_esc/ans_n:5.1f}%  ({over_esc}/{ans_n})")
print("-----------------------------------------------------------------------")
print(f"Prompted baseline routing: {100*BASELINE_ROUTING_ACC:5.1f}%")
delta = 100 * (route_ok / n - BASELINE_ROUTING_ACC)
print(f"Delta (LoRA - baseline)  : {delta:+.1f} pts")
print("=======================================================================")
