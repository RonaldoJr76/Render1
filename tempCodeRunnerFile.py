from flask import Flask, render_template, request, send_from_directory, redirect, url_for
import os
import sqlite3

app = Flask(__name__)
UPLOAD_FOLDER = 'static'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DB_NAME = 'notas.db'

# --- Configuração do Gabarito ---
GABARITO_OFICIAL = {
    'q1': 'e',
    'q2': 'd',
    'q3': 'b',
    'q4': 'd',
    'q5': 'e',
    'q6': 'c',
    'q7': 'b',
    'q8': 'c',
    'q9': 'b',
    'q10': 'b'
}
NUM_QUESTOES = len(GABARITO_OFICIAL)

# --- Funções do Banco de Dados SQLite ---

def get_db_connection():
    """Cria e retorna a conexão com o banco de dados."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Permite acessar colunas por nome
    return conn

def init_db():
    """Inicializa o banco de dados e cria a tabela 'resultados'."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resultados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_aluno TEXT NOT NULL,
            acertos INTEGER NOT NULL,
            total_questoes INTEGER NOT NULL,
            percentual REAL NOT NULL,
            data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# --- Rotas do Aplicativo ---

@app.route('/', methods=['GET', 'POST'])
def index():
    """Página inicial que pede o nome do aluno e permite o download."""
    
    # Se o método for POST, o aluno está enviando o nome para ir ao gabarito.
    if request.method == 'POST':
        nome_aluno = request.form.get('nome_aluno')
        if nome_aluno:
            # Redireciona para o gabarito, passando o nome na URL
            return redirect(url_for('gabarito_form', nome=nome_aluno))
        
    # Método GET (primeiro acesso)
    return render_template('index.html', prova_filename='prova.pdf')

@app.route('/download/<filename>')
def download_prova(filename):
    """Rota para servir o arquivo da prova para download."""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        return "Arquivo da prova não encontrado! Verifique se 'prova.pdf' está na pasta 'static'.", 404

@app.route('/gabarito')
def gabarito_form():
    """Exibe o formulário para o aluno preencher o gabarito."""
    
    # ⚠️ REQUER O NOME para prosseguir.
    nome_aluno = request.args.get('nome')
    if not nome_aluno:
        return redirect(url_for('index')) # Se não tiver nome, volta para o início.
        
    return render_template('gabarito.html', 
                           num_questoes=NUM_QUESTOES, 
                           nome_aluno=nome_aluno)

@app.route('/submit', methods=['POST'])
def submit_gabarito():
    """Processa o gabarito, calcula a nota e SALVA no banco de dados."""
    
    # Captura o nome, que está em um campo HIDDEN
    nome_aluno = request.form.get('nome_aluno', 'Aluno Não Identificado') 
    
    respostas_aluno = {}
    acertos = 0
    total = NUM_QUESTOES
    
    # 1. Coleta e Verifica as Respostas
    for i in range(1, total + 1):
        questao_key = f'q{i}'
        resposta_aluno = request.form.get(questao_key, 'N/A').lower() 
        respostas_aluno[questao_key] = resposta_aluno
        
        if resposta_aluno == GABARITO_OFICIAL.get(questao_key):
            acertos += 1

    percentual = (acertos / total) * 100 if total > 0 else 0
    
    # 2. Grava o Resultado no SQLite
    try:
        conn = get_db_connection()
        conn.execute('INSERT INTO resultados (nome_aluno, acertos, total_questoes, percentual) VALUES (?, ?, ?, ?)',
                     (nome_aluno, acertos, total, percentual))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Erro ao salvar no banco de dados: {e}")
        
    # 3. Renderiza a Página de Resultado
    return render_template('resultado.html', 
                           nome_aluno=nome_aluno,
                           acertos=acertos, 
                           total=total,
                           percentual=f'{percentual:.2f}%',
                           respostas_aluno=respostas_aluno,
                           gabarito_oficial=GABARITO_OFICIAL)

@app.route('/admin/notas')
def admin_notas():
    """Rota de administração para ver todas as notas salvas."""
    try:
        conn = get_db_connection()
        # Ordena por data mais recente
        resultados = conn.execute('SELECT nome_aluno, acertos, total_questoes, percentual, data_envio FROM resultados ORDER BY data_envio DESC').fetchall()
        conn.close()
        return render_template('admin_notas.html', resultados=resultados)
    except Exception as e:
        return f"Erro ao carregar notas: {e}", 500


if __name__ == '__main__':
    # Inicializa o banco de dados antes de rodar o app
    init_db()
    if not os.path.exists('static'):
        os.makedirs('static')
    app.run(debug=True)