from ai.analyst import ask_ai

print("=" * 50)
print("AI STOCK TRADING BOT")
print("=" * 50)

question = """
Apple 주식을 간단하게 분석해줘.
3줄 정도로 설명해줘.
"""

answer = ask_ai(question)

print(answer)