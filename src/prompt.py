import os
from anthropic import Anthropic
from anthropic.types import TextBlock

from variable_counts import count_variables

import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# code_sample_path = Path("../c_samples/02_gcd_lcm.c")
# expected_results_path = Path("../expected_results/02_gcd_lcm_results.json")
model_names = ["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"]
THINKING_MODES = {"claude-opus-4-6", "claude-sonnet-4-6"}
client = Anthropic(
    # This is the default and can be omitted
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
)

# Load prompt as string
with open("../prompts/baseline_prompt.txt", "r") as f:
    prompt = f.read()

for f in Path("../c_samples").glob("01_temperature_converter.c"):
    code = f.read_text(encoding="utf-8")
    expected_results = count_variables(f)

    final_prompt = prompt.replace("{{CODE}}", code)

    # See how accurate the model is by comparing its response to expected results
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
        
        message = client.messages.create(**kwargs)
        messages.append((model, message))

    # Parse JSON response
    for model, message in messages:
        print(f"Model: {model}\n")

        # Extract JSON text from the message content
        text_block = next(block for block in message.content if isinstance(block, TextBlock))
        text = text_block.text

        # Clean text
        if text.startswith("```"):
            # drop first line (```json) and last line (```)
            json_str = text.split("\n", 1)[1].rsplit("```", 1)[0]
        else:
            json_str = text

        data = json.loads(json_str)

        
        # print(f"AI Response: {data} \n")
        print(f"Expected Results: {expected_results} + \n")
        total_unique_variables = len(expected_results)
        print(f"Total Unique Variables: {total_unique_variables} \n")
        correctly_identified = 0
        incorrect_variable_counts = []

        for index, inferred_item in enumerate(data):
            current_name = inferred_item["name"]
            guessed_type = inferred_item["type"]
            guessed_occurrences = inferred_item["occurrences"]
            name_found = False

            expected_count = expected_results.get((current_name, guessed_type))
            if expected_count is None:
                print(f"Unexpected variable {current_name} of type {guessed_type} found in AI response")
                continue

            if expected_count == guessed_occurrences:
                correctly_identified += 1
            else:
                incorrect_variable_counts.append({
                    "model": model,
                    "file": f.name,
                    "name": current_name,
                    "type": guessed_type,
                    "expected_occurrences": expected_count,
                    "guessed_occurrences": guessed_occurrences,
                })
        
        print(f"Correctly identified {correctly_identified} out of {total_unique_variables} unique variables (including references) \n")
        print("Percentage correctly identified: {:.2f}%\n".format(correctly_identified / total_unique_variables * 100))
        
        if incorrect_variable_counts:
            print("Incorrect variable counts:")
            for item in incorrect_variable_counts:
                print(f"Model: {item['model']}, File: {item['file']}, Variable: {item['name']} (Type: {item['type']}), Expected Occurrences: {item['expected_occurrences']}, Guessed Occurrences: {item['guessed_occurrences']}")
