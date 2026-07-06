import os
from pathlib import Path
from datetime import datetime
import anthropic

SYSTEM_PROMPT_FILE = "Prompt.txt"

client = anthropic.Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"]
)

def create_prompt_file(email_file_path: str) -> tuple[str, str]:
    script_dir = Path(__file__).parent
    prompt_template_path = script_dir / SYSTEM_PROMPT_FILE

    if not prompt_template_path.exists():
        raise FileNotFoundError(
            f"Prompt.txt not found: {prompt_template_path}"
        )

    email_path = Path(email_file_path)

    if not email_path.exists():
        raise FileNotFoundError(
            f"Email file not found: {email_path}"
        )

    with open(prompt_template_path, "r", encoding="utf-8") as f:
        prompt_text = f.read()

    with open(email_path, "r", encoding="utf-8") as f:
        email_content = f.read()

    output_text = prompt_text.replace(
        "{{EMAIL_TEXT}}",
        email_content
    )

    timestamp = datetime.now().strftime("%m%d%y%H%M%S")

    output_file = script_dir / f"prompt-{timestamp}.txt"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(output_text)

    return str(output_file), timestamp


def read_file(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


def call_claude(prompt: str, model: str = "claude-sonnet-5", max_tokens: int = 1024) -> str:
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return message.content[0].text


def save_response_file(
    response_text: str,
    timestamp: str
) -> str:

    script_dir = Path(__file__).parent

    response_file = script_dir / f"response-{timestamp}.txt"

    with open(response_file, "w", encoding="utf-8") as f:
        f.write(response_text)

    return str(response_file)


def process_email(email_file_path: str) -> tuple[str, str]:
    prompt_file, timestamp = create_prompt_file(
        email_file_path
    )

    prompt_text = read_file(prompt_file)

    response_text = call_claude(prompt_text)

    response_file = save_response_file(
        response_text,
        timestamp
    )

    return prompt_file, response_file