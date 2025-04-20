import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")  # Set in .env or export in terminal

def summarize_text(text):
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": f"Summarize this: {text}"}]
    )
    return response.choices[0].message["content"]

if __name__ == "__main__":
    summary = summarize_text("The quick brown fox jumps over the lazy dog.")
    print("Summary:", summary)
