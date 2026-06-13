from openai import AsyncOpenAI


class ChatGptService:
    def __init__(self, token):
        self.client = AsyncOpenAI(api_key=token)
        self.message_list = []

    async def send_message_list(self) -> str:
        completion = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.message_list,
            max_tokens=3000,
            temperature=0.9
        )
        message = completion.choices[0].message
        self.message_list.append({"role": message.role, "content": message.content})
        return message.content

    def set_prompt(self, prompt_text: str) -> None:
        self.message_list.clear()
        self.message_list.append({"role": "system", "content": prompt_text})

    async def add_message(self, message_text: str) -> str:
        self.message_list.append({"role": "user", "content": message_text})
        return await self.send_message_list()

    async def send_question(self, prompt_text: str, message_text: str) -> str:
        self.message_list.clear()
        self.message_list.append({"role": "system", "content": prompt_text})
        self.message_list.append({"role": "user", "content": message_text})
        return await self.send_message_list()

    async def send_image_question(self, prompt_text: str, image_url: str) -> str:
        completion = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt_text},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Опиши це зображення згідно з інструкцією системи."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url,
                            },
                        },
                    ],
                }
            ],
            max_tokens=1000
        )
        return completion.choices[0].message.content
