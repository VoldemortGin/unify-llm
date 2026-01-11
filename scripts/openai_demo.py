from openai import OpenAI
import rootutils

ROOT_DIR = rootutils.setup_root(search_from=__file__, indicator=[".project-root"], pythonpath=True)


from unify_llm import settings

llm = OpenAI(api_key=settings.OPENAI_API_KEY)


if __name__ == '__main__':
    response = llm.chat.completions.create(model='gpt-5-nano', messages=[{"role": "user", "content": "Hello!"}])

    print(response)
