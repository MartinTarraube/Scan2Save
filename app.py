from flask import Flask, render_template, request, redirect, url_for, jsonify
from google.cloud import vision
import os
import google.generativeai as genai
import pandas as pd

EXCEL_FILE = ''
UPLOADS_FOLDER = 'uploads'

app = Flask(__name__)
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
gem_api_key = os.getenv('GEMINI_API_KEY')
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    global EXCEL_FILE
    if request.method == 'GET':
        return render_template('upload.html')
    
    if 'file' not in request.files and 'imageFile' not in request.files:            
        return jsonify({'success': False, 'message': 'No file part'})
    
    if EXCEL_FILE == "":
        if 'file' in request.files:
            file = request.files['file']
            if file.filename.endswith(('.xlsx', '.xls')):
                EXCEL_FILE = file.filename
                file_path = os.path.join('uploads', file.filename)
                file.save(file_path)
                print('Excel file uploaded.')     
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'message': 'File is not an Excel'})
        else:
            return jsonify({'success': False, 'message': 'No excel file part'})
    else:
        if 'imageFile' in request.files:
            file = request.files['imageFile']            
            if file.content_type.startswith('image/') or file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff')):
                file_path = os.path.join('uploads', file.filename)
                file.save(file_path)
                print('Image file uploaded.')

                text = parse_receipt(file_path)
                parsed_data = parse_with_gemini(text)

                parsed_data = parsed_data.strip()
                
                price, date, merchant = parsed_data.split(' ', 2)
                merchant = merchant.strip('"')
                print(price)
                print(date)
                print(merchant)
                
                return jsonify({'success': True, 'price': price, 'date': date, 'merchant': merchant})
            else:
                return jsonify({'success': False, 'message': 'File is of wrong type'})
        else: 
            return jsonify({'success': False, 'message': 'No image file part'})
    return jsonify({'success': False, 'message': 'Unknown error'})

@app.route('/finalize', methods=['POST'])
def finalize():
    data = request.form.to_dict()
    rows = []
    for key in data:
        if key.startswith('date-'):
            index = key.split('-')[1]
            price = data[key]
            date = data[f'price-{index}']
            merchant = data[f'merchant-{index}']
            rows.append([date, price, merchant])
    append_to_excel(rows)
    return redirect(url_for('home'))

@app.route('/create_excel', methods=['POST'])
def create_excel():
    data = request.get_json()
    file_name = data.get('fileName')
    if not file_name:
        return jsonify({'success': False, 'message': 'File name is required'})
    file_path = os.path.join(UPLOADS_FOLDER, f"{file_name}.xlsx")
    if os.path.exists(file_path):
        return jsonify({'success': False, 'message': 'File already exists'})
    df = pd.DataFrame(columns=['Price', 'Date', 'Merchant'])
    df.to_excel(file_path, index=False)
    global EXCEL_FILE
    EXCEL_FILE = file_path

    return jsonify({'success': True, 'message': 'Excel file created successfully'})


def parse_receipt(file_path):
    client = vision.ImageAnnotatorClient()

    with open(file_path, 'rb') as image_file:
        content = image_file.read()
    image = vision.Image(content=content)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    return texts[0].description if texts else 'no text'

def parse_with_gemini(text):
    genai.configure(api_key=gem_api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    prompt = ('Parse this receipt for the following categories'
        ' and their values: "total", "date", "merchant"\\n'
        'The format of your response should be as follows:\\n'
        'price date merchant'
        '\\nThis means that the ONLY TEXT I want you to provide'
        ' is the value of the price, the date, and the merchant.'
        'Your response should be a maximum of 3 lines long.'
        'Each value should have one space in between them.'
        'The date should be in format YYYY-MM-DD.'
        'Put the merchant value in quotes.')
    response = model.generate_content(prompt + text)
    return response.text

def append_to_excel(rows):
    new_data = pd.DataFrame(rows, columns=['Date', 'Date', 'Merchant'])
    if os.path.exists(EXCEL_FILE):
        df = pd.read_excel(EXCEL_FILE)
        df = pd.concat([df, new_data], ignore_index=True)
    else:
        df = new_data
    df.to_excel(EXCEL_FILE, index=False)

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



if __name__ == '__main__':
    app.run(debug=True, port=5000)