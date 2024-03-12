import openai
import tiktoken
import time
import google.generativeai as palm

with open("gpt-key-2") as f:
    openai.api_key = f.read()

with open("palm-key") as f:
    palm.configure(api_key=f.read())

def extract_response_gpt(response):
    return response['choices'][0]['message']['content']

def get_completion_messages_gpt(messages, temperature, model):
    assert model.startswith('gpt')
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
    num_tokens = len(enc.encode("\n".join([i['content'] for i in messages]))) + 50
    retry = 3
    retry_times = [15, 30, 120, 200]
    while (retry):
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=temperature,  # this is the degree of randomness of the model's output
                max_tokens=4097 - num_tokens - 20,
            )
            retry = 0
        except openai.error.RateLimitError as e:
            # pdb.set_trace()
            response = {}
            print(f"Rate limited. retrying: {retry - 1}")
            ind = 3-retry
            time.sleep(retry_times[ind])
            retry -= 1
            if retry == 0:
                raise

    return response, extract_response_gpt(response)


def transform_to_palm_messages(messages):
    context = "\n".join([i["content"] for i in messages if i['role']=='system'])
    non_system_messages = [i["content"] for i in messages if i['role']!='system']
    examples = [(user, chatbot) for user, chatbot in zip(non_system_messages[0::2], non_system_messages[1::2])]
    message = non_system_messages[-1]

    return context, examples, message

def extract_response_palm(response):
    try:
        res = response.messages[-1]['content']
    except:
        res = ''
    return  res
def get_completion_messages_palm(messages, temperature, model):
    assert model == 'palm'
    palm_defaults = {
        'model': 'models/chat-bison-001',
        'temperature': min(1, temperature),
        'candidate_count': 1,
        'top_k': 40,
        'top_p': 0.95,
        # 'max_output_tokens': 1024,
        # 'stop_sequences': [],
        # 'safety_settings': [{"category": "HARM_CATEGORY_DEROGATORY", "threshold": 1},
        #                     {"category": "HARM_CATEGORY_TOXICITY", "threshold": 1},
        #                     {"category": "HARM_CATEGORY_VIOLENCE", "threshold": 2},
        #                     {"category": "HARM_CATEGORY_SEXUAL", "threshold": 2},
        #                     {"category": "HARM_CATEGORY_MEDICAL", "threshold": 2},
        #                     {"category": "HARM_CATEGORY_DANGEROUS", "threshold": 2}],
    }


    context, examples, message = transform_to_palm_messages(messages)

    response = palm.chat(
        **palm_defaults,
        context=context,
        examples=examples,
        messages=message
    )
    resp_dict = response.to_dict()
    resp_dict['filters'] = response.filters
    return resp_dict, extract_response_palm(response)


def get_completion_messages(messages, temperature, model):
    fun_mapping = {
        'gpt-3.5-turbo': get_completion_messages_gpt,
        'gpt-4': get_completion_messages_gpt,
        'palm': get_completion_messages_palm
    }
    completion_func = fun_mapping[model]


    starttime = time.time()
    response, response_extracted = completion_func(messages, temperature, model)
    endtime = time.time()

    return response, response_extracted,  endtime-starttime