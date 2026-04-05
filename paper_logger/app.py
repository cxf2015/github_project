from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import json
import uuid

app = Flask(__name__)
# 配置数据库
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'papers.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 限制上传文件大小为 50MB

# 翻译 API 配置
# 百度翻译 API 注册地址：https://fanyi-api.baidu.com/
app.config['TRANSLATION_APP_ID'] = ''  # 填入你的百度翻译 APP ID
app.config['TRANSLATION_SECRET_KEY'] = ''  # 填入你的百度翻译密钥

# 有道翻译 API 注册地址：https://ai.youdao.com/
app.config['YOUDAO_APP_ID'] = ''  # 填入你的有道翻译 APP ID
app.config['YOUDAO_SECRET_KEY'] = ''  # 填入你的有道翻译密钥

# Google 翻译 (无需 API key，直接调用)
# 注意：国内可能需要代理才能访问

# DeepL 翻译 API 注册地址：https://www.deepl.com/pro-api
app.config['DEEPL_API_KEY'] = ''  # 填入你的 DeepL API 密钥 (付费)

# 创建上传文件夹
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# 论文模型
class Paper(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    file_path = db.Column(db.String(1000))  # 本地文件路径或 URL
    file_type = db.Column(db.String(10))  # 'local' 或 'url'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = db.relationship('Note', backref='paper', lazy=True, cascade='all, delete-orphan')

# 笔记模型
class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('paper.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    page_number = db.Column(db.Integer, default=1)  # 对应的页码
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# 创建数据库表
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/papers', methods=['GET'])
def get_papers():
    """获取所有论文列表"""
    papers = Paper.query.order_by(Paper.updated_at.desc()).all()
    result = []
    for paper in papers:
        result.append({
            'id': paper.id,
            'title': paper.title,
            'file_type': paper.file_type,
            'created_at': paper.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'notes_count': len(paper.notes)
        })
    return jsonify(result)

@app.route('/api/papers/<int:paper_id>', methods=['GET'])
def get_paper(paper_id):
    """获取单篇论文详情和笔记"""
    paper = Paper.query.get_or_404(paper_id)
    notes = []
    for note in paper.notes:
        notes.append({
            'id': note.id,
            'content': note.content,
            'page_number': note.page_number,
            'created_at': note.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    return jsonify({
        'id': paper.id,
        'title': paper.title,
        'file_path': paper.file_path,
        'file_type': paper.file_type,
        'notes': notes
    })

@app.route('/api/papers', methods=['POST'])
def create_paper():
    """创建新论文记录"""
    data = request.json
    title = data.get('title')
    file_path = data.get('file_path')
    file_type = data.get('file_type', 'local')
    
    if not title or not file_path:
        return jsonify({'error': '标题和文件路径不能为空'}), 400
    
    paper = Paper(title=title, file_path=file_path, file_type=file_type)
    db.session.add(paper)
    db.session.commit()
    
    return jsonify({'id': paper.id, 'message': '论文记录创建成功'}), 201

@app.route('/api/papers/<int:paper_id>', methods=['PUT'])
def update_paper(paper_id):
    """更新论文信息"""
    paper = Paper.query.get_or_404(paper_id)
    data = request.json
    
    if 'title' in data:
        paper.title = data['title']
    if 'file_path' in data:
        paper.file_path = data['file_path']
    
    paper.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'message': '论文信息更新成功'})

@app.route('/api/papers/<int:paper_id>', methods=['DELETE'])
def delete_paper(paper_id):
    """删除论文记录"""
    paper = Paper.query.get_or_404(paper_id)
    db.session.delete(paper)
    db.session.commit()
    
    return jsonify({'message': '论文记录已删除'})

@app.route('/api/papers/<int:paper_id>/notes', methods=['POST'])
def add_note(paper_id):
    """添加笔记"""
    paper = Paper.query.get_or_404(paper_id)
    data = request.json
    content = data.get('content')
    page_number = data.get('page_number', 1)
    
    if not content:
        return jsonify({'error': '笔记内容不能为空'}), 400
    
    note = Note(paper_id=paper_id, content=content, page_number=page_number)
    db.session.add(note)
    db.session.commit()
    
    return jsonify({'id': note.id, 'message': '笔记添加成功'}), 201

@app.route('/api/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    """更新笔记"""
    note = Note.query.get_or_404(note_id)
    data = request.json
    
    if 'content' in data:
        note.content = data['content']
    if 'page_number' in data:
        note.page_number = data['page_number']
    
    note.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'message': '笔记更新成功'})

@app.route('/api/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    """删除笔记"""
    note = Note.query.get_or_404(note_id)
    db.session.delete(note)
    db.session.commit()
    
    return jsonify({'message': '笔记已删除'})

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传 PDF 文件"""
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '文件名为空'}), 400
    
    if file and file.filename.endswith('.pdf'):
        # 生成唯一文件名
        original_filename = file.filename
        unique_filename = f"{uuid.uuid4().hex}_{original_filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        return jsonify({
            'filename': unique_filename,
            'original_filename': original_filename,
            'message': '上传成功'
        }), 200
    else:
        return jsonify({'error': '只支持 PDF 文件'}), 400

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """提供上传文件的访问"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/translate', methods=['POST'])
def translate():
    """翻译文本 - 支持多个翻译引擎"""
    import hashlib
    import requests
    
    data = request.json
    text = data.get('text', '')
    engine = data.get('engine', 'baidu')  # 默认使用百度翻译
    
    if not text:
        return jsonify({'error': '翻译文本不能为空'}), 400
    
    try:
        if engine == 'baidu':
            return translate_baidu(text)
        elif engine == 'youdao':
            return translate_youdao(text)
        elif engine == 'google':
            return translate_google(text)
        elif engine == 'deepl':
            return translate_deepl(text)
        else:
            return jsonify({
                'error': '不支持的翻译引擎',
                'message': f'当前支持的引擎：baidu, youdao, google, deepl'
            }), 400
            
    except Exception as e:
        return jsonify({
            'error': '翻译失败',
            'message': str(e)
        }), 500

def translate_baidu(text):
    """百度翻译"""
    app_id = app.config['TRANSLATION_APP_ID']
    secret_key = app.config['TRANSLATION_SECRET_KEY']
    
    if not app_id or not secret_key:
        return jsonify({
            'error': '百度翻译 API 未配置',
            'message': '请在 app.py 中配置 TRANSLATION_APP_ID 和 TRANSLATION_SECRET_KEY',
            'guide': '注册地址：https://fanyi-api.baidu.com/'
        }), 400
    
    try:
        # 生成签名
        salt = str(uuid.uuid4())
        sign_str = app_id + text + salt + secret_key
        sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()
        
        # 调用百度翻译 API
        url = 'https://fanyi-api.baidu.com/api/trans/vip/translate'
        params = {
            'q': text,
            'from': 'en',
            'to': 'zh',
            'appid': app_id,
            'salt': salt,
            'sign': sign
        }
        
        response = requests.post(url, params=params, timeout=10)
        result = response.json()
        
        if 'error_code' in result:
            return jsonify({
                'error': '翻译失败',
                'message': result.get('error_msg', '未知错误')
            }), 400
        
        translated_text = result['trans_result'][0]['dst']
        return jsonify({
            'original': text,
            'translated': translated_text,
            'engine_name': '百度翻译'
        }), 200
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': '网络请求失败',
            'message': str(e)
        }), 500

