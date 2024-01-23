from pydantic import BaseModel, PositiveInt, ConfigDict


class KAITokenCountSchema(BaseModel):
    prompt: str


class MemoirSchema(BaseModel):
    chat_id: str


class KAIGenerationInputSchema(BaseModel):
    model_config = ConfigDict(extra='allow')

    prompt: str
    max_context_length: PositiveInt
    max_length: PositiveInt
    memoir: MemoirSchema


class OAIGenerationInputSchema(BaseModel):
    model_config = ConfigDict(extra='allow')

    prompt: str
    truncation_length: PositiveInt
    stream: bool = False
    memoir: MemoirSchema