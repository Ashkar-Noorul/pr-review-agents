import os 
from dotenv import load_dotenv 
load_dotenv() 
print('Key loaded:', bool(os.getenv('ANTHROPIC_API_KEY')))