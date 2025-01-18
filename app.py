from flask import Flask, render_template, request, redirect, url_for
from google.cloud import vision
import os
import google.generativeai as genai
import pandas as pd

excel_file_path = 0

app = Flask(__name__)
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/home/zmchuang/McWics-hackathon/receipt-parser-448216-ad317ae49a0a.json'
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    

    if request.method == 'POST':
        if 'file' not in request.files: 
            raise Exception("No file part")

        file = request.files['file']

        if excel_file_path == 0:
            detect_excel(file)
        
        elif file:
            if file.content_type.startswith('image/'):
                file_path = os.path.join('uploads', file.filename)
                file.save(file_path)

                text = parse_receipt(file_path)
                parsed_data = parse_with_gemini(text)

                parsed_data = parsed_data.strip()
                
                price, date, merchant = parsed_data.split(' ', 2)
                merchant = merchant.strip('"')
                print(price)
                print(date)
                print(merchant)     
                
                return render_template('result.html', text=parsed_data)
            else:
                raise Exception("File is of wrong type")
                return redirect(url_for('upload'))
    return render_template('upload.html', text=None)

def parse_receipt(file_path):
    client = vision.ImageAnnotatorClient()

    with open(file_path, 'rb') as image_file:
        content = image_file.read()
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    return texts[0].description if texts else 'no text'

def parse_with_gemini(text):
    genai.configure(api_key = os.getenv('GEMINI_API_KEY'))
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = ('Parse this receipt for the following categories'
        ' and their values: "total", "date", "merchant"\\n'
        'The format of your respon should be as follows:\\n'
        'price date merchant'
        '\\nThis means that the ONLY TEXT I want you to provide'
        ' is the value of the price, the date, and the merchant.'
        'Your response should be a maximum of 3 lines long.'
        'Each value should have one space in between them.'
        'The date should be in format YYYY-MM-DD.'
        'Put the merchant value in quotes.')
    response = model.generate_content(prompt + text)
    return response.text

def modify_excel_price(prix, the_path):
    df = pd.read_excel(the_path)

    #add new value to end of 2nd column
    df.loc[len(df), df.columns[1]] = prix
    total_sum = df.iloc[:, 1].sum()
    df.to_excel(the_path, index=False)
    return total_sum

def modify_excel_date(date, the_path):
    df = pd.read_excel(the_path)

    #add new value to end of 2nd column
    df.loc[len(df), df.columns[0]] = date
    
    df.to_excel(the_path, index=False)
    return 

def modify_excel_merchant(merchant, the_path):
    df = pd.read_excel(the_path)

    #add new value to end of 2nd column
    df.loc[len(df), df.columns[2]] = merchant
    
    df.to_excel(the_path, index=False)
    return

def detect_excel(file):
    if file and file.filename.endswith(('.xlsx', '.xls')):
        excel_file_path = file
    return

if __name__ == '__main__':
    app.run(debug=True, port=5000)