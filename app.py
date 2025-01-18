from flask import Flask, render_template, request, redirect, url_for
from google.cloud import vision
import os

app = Flask(__name__)
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = process.env.GOOGLE_APPLICATION_CREDENTIALS
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)