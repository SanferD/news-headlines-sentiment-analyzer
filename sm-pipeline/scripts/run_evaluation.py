import os

os.system("apt-get update && apt-get install ffmpeg libsm6 libxext6 -y")
os.system("pip install -r /opt/ml/processing/scripts/requirements.txt")
os.system("python /opt/ml/processing/scripts/evaluation.py")
