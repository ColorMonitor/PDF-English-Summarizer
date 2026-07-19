from beam import Image, Volume, endpoint


MODEL_PATH = "/model"
MAX_INPUT_TOKENS = 2048
MIN_SUMMARY_TOKENS = 32
MAX_SUMMARY_TOKENS = 256
SUMMARY_SOURCE_TOKEN_RATIO = 0.35


def load_model():
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, local_files_only=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(
        MODEL_PATH,
        local_files_only=True,
        dtype=torch.bfloat16,
    )
    model.to("cuda")
    model.eval()
    return model, tokenizer


def summary_token_budget(source_tokens):
    budget = max(MIN_SUMMARY_TOKENS, int(source_tokens * SUMMARY_SOURCE_TOKEN_RATIO))
    return min(MAX_SUMMARY_TOKENS, budget)


@endpoint(
    name="kls-pdf-summarizer",
    on_start=load_model,
    volumes=[Volume(name="kls-model", mount_path=MODEL_PATH)],
    image=Image(
        python_version="python3.11",
        python_packages=[
            "torch==2.13.0",
            "transformers==5.13.0",
            "sentencepiece==0.2.1",
            "safetensors==0.8.0",
        ],
    ),
    gpu="RTX4090",
    cpu=4,
    memory="16Gi",
    timeout=180,
    keep_warm_seconds=180,
    workers=1,
    authorized=True,
)
def summarize(context, **inputs):
    import torch

    text = inputs.get("text", "")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must be a non-empty string")
    if len(text) > 200_000:
        raise ValueError("text exceeds the 200,000-character limit")

    page_number = int(inputs.get("page_number", 1))
    if page_number < 1:
        raise ValueError("page_number must be at least 1")

    model, tokenizer = context.on_start_value
    encoded = tokenizer(
        text,
        max_length=MAX_INPUT_TOKENS,
        truncation=True,
        return_tensors="pt",
    )
    token_count = int(encoded["input_ids"].shape[1])
    truncated = len(tokenizer.encode(text, add_special_tokens=True)) > MAX_INPUT_TOKENS
    encoded = {key: value.to("cuda") for key, value in encoded.items()}

    with torch.inference_mode():
        generated = model.generate(
            **encoded,
            max_new_tokens=summary_token_budget(token_count),
            num_beams=4,
            length_penalty=0.8,
            no_repeat_ngram_size=4,
            repetition_penalty=1.08,
            early_stopping=True,
        )

    summary = tokenizer.decode(generated[0], skip_special_tokens=True).strip()
    return {
        "page_number": page_number,
        "char_count": len(text),
        "token_count": token_count,
        "truncated": truncated,
        "summary": summary or "The model returned an empty summary for this page.",
    }
