import re
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import PyPDF2
import torch

WHITESPACE_HANDLER = lambda k: re.sub('\s+', ' ', re.sub('\n+', ' ', k.strip()))

def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text()
    return text

def chunk_text(text, chunk_size=2000):
    words = text.split()
    return [' '.join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

def summarize_chunk(chunk, tokenizer, model, device):
    input_ids = tokenizer(
        [WHITESPACE_HANDLER(chunk)],
        return_tensors="pt",
        padding="max_length",
        truncation=True,
        max_length=512
    )["input_ids"].to(device)

    output_ids = model.generate(
        input_ids=input_ids,
        max_length=256,
        min_length=50,
        no_repeat_ngram_size=2,
        num_beams=4
    )[0]

    return tokenizer.decode(
        output_ids,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False
    )

def summarize_pdf(pdf_path):
    # Check if CUDA is available
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    model_name = "csebuetnlp/mT5_multilingual_XLSum"
    tokenizer = AutoTokenizer.from_pretrained(model_name, legacy=True)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(device)

    text = extract_text_from_pdf(pdf_path)
    chunks = chunk_text(text)
    
    summaries = []
    for chunk in chunks:
        summary = summarize_chunk(chunk, tokenizer, model, device)
        summaries.append(summary)
    
    return " ".join(summaries)

# # Usage
# pdf_path = "data/pokhrel2021.pdf"
# final_summary = summarize_pdf(pdf_path)
# print(final_summary)