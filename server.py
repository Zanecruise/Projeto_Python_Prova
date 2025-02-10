from flask import Flask, request
from automation import processar_dados

app = Flask(__name__)

@app.route('/processar', methods=['POST'])
def processar():
    dados = request.json
    return processar_dados(dados)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
