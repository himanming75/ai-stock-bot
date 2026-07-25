import os
from dotenv import load_dotenv
from openai import OpenAI

# .env 파일 읽기
load_dotenv()

# API Key 가져오기
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY를 찾을 수 없습니다.")

# OpenAI Client 생성
client = OpenAI(api_key=api_key)


def ask_ai(prompt):
    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt
    )

    return response.output_text