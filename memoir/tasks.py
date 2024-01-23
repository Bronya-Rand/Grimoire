import requests
from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from llm_helpers import count_context
from loggers import summary_logger
from models import Knowledge
from settings import SIDE_API_URL, DB_ENGINE

celery_app = Celery('tasks', broker='amqp://guest@localhost//')


def make_summary_prompt(session: Session, term: str, label: str, chat_id: str, max_context: int) -> str:
    prompt = f'<s>[INST] Based on following text describe {term}.\n\n'
    instance = session.query(Knowledge).filter_by(entity=term, chat_id=chat_id, entity_label=label).scalar()
    if instance.summary is not None:
        prompt += instance.summary + '\n'
    for message in instance.messages[::-1]:  # reverse order to start from latest message
        new_prompt = prompt + message.message + '\n'
        new_tokens = count_context(new_prompt + '[/INST]', 'KoboldAI', SIDE_API_URL)
        if new_tokens >= max_context:
            break
        else:
            prompt = new_prompt
    prompt += '[/INST]'
    return prompt


@celery_app.task
def summarize(term: str, label: str, chat_id: str, context_len: int = 4096,
              response_len: int = 300) -> None:
    db = create_engine(DB_ENGINE)
    with Session(db) as session:
        prompt = make_summary_prompt(session, term, label, chat_id, context_len)
        json = {
            'prompt': prompt,
            'max_length': response_len,
            "temperature": 0.3,
            "max_context_length": context_len,
            "stop": [
                "</s>"
            ],
            "top_p": 0.95,
            "top_k": 50,
            "rep_pen": 1.2,
            "stop_sequence": [
                "</s>"
            ]
        }
        kobold_response = requests.post(SIDE_API_URL + '/api/v1/generate', json=json)
        response = kobold_response.json()
        summary_text = response['results'][0]['text']
        knowledge_entry = session.query(Knowledge).filter_by(entity=term, chat_id=chat_id, entity_label=label).scalar()
        knowledge_entry.summary = summary_text
        knowledge_entry.token_count = count_context(summary_text, 'KoboldAI', SIDE_API_URL)
        summary_logger.debug(f'({knowledge_entry.token_count} tokens){term} ({label}): {summary_text}\n{json}')
        session.commit()