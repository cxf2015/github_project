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

if __name__ == '__main__':
    app.run(debug=True, port=5000)
