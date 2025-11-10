from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "Discord Bot is alive!"

def keep_alive():
    """Start a Flask web server to keep the bot alive on Replit"""
    def run():
        app.run(host='0.0.0.0', port=5000)
    
    thread = Thread(target=run)
    thread.daemon = True
    thread.start()
