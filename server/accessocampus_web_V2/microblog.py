from app import app, db
from app.models import User, Post
import subprocess


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Post': Post}

print("Started!")
subprocess.Popen("python3 accessocampus_full_mqtt_server_web.py 1", shell=True)
