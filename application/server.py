from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import predictor

app = Flask(__name__)
CORS(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze_headline():
    headline = request.json['headline']
    result = predictor.predict(headline)
    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True)
