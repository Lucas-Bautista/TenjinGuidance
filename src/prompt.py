import os
from anthropic import Anthropic
from anthropic.types import TextBlock

import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

expected_results_path = Path("../expected_results/01_temperature_converter_results.json")
model_names = ["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"]
THINKING_MODES = {"claude-opus-4-6", "claude-sonnet-4-6"}

client = Anthropic(
    # This is the default and can be omitted
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
)

# Load prompt as string
with open("../prompts/baseline_prompt.txt", "r") as f:
    prompt = f.read()

with open("../c_samples/01_temperature_converter.c", "r") as f:
    code = f.read()

final_prompt = prompt.replace("{{CODE}}", code)

messages = []
# print(final_prompt)
for model in model_names:
    kwargs = dict(
        max_tokens=12000,
        messages=[
            {
                "role": "user",
                "content": final_prompt,
            }
        ],
        model=model,
        thinking={
            "type": "disabled",
        },)
    
    if model in THINKING_MODES:
        kwargs["thinking"]["type"] = "adaptive"
    
    # print(kwargs)
    # print(model)
    message = client.messages.create(**kwargs)
    messages.append((model, message))


# message = client.messages.create(
#     max_tokens=12000,
#     messages=[
#         {
#             "role": "user",
#             "content": final_prompt,
#         }
#     ],
#     model="claude-haiku-4-5-20251001",
# )

# Parse JSON response

for model, message in messages:
    print(f"Model: {model}\n")
    text_block = next(block for block in message.content if isinstance(block, TextBlock))
    text = text_block.text

    if text.startswith("```"):
        # drop first line (```json) and last line (```)
        json_str = text.split("\n", 1)[1].rsplit("```", 1)[0]
    else:
        json_str = text

    data = json.loads(json_str)

    with expected_results_path.open("r", encoding="utf-8") as out:
        expected_results = json.load(out)

    print(f"AI Response: {data} \n")
    print(f"Expected Results: {expected_results} + \n")
    for index, item in enumerate(data):
        expected_item = expected_results[index]
        assert item["name"] == expected_item["name"], f"Expected name {expected_item['name']}, got {item['name']}"
        assert item["type"] == expected_item["type"], f"Expected type {expected_item['type']}, got {item['type']}"
        assert item["occurrences"] == expected_item["occurrences"], f"Expected occurrences {expected_item['occurrences']} for {expected_item['name']}, got {item['occurrences']}"
