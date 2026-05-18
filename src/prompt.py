import os
from anthropic import Anthropic
from anthropic.types import TextBlock

from variable_counts import count_variables

import json
from pathlib import Path
from dotenv import load_dotenv

_TRACTOR_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_TRACTOR_ROOT / ".env")
load_dotenv()

# code_sample_path = Path("../c_samples/02_gcd_lcm.c")
# expected_results_path = Path("../expected_results/02_gcd_lcm_results.json")
# model_names = ["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"]
model_names = ["claude-opus-4-6"]

THINKING_MODES = {"claude-opus-4-6", "claude-sonnet-4-6"}
client = Anthropic(
    # This is the default and can be omitted
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
)
def clean_json_response(text: str) -> str:
    # Normalize leading/trailing whitespace so leading newlines don't break detection
    t = text.strip()

    # If the response is wrapped in a code block, extract the JSON part
    if t.startswith("```"):
        json_str = t.split("\n", 1)[1].rsplit("```", 1)[0]
        return json_str.strip()

    return t

def _write_llm_record(
    record_dir: Path,
    record_name: str,
    *,
    code_path: Path,
    prompt_path: Path,
    data_heading: str,
    json_key: str,
    system_prompt: str,
    user_prompt: str,
    model_names_used: list[str],
    responses: list[tuple[str, dict]],
) -> None:
    record_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "code_path": str(code_path.resolve()),
        "prompt_path": str(prompt_path.resolve()),
        "data_heading": data_heading,
        "json_key": json_key,
        "models": model_names_used,
        "record_name": record_name,
    }
    (record_dir / f"{record_name}_meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=False), encoding="utf-8"
    )
    (record_dir / f"{record_name}_system.txt").write_text(system_prompt, encoding="utf-8")
    (record_dir / f"{record_name}_user.txt").write_text(user_prompt, encoding="utf-8")
    serializable = [{"model": m, "parsed_json": d} for m, d in responses]
    (record_dir / f"{record_name}_response.json").write_text(
        json.dumps(serializable, indent=2, sort_keys=False, default=str),
        encoding="utf-8",
    )


def prompt(
    code_path: Path,
    prompt_path: Path,
    json_input: str | None,
    compile_errors: str | None = None,
    *,
    data_heading: str = "Variables",
    json_key: str = "counts",
    record_dir: Path | None = None,
    record_name: str = "llm_call",
) -> list[tuple[str, dict]]:
    # Load prompt as string
    system_prompt = prompt_path.read_text(encoding="utf-8")
    code = code_path.read_text(encoding="utf-8")
    json_part = json_input if json_input is not None else "null"
    user_prompt = f"""Source code:
                    {code}

                    {data_heading}:
                    {{
                    {json.dumps(json_key)}: {json_part}
                    }}

                    Compiler errors from previous translation attempt:
                    {compile_errors or ""}"""

    # See how accurate the model is by comparing its response to expected results
    messages = []
    # print(final_prompt)
    for model in model_names:
        kwargs = dict(
            max_tokens=12000,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": user_prompt,
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

    organized_responses = []
    # Parse JSON response
    for model, message in messages:
        print(f"Model: {model}\n")
        # print(f"Guessed content: {message.content}\n")

        # Extract JSON text from the message content
        text_block = next(block for block in message.content if isinstance(block, TextBlock))
        text = text_block.text

        # Clean text
        json_str = clean_json_response(text)
        print(f"Guessed values {json_str} \n")
        data = json.loads(json_str)
        organized_responses.append((model, data))

    if record_dir is not None:
        _write_llm_record(
            record_dir,
            record_name,
            code_path=code_path,
            prompt_path=prompt_path,
            data_heading=data_heading,
            json_key=json_key,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model_names_used=list(model_names),
            responses=organized_responses,
        )
    return organized_responses


def evaluate():
    # Declare prompt, code sample, and json
    code_sample_path = Path("../c_samples/02_gcd_lcm.c")
    prompt_path = Path("../prompts/baseline_prompt.txt")
    responses = prompt(code_sample_path, prompt_path, None, None)
    expected_results = count_variables("../c_samples/02_gcd_lcm.c")
    

    print("expected_results:", expected_results, "\n\n")

    for model, data in responses: 
        print(f"Model: {model}\n")
        print(f"Data: {data}\n")
        correctly_identified = 0
        incorrect_variable_counts = []
        total_unique_variables = len(expected_results)
    
        # Iterate through all expected variables and their counts
        for key, expected_count in expected_results.items():
            (expected_name, expected_variable_type) = key

            # iterate through all model responses and see if any of them correctly identified the variable and its count
            found_corresponding_variable = False
            for inferred_item in data:
                guessed_name = inferred_item["name"]
                guessed_type = inferred_item["type"]
                guessed_occurrences = inferred_item["occurrences"]
                if (expected_name == guessed_name):
                    if expected_count == guessed_occurrences and expected_variable_type == guessed_type:
                        correctly_identified += 1
                    else:
                        incorrect_variable_counts.append({
                            "model": model,
                            "file": code_sample_path.name,
                            "guessed_name": guessed_name,
                            "guessed_type": guessed_type,
                            "name": expected_name,
                            "type": expected_variable_type,
                            "expected_occurrences": expected_count,
                            "guessed_occurrences": guessed_occurrences,
                        })
                    found_corresponding_variable = True
                    break

            if not found_corresponding_variable:
                incorrect_variable_counts.append({
                    "model": model,
                    "file": code_sample_path.name,
                    "guessed_name": "Not found",
                    "guessed_type": "Not found",
                    "name": expected_name,
                    "type": expected_variable_type,
                    "expected_occurrences": expected_count,
                    "guessed_occurrences": 0,
                })
            
        print(f"Correctly identified {correctly_identified} out of {total_unique_variables} unique variables (including references) \n")
        print("Percentage correctly identified: {:.2f}%\n".format(correctly_identified / total_unique_variables * 100))
        
        if incorrect_variable_counts:
            print("Incorrect variable counts:")
            for item in incorrect_variable_counts:
                print(f"Model: {item['model']}, File: {item['file']}, Variable: {item['name']} (Type: {item['type']}),Expected Occurrences: {item['expected_occurrences']}, Guessed Occurrences: {item['guessed_occurrences']}, guessed type: {item['guessed_type']}\n")


if __name__ == "__main__":    evaluate()