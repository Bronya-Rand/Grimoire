import uvicorn
from dotenv import load_dotenv

from memoir.api.client import app

if __name__ == '__main__':
    load_dotenv()
    uvicorn.run(app, host="127.0.0.1", port=5005)
