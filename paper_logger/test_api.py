"""
Paper Logger 测试脚本
用于快速测试 API 功能
"""

import requests
import json

BASE_URL = 'http://localhost:5000'

def test_api():
    print("=" * 60)
    print("Paper Logger API 测试")
    print("=" * 60)
    
    # 1. 测试获取论文列表 (应该是空的)
    print("\n1. 获取论文列表...")
    response = requests.get(f'{BASE_URL}/api/papers')
    if response.status_code == 200:
        papers = response.json()
        print(f"✓ 成功获取论文列表，当前数量：{len(papers)}")
    else:
        print(f"✗ 失败：{response.status_code}")
        return
    
    # 2. 创建测试论文记录
    print("\n2. 创建测试论文记录...")
    test_paper = {
        'title': '测试论文：Attention Is All You Need',
        'file_path': 'https://arxiv.org/pdf/1706.03762.pdf',
        'file_type': 'url'
    }
    response = requests.post(f'{BASE_URL}/api/papers', json=test_paper)
    if response.status_code == 201:
        result = response.json()
        paper_id = result['id']
        print(f"✓ 成功创建论文记录，ID: {paper_id}")
    else:
        print(f"✗ 失败：{response.status_code}")
        return
    
    # 3. 获取论文详情
    print(f"\n3. 获取论文详情 (ID: {paper_id})...")
    response = requests.get(f'{BASE_URL}/api/papers/{paper_id}')
    if response.status_code == 200:
        paper = response.json()
        print(f"✓ 成功获取论文详情:")
        print(f"  标题：{paper['title']}")
        print(f"  类型：{paper['file_type']}")
        print(f"  URL: {paper['file_path']}")
    else:
        print(f"✗ 失败：{response.status_code}")
        return
    
    # 4. 添加笔记
    print(f"\n4. 为论文添加笔记...")
    test_note = {
        'content': '这是一篇 Transformer 的开创性论文，提出了自注意力机制。',
        'page_number': 1
    }
    response = requests.post(f'{BASE_URL}/api/papers/{paper_id}/notes', json=test_note)
    if response.status_code == 201:
        note_result = response.json()
        note_id = note_result['id']
        print(f"✓ 成功添加笔记，ID: {note_id}")
    else:
        print(f"✗ 失败：{response.status_code}")
        return
    
    # 5. 再次添加一条笔记
    print(f"\n5. 添加第二条笔记...")
    test_note2 = {
        'content': '实验结果表明 Transformer 在翻译任务上超越了 RNN 和 LSTM。',
        'page_number': 10
    }
    response = requests.post(f'{BASE_URL}/api/papers/{paper_id}/notes', json=test_note2)
    if response.status_code == 201:
        print(f"✓ 成功添加第二条笔记")
    else:
        print(f"✗ 失败：{response.status_code}")
    
    # 6. 重新获取论文详情 (应该包含笔记)
    print(f"\n6. 重新获取论文详情 (应包含 2 条笔记)...")
    response = requests.get(f'{BASE_URL}/api/papers/{paper_id}')
    if response.status_code == 200:
        paper = response.json()
        print(f"✓ 成功获取论文详情:")
        print(f"  笔记数量：{len(paper['notes'])}")
        for i, note in enumerate(paper['notes'], 1):
            print(f"\n  笔记 {i}:")
            print(f"    页码：{note['page_number']}")
            print(f"    内容：{note['content'][:50]}...")
    else:
        print(f"✗ 失败：{response.status_code}")
    
    # 7. 更新笔记
    print(f"\n7. 更新第一条笔记...")
    update_data = {
        'content': '[已更新] 这是一篇 Transformer的开创性论文，提出了自注意力机制。非常重要！'
    }
    response = requests.put(f'{BASE_URL}/api/notes/{note_id}', json=update_data)
    if response.status_code == 200:
        print(f"✓ 成功更新笔记")
    else:
        print(f"✗ 失败：{response.status_code}")
    
    # 8. 获取所有论文列表
    print(f"\n8. 获取所有论文列表...")
    response = requests.get(f'{BASE_URL}/api/papers')
    if response.status_code == 200:
        papers = response.json()
        print(f"✓ 当前共有 {len(papers)} 篇论文:")
        for paper in papers:
            print(f"  - {paper['title']} ({paper['notes_count']} 条笔记)")
    else:
        print(f"✗ 失败：{response.status_code}")
    
    # 9. 删除测试数据
    print(f"\n9. 清理测试数据...")
    response = requests.delete(f'{BASE_URL}/api/papers/{paper_id}')
    if response.status_code == 200:
        print(f"✓ 成功删除测试论文记录")
    else:
        print(f"✗ 失败：{response.status_code}")
    
    print("\n" + "=" * 60)
    print("✓ 所有测试完成!")
    print("=" * 60)
    print("\n提示：请在浏览器中访问 http://localhost:5000 查看实际界面")

if __name__ == '__main__':
    try:
        test_api()
    except requests.exceptions.ConnectionError:
        print("\n✗ 错误：无法连接到服务器")
        print("请确保应用正在运行：python app.py")
    except Exception as e:
        print(f"\n✗ 发生错误：{e}")