def translate_youdao(text):
    """有道翻译"""
    app_id = app.config['YOUDAO_APP_ID']
    secret_key = app.config['YOUDAO_SECRET_KEY']
    
    if not app_id or not secret_key:
        return jsonify({
            'error': '有道翻译 API 未配置',
            'message': '请在 app.py 中配置 YOUDAO_APP_ID 和 YOUDAO_SECRET_KEY',
            'guide': '注册地址：https://ai.youdao.com/'
        }), 400
    
    try:
        import time
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad
        import base64
        
        # 有道翻译需要更复杂的加密，这里简化处理
        # 实际使用时需要按照有道文档实现完整签名
        salt = str(uuid.uuid4())
        curtime = str(int(time.time()))
        
        # 简化版本（实际应该使用 AES 加密）
        sign = hashlib.sha256((app_id + text + salt + curtime + secret_key).encode()).hexdigest()
        
        url = 'https://openapi.youdao.com/api'
        params = {
            'q': text,
            'from': 'EN',
            'to': 'zh-CHS',
            'appKey': app_id,
            'salt': salt,
            'sign': sign,
            'signType': 'v3',
            'curtime': curtime
        }
        
        response = requests.get(url, params=params, timeout=10)
        result = response.json()
        
        if result.get('errorCode') != '0':
            return jsonify({
                'error': '翻译失败',
                'message': f'有道 API 错误：{result.get("errorCode", "未知")}'
            }), 400
        
        # 有道返回格式与百度不同
        translated_text = ' '.join(result.get('translation', []))
        return jsonify({
            'original': text,
            'translated': translated_text,
            'engine_name': '有道翻译'
        }), 200
        
    except ImportError:
        return jsonify({
            'error': '缺少依赖库',
            'message': '请安装 pycryptodome: pip install pycryptodome'
        }), 500
    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': '网络请求失败',
            'message': str(e)
        }), 500

def translate_google(text):
    """Google 翻译 (无需 API key)"""
    try:
        # 使用 Google 翻译的公开接口（非官方 API）
        # 注意：有频率限制，适合低频使用
        url = 'https://translate.googleapis.com/translate_a/single'
        params = {
            'client': 'gtx',
            'sl': 'en',
            'tl': 'zh-CN',
            'dt': 't',
            'q': text
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        result = response.json()
        
        # 解析 Google 翻译结果
        translated_text = ''.join([sentence[0] for sentence in result[0] if sentence[0]])
        
        return jsonify({
            'original': text,
            'translated': translated_text,
            'engine_name': 'Google 翻译 (免费)'
        }), 200
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': '网络请求失败',
            'message': '无法访问 Google 服务，可能需要代理。错误：' + str(e)
        }), 500

def translate_deepl(text):
    """DeepL 翻译 (付费，质量最高)"""
    api_key = app.config['DEEPL_API_KEY']
    
    if not api_key:
        return jsonify({
            'error': 'DeepL API 未配置',
            'message': '请在 app.py 中配置 DEEPL_API_KEY',
            'guide': '注册地址：https://www.deepl.com/pro-api (付费服务)'
        }), 400
    
    try:
        url = 'https://api-free.deepl.com/v2/translate'
        headers = {
            'Authorization': f'DeepL-Auth-Key {api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            'text': [text],
            'target_lang': 'ZH'
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=10)
        result = response.json()
        
        if response.status_code != 200:
            return jsonify({
                'error': '翻译失败',
                'message': f'DeepL API 错误：{result.get("message", "未知错误")}'
            }), 400
        
        translated_text = result['translations'][0]['text']
        return jsonify({
            'original': text,
            'translated': translated_text,
            'engine_name': 'DeepL 翻译 (专业级)'
        }), 200
        
    except requests.exceptions.RequestException as e:
        return jsonify({
            'error': '网络请求失败',
            'message': str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
