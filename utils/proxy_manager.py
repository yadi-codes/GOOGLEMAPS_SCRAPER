import random
from dotenv import load_dotenv
import os

load_dotenv()

def get_proxy():
    proxies = os.getenv('PROXY_LIST', '').split(',')
    if proxies and proxies[0]:
        return {
            'server': random.choice(proxies),
            'username': os.getenv('PROXY_USER'),
            'password': os.getenv('PROXY_PASS')
        }
    return None