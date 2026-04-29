from os import environ
from tools.azure_open_ai import AzureOpenAI
from util.settings import set_prox, SETTING


# https://learn.microsoft.com/en-us/azure/ai-foundry/openai/reference?view=foundry-classic&completions
def test_openai_completions():
    # set_prox()
    data = {
        "messages": [
            {"role": "user", "content": "What is the airspeed velocity of an unladen swallow?"},
        ],
        "n": 1,
    }

    response = AzureOpenAI.post(data=data)
    if response.ok:
        print(response.json())


if __name__ == "__main__":
    test_openai_completions()
