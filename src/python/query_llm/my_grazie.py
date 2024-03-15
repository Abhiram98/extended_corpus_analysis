import click
import os
import time

from grazie.api.client.chat.prompt import ChatPrompt
from grazie.api.client.endpoints import GrazieApiGatewayUrls
from grazie.api.client.gateway import GrazieApiGatewayClient, GrazieAgent, AuthType
from grazie.api.client.llm_parameters import LLMParameters
from grazie.api.client.parameters import Parameters
from grazie.api.client.profiles import Profile

LLM_MAPPING = {
    'GPT-4': Profile.OPENAI_GPT_4,
    'GPT-3.5-TURBO': Profile.OPENAI_CHAT_GPT
}


def build_chat_prompt(chat_messages):
    chat_prompt = ChatPrompt()
    for message in chat_messages:
        if message['role'] == 'system':
            chat_prompt.add_system(message['content'])
        elif message['role'] == 'user':
            chat_prompt.add_user(message['content'])
        elif message['role'] == 'assistant':
            chat_prompt.add_assistant(message['content'])
    return chat_prompt


def query(llm_name, temperature, chat_messages):
    starttime = time.time()
    llm_name = llm_name.upper()
    client = GrazieApiGatewayClient(
        grazie_agent=GrazieAgent(name="llm4-function-improvements", version="dev"),
        url=GrazieApiGatewayUrls.STAGING,
        auth_type=AuthType.SERVICE,
        grazie_jwt_token=os.environ["GRAZIE_JWT_TOKEN"],
    )

    response = client.chat(
        chat=build_chat_prompt(chat_messages),
        profile=LLM_MAPPING.get(llm_name, Profile.OPENAI_GPT_4),
        parameters={
            LLMParameters.Temperature: Parameters.FloatValue(temperature)
        },
        prompt_id='v1'
    )

    click.echo(response.content)
    endtime = time.time()
    return response.__str__(), response.content, endtime-starttime


@click.command()
@click.option("--prompt-str", help='String to prompt LLM with.')
@click.option("--system-msg", help='System message for LLM', default='You are an expert programmer.')
@click.option('--temperature', default=0.7, help='LLM Temperature.', type=float)
@click.option('--llm-name', default='GPT-4', help='LLM to query!')
def main(prompt_str, system_msg, temperature, llm_name):
    query(prompt_str, system_msg, temperature, llm_name)


if __name__ == '__main__':
    main()
