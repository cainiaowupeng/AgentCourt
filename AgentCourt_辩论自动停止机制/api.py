from config import Config
from openai import OpenAI


def run_api(prompt, stream=False):
    gpt_params = {
        "temperature": Config.temperature,
        "top_p": Config.top_p,
        "stream": stream,
        "frequency_penalty": Config.frequency_penalty,
        "presence_penalty": Config.presence_penalty,
    }
    message = [{
        "role": "user",
        "content": prompt
    }]
    client = OpenAI(
        base_url=Config.api_url,
        api_key=Config.api_key
    )
    retry = Config.MAX_RETRY
    if not stream:
        # 非流式处理
        while True:
            try:
                completion = client.chat.completions.create(
                    model=Config.api_model,
                    messages=message,
                    temperature=gpt_params["temperature"],
                    top_p=gpt_params["top_p"],
                    stream=gpt_params["stream"],
                    frequency_penalty=gpt_params["frequency_penalty"],
                    presence_penalty=gpt_params["presence_penalty"],
                )
                result = completion.choices[0].message.content
                break
            except Exception as e:
                if retry > 0:
                    retry -= 1
                    continue
                raise ConnectionError('Api Failed with Exception {}'.format(e))
        return result
    else:
        # 流式处理
        while True:
            try:
                completion = client.chat.completions.create(
                    model=Config.api_model,
                    messages=message,
                    temperature=gpt_params["temperature"],
                    top_p=gpt_params["top_p"],
                    stream=stream,
                    frequency_penalty=gpt_params["frequency_penalty"],
                    presence_penalty=gpt_params["presence_penalty"],
                )

                # 创建一个生成器来逐步返回结果
                def generate():
                    collected_chunks = []
                    for chunk in completion:
                        if chunk.choices[0].delta.content is not None:
                            content = chunk.choices[0].delta.content
                            collected_chunks.append(content)
                            yield content

                return generate()

            except Exception as e:
                if retry > 0:
                    retry -= 1
                    continue
                raise ConnectionError('Api Failed with Exception {}'.format(e))


def test_api(message=None):
    if message is None:
        while True:
            message = input()
            if message == 'q':
                break
            for chunk in run_api(prompt=message, stream=True):
                print(chunk, end='', flush=True)
    else:
        for chunk in run_api(prompt=message, stream=True):
            print(chunk, end='', flush=True)


if __name__ == '__main__':
    test_api('请简单介绍一下你自己')
