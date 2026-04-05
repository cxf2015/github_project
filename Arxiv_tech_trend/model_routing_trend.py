import arxiv
import re
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Dict
import time
import os

def search_multimodal_router_papers(months_back: int = 3) -> List[Dict]:
    """
    从Arxiv检索多模态大模型Router相关的论文
    
    Args:
        months_back: 检索几个月内的论文，默认3个月
    
    Returns:
        包含论文信息的字典列表
    """
    
    # 计算搜索时间范围
    end_date = datetime.now()
    start_date = end_date - timedelta(days=months_back * 30)
    
    # 确保所有datetime对象都没有时区信息以便比较
    if end_date.tzinfo is not None:
        end_date = end_date.replace(tzinfo=None)
    if start_date.tzinfo is not None:
        start_date = start_date.replace(tzinfo=None)
    
    # 多模态相关的搜索关键词
    multimodal_keywords = [
        "multimodal router",
        "vision-language router",
        "multi-modal routing",
        "cross-modal router",
        "multimodal model selection",
        "vision language model routing",
        "vlm router",
        "multimodal foundation model router",
        "multimodal large language model router"
    ]
    
    # 多模态技术术语
    multimodal_terms = [
        "multimodal fusion",
        "cross-modal attention",
        "vision-language pretraining",
        "multimodal representation",
        "image-text alignment",
        "multimodal embedding"
    ]
    
    # 结合路由和多模态的复合关键词
    combined_keywords = [
        "router for multimodal",
        "multimodal model routing",
        "routing in multimodal",
        "multimodal task routing",
        "cross-modal model selection"
    ]
    
    # 构建搜索查询
    search_queries = []
    
    # 处理多模态路由关键词
    for keyword in multimodal_keywords:
        search_queries.append(f'all:"{keyword}"')
    
    # 处理多模态技术术语
    for term in multimodal_terms:
        search_queries.append(f'all:"{term}"')
    
    # 处理复合关键词
    for keyword in combined_keywords:
        search_queries.append(f'all:"{keyword}"')
    
    # 合并所有查询
    combined_query = " OR ".join(search_queries)
    
    # 添加时间限制
    date_filter = f" AND submittedDate:[{start_date.strftime('%Y%m%d')}000000 TO {end_date.strftime('%Y%m%d')}235959]"
    final_query = combined_query + date_filter
    
    print(f"多模态Router搜索查询: {final_query}")
    print(f"时间范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
    
    # 创建arxiv客户端
    client = arxiv.Client()
    
    # 执行搜索
    search = arxiv.Search(
        query=final_query,
        max_results=100,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )
    
    papers = []
    
    try:
        results = client.results(search)
        
        for paper in results:
            # 处理论文的发布时间，确保时区一致性
            paper_published = paper.published
            if paper_published.tzinfo is not None:
                paper_published = paper_published.replace(tzinfo=None)
            
            # 过滤时间范围
            if start_date <= paper_published <= end_date:
                # 检查是否确实包含多模态相关内容
                title_lower = paper.title.lower()
                abstract_lower = paper.summary.lower()
                
                # 确认包含多模态相关关键词
                multimodal_indicators = [
                    "multimodal", "vision-language", "vlm", "cross-modal",
                    "image-text", "vision language", "multi-modal"
                ]
                
                has_multimodal_content = any(indicator in title_lower or indicator in abstract_lower 
                                           for indicator in multimodal_indicators)
                
                # 确认包含路由相关关键词
                router_indicators = [
                    "router", "routing", "model selection", "dispatch", "route"
                ]
                
                has_router_content = any(indicator in title_lower or indicator in abstract_lower 
                                       for indicator in router_indicators)
                
                # 只保留同时包含多模态和路由内容的论文
                if has_multimodal_content and has_router_content:
                    paper_info = {
                        'title': paper.title,
                        'authors': [str(author) for author in paper.authors],
                        'published': paper_published,
                        'abstract': paper.summary,
                        'url': paper.entry_id,
                        'categories': paper.categories
                    }
                    papers.append(paper_info)
                
    except Exception as e:
        print(f"搜索过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    return papers

def generate_multimodal_chinese_summary(abstract: str) -> str:
    """
    为多模态大模型Router论文生成中文介绍
    
    Args:
        abstract: 英文论文摘要
    
    Returns:
        中文简介
    """
    # 多模态路由专用关键词映射
    keyword_mapping = {
        # 多模态路由核心概念
        'multimodal router': '多模态路由器',
        'vision-language router': '视觉-语言路由器',
        'vlm router': '视觉语言模型路由器',
        'cross-modal router': '跨模态路由器',
        'multimodal model selection': '多模态模型选择',
        'multimodal routing': '多模态路由',
        
        # 多模态技术
        'multimodal fusion': '多模态融合',
        'cross-modal attention': '跨模态注意力',
        'vision-language pretraining': '视觉-语言预训练',
        'multimodal representation': '多模态表示',
        'image-text alignment': '图文对齐',
        'multimodal embedding': '多模态嵌入',
        
        # 基础概念
        'large language models': '大语言模型',
        'foundation models': '基础模型',
        'vision language models': '视觉语言模型',
        'vlms': '视觉语言模型',
        'multimodal models': '多模态模型',
        
        # 技术方法
        'attention mechanism': '注意力机制',
        'transformer': '变换器',
        'neural networks': '神经网络',
        'deep learning': '深度学习',
        'machine learning': '机器学习',
        
        # 应用场景
        'computer vision': '计算机视觉',
        'natural language processing': '自然语言处理',
        'image captioning': '图像描述',
        'visual question answering': '视觉问答',
        'image-text retrieval': '图文检索',
        
        # 性能指标
        'accuracy': '准确率',
        'efficiency': '效率',
        'performance': '性能',
        'scalability': '可扩展性',
        'latency': '延迟',
        
        # 动词
        'propose': '提出',
        'present': '提出',
        'introduce': '介绍',
        'develop': '开发',
        'design': '设计',
        'implement': '实现',
        'evaluate': '评估',
        'analyze': '分析'
    }
    
    # 清理和预处理摘要
    clean_abstract = re.sub(r'\s+', ' ', abstract.strip().lower())
    
    # 提取关键特征
    features = {
        'has_vlm_router': 'vlm router' in clean_abstract or ('vision language' in clean_abstract and 'router' in clean_abstract),
        'has_multimodal_router': 'multimodal router' in clean_abstract,
        'has_cross_modal': 'cross-modal' in clean_abstract or 'cross modal' in clean_abstract,
        'has_fusion': 'fusion' in clean_abstract,
        'has_attention': 'attention' in clean_abstract,
        'has_vision_language': 'vision language' in clean_abstract or 'vlm' in clean_abstract,
        'has_image_text': 'image-text' in clean_abstract or 'image text' in clean_abstract
    }
    
    # 生成中文关键词
    chinese_words = []
    word_count = 0
    max_words = 20
    
    # 优先处理多模态路由相关关键词
    priority_keywords = [
        'multimodal router', 'vision-language router', 'vlm router',
        'cross-modal router', 'multimodal model selection'
    ]
    
    for eng_word in priority_keywords:
        if eng_word.lower() in clean_abstract and word_count < max_words:
            chi_word = keyword_mapping.get(eng_word.lower(), eng_word)
            if chi_word not in chinese_words:
                chinese_words.append(chi_word)
                word_count += 1
    
    # 处理其他重要关键词
    other_keywords = [
        'multimodal fusion', 'vision-language pretraining', 'large language models',
        'attention mechanism', 'computer vision', 'natural language processing'
    ]
    
    for eng_word in other_keywords:
        if eng_word.lower() in clean_abstract and word_count < max_words:
            chi_word = keyword_mapping.get(eng_word.lower(), eng_word)
            if chi_word not in chinese_words:
                chinese_words.append(chi_word)
                word_count += 1
    
    # 补充基础词汇
    if len(chinese_words) < 2:
        basic_words = ['多模态', '路由', '模型', '框架']
        chinese_words.extend(basic_words[:min(4, max_words - len(chinese_words))])
    
    # 构造中文介绍
    if features['has_vlm_router']:
        intro = f"本文提出了针对{chinese_words[0]}的创新路由机制。"
    elif features['has_multimodal_router']:
        intro = f"该研究设计了{chinese_words[0]}框架，用于处理多模态任务。"
    elif features['has_cross_modal'] and features['has_attention']:
        intro = f"作者开发了基于{chinese_words[0]}的跨模态路由方法。"
    else:
        intro = f"该论文研究了{chinese_words[0]}在多模态场景中的应用。"
    
    # 添加技术特点描述
    if features['has_fusion']:
        intro += f"采用了先进的{chinese_words[1]}技术。"
    elif features['has_attention']:
        intro += f"利用{chinese_words[1]}机制提升路由效果。"
    elif features['has_vision_language']:
        intro += f"专注于{chinese_words[1]}领域的路由优化。"
    else:
        intro += "在多模态模型路由方面做出了重要贡献。"
    
    # 添加应用场景
    if 'image captioning' in clean_abstract or 'caption' in clean_abstract:
        intro += "特别适用于图像描述生成任务。"
    elif 'visual question answering' in clean_abstract or 'vqa' in clean_abstract:
        intro += "在视觉问答任务中表现出色。"
    elif 'retrieval' in clean_abstract:
        intro += "有效支持图文检索应用。"
    else:
        intro += "具有广泛的应用前景。"
    
    return intro

def display_multimodal_papers(papers: List[Dict]):
    """
    显示多模态Router论文信息
    
    Args:
        papers: 论文信息列表
    """
    if not papers:
        print("未找到多模态Router相关论文")
        return
    
    print(f"\n找到 {len(papers)} 篇多模态Router相关论文:")
    print("=" * 80)
    
    # 按发表日期排序（最新的在前）
    sorted_papers = sorted(papers, key=lambda x: x['published'], reverse=True)
    
    for i, paper in enumerate(sorted_papers, 1):
        print(f"\n{i}. {paper['title']}")
        print(f"   发表日期: {paper['published'].strftime('%Y-%m-%d')}")
        print(f"   作者: {', '.join(paper['authors'][:3])}" + 
              (f" 等{len(paper['authors'])}人" if len(paper['authors']) > 3 else ""))
        print(f"   分类: {', '.join(paper['categories'])}")
        print(f"   链接: {paper['url']}")
        print(f"   英文摘要: {generate_brief_summary(paper['abstract'])}")
        print(f"   中文介绍: {generate_multimodal_chinese_summary(paper['abstract'])}")
        print("-" * 80)

def save_multimodal_to_csv(papers: List[Dict], filename: str = "multimodal_router_papers.csv"):
    """
    将多模态Router论文信息保存到CSV文件
    
    Args:
        papers: 论文信息列表
        filename: 输出文件名
    """
    if not papers:
        print("没有论文可保存")
        return
    
    # 准备数据
    data = []
    for paper in papers:
        row = {
            '标题': paper['title'],
            '发表日期': paper['published'].strftime('%Y-%m-%d'),
            '作者': ', '.join(paper['authors']),
            '分类': ', '.join(paper['categories']),
            '链接': paper['url'],
            '英文摘要': paper['abstract'],
            '中文介绍': generate_multimodal_chinese_summary(paper['abstract'])
        }
        data.append(row)
    
    # 创建DataFrame并保存
    df = pd.DataFrame(data)
    try:
        current_dir = os.getcwd()
        full_path = os.path.join(current_dir, filename)
        print(f"文件将保存到: {full_path}")
        
        df.to_csv(full_path, index=False, encoding='utf-8-sig')
        print(f"多模态Router论文信息已保存到 {full_path}")
    except Exception as e:
        print(f"保存文件时出错: {e}")
        import traceback
        traceback.print_exc()

def generate_brief_summary(abstract: str, max_length: int = 200) -> str:
    """
    为论文摘要生成简短介绍
    
    Args:
        abstract: 论文摘要
        max_length: 最大长度
    
    Returns:
        简短介绍
    """
    # 清理摘要文本
    clean_abstract = re.sub(r'\s+', ' ', abstract.strip())
    
    # 如果摘要太长，截取前部分并添加省略号
    if len(clean_abstract) > max_length:
        # 找到合适的截断点
        truncated = clean_abstract[:max_length]
        last_space = truncated.rfind(' ')
        if last_space > 0:
            brief = truncated[:last_space] + "..."
        else:
            brief = truncated + "..."
    else:
        brief = clean_abstract
    
    return brief

def generate_chinese_summary(abstract: str) -> str:
    """
    为论文摘要生成中文介绍，专门针对模型路由和选择论文
    
    Args:
        abstract: 英文论文摘要
    
    Returns:
        中文简介
    """
    # 关键词映射字典 - 包含具体路由框架
    keyword_mapping = {
        # 具体路由框架
        'graphrouter': '图路由器',
        'llmrouter': '大语言模型路由器',
        'routerdc': '数据中心路由器',
        'model router': '模型路由器',
        'neural router': '神经路由器',
        'learnable router': '可学习路由器',
        'adaptive router': '自适应路由器',
        'dynamic router': '动态路由器',
        'smart router': '智能路由器',
        'intelligent router': '智能路由器',
        
        # 核心概念
        'model selection': '模型选择',
        'model routing': '模型路由',
        'model ranking': '模型排序',
        'model evaluation': '模型评估',
        'model comparison': '模型比较',
        'best model': '最优模型',
        'optimal model': '最佳模型',
        'model recommendation': '模型推荐',
        
        # 技术方法
        'machine learning': '机器学习',
        'deep learning': '深度学习',
        'neural networks': '神经网络',
        'graph neural': '图神经网络',
        'reinforcement learning': '强化学习',
        'attention mechanism': '注意力机制',
        'transformer': '变换器',
        'ensemble': '集成',
        
        # 应用场景
        'large language models': '大语言模型',
        'llms': '大语言模型',
        'foundation models': '基础模型',
        'computer vision': '计算机视觉',
        'natural language': '自然语言',
        'multimodal': '多模态',
        'distributed': '分布式',
        'cloud': '云计算',
        
        # 性能指标
        'accuracy': '准确率',
        'efficiency': '效率',
        'latency': '延迟',
        'throughput': '吞吐量',
        'scalability': '可扩展性',
        'performance': '性能',
        
        # 动词
        'propose': '提出',
        'present': '提出',
        'introduce': '介绍',
        'develop': '开发',
        'design': '设计',
        'implement': '实现',
        'evaluate': '评估',
        'analyze': '分析',
        'optimize': '优化',
        'improve': '改进'
    }
    
    # 清理和预处理摘要
    clean_abstract = re.sub(r'\s+', ' ', abstract.strip().lower())
    
    # 提取关键信息特征
    features = {
        'has_graph_router': 'graphrouter' in clean_abstract or 'graph router' in clean_abstract,
        'has_llm_router': 'llmrouter' in clean_abstract or ('llm' in clean_abstract and 'router' in clean_abstract),
        'has_dc_router': 'routerdc' in clean_abstract or ('data center' in clean_abstract and 'router' in clean_abstract),
        'has_neural_router': 'neural router' in clean_abstract,
        'has_learnable': 'learnable' in clean_abstract or 'trainable' in clean_abstract,
        'has_adaptive': 'adaptive' in clean_abstract or 'dynamic' in clean_abstract,
        'has_llms': 'large language' in clean_abstract or 'llm' in clean_abstract or 'foundation model' in clean_abstract,
        'has_graph': 'graph' in clean_abstract,
        'has_performance': any(word in clean_abstract for word in ['performance', 'efficiency', 'accuracy', 'latency'])
    }
    
    # 生成中文关键词
    chinese_words = []
    word_count = 0
    max_words = 25  # 控制长度
    
    # 优先处理具体框架名称
    framework_keywords = ['graphrouter', 'llmrouter', 'routerdc', 'model router', 'neural router']
    for eng_word in framework_keywords:
        if eng_word.lower() in clean_abstract and word_count < max_words:
            chi_word = keyword_mapping.get(eng_word.lower(), eng_word)
            if chi_word not in chinese_words:
                chinese_words.append(chi_word)
                word_count += 1
    
    # 处理其他重要关键词
    priority_keywords = ['model selection', 'large language models', 'machine learning', 'performance', 'efficiency']
    for eng_word in priority_keywords:
        if eng_word.lower() in clean_abstract and word_count < max_words:
            chi_word = keyword_mapping.get(eng_word.lower(), eng_word)
            if chi_word not in chinese_words:
                chinese_words.append(chi_word)
                word_count += 1
    
    # 处理剩余关键词
    for eng_word, chi_word in keyword_mapping.items():
        if eng_word.lower() in clean_abstract and word_count < max_words:
            if chi_word not in chinese_words:
                chinese_words.append(chi_word)
                word_count += 1
    
    # 如果关键词太少，补充通用词汇
    if len(chinese_words) < 3:
        basic_words = ['模型', '路由', '框架', '方法']
        chinese_words.extend(basic_words[:min(4, max_words - len(chinese_words))])
    
    # 根据具体特征构造中文介绍
    if features['has_graph_router']:
        intro = f"本文提出了{chinese_words[0]}框架，用于解决图结构数据的模型路由问题。"
    elif features['has_llm_router']:
        intro = f"该研究设计了专门针对{chinese_words[0]}的智能路由机制。"
    elif features['has_dc_router']:
        intro = f"作者开发了适用于{chinese_words[0]}环境的高效路由解决方案。"
    elif features['has_neural_router'] and features['has_learnable']:
        intro = f"本文{chinese_words[0]}了一个基于{chinese_words[1]}的可学习路由系统。"
    elif features['has_adaptive'] and features['has_llms']:
        intro = f"该工作提出了面向{chinese_words[0]}的{chinese_words[1]}路由方法。"
    else:
        intro = f"该论文研究了{chinese_words[0]}相关的{chinese_words[1]}技术。"
    
    # 添加性能或贡献描述
    if features['has_performance']:
        intro += "实验验证了该方法在性能指标上的显著改善。"
    elif 'efficiency' in clean_abstract:
        intro += "在计算效率和资源利用方面表现优异。"
    elif 'scalability' in clean_abstract:
        intro += "具有良好的可扩展性和实用性。"
    else:
        intro += "为模型路由领域提供了创新性的技术方案。"
    
    return intro

def display_papers(papers: List[Dict]):
    """
    显示论文信息，包括中文介绍
    
    Args:
        papers: 论文信息列表
    """
    if not papers:
        print("未找到相关论文")
        return
    
    print(f"\n找到 {len(papers)} 篇相关论文:")
    print("=" * 80)
    
    # 按发表日期排序（最新的在前）
    sorted_papers = sorted(papers, key=lambda x: x['published'], reverse=True)
    
    for i, paper in enumerate(sorted_papers, 1):
        print(f"\n{i}. {paper['title']}")
        print(f"   发表日期: {paper['published'].strftime('%Y-%m-%d')}")
        print(f"   作者: {', '.join(paper['authors'][:3])}" + 
              (f" 等{len(paper['authors'])}人" if len(paper['authors']) > 3 else ""))
        print(f"   分类: {', '.join(paper['categories'])}")
        print(f"   链接: {paper['url']}")
        print(f"   英文摘要: {generate_brief_summary(paper['abstract'])}")
        print(f"   中文介绍: {generate_chinese_summary(paper['abstract'])}")
        print("-" * 80)

def save_to_csv(papers: List[Dict], filename: str = "model_routing_papers.csv"):
    """
    将论文信息保存到CSV文件，包含中文介绍
    
    Args:
        papers: 论文信息列表
        filename: 输出文件名
    """
    if not papers:
        print("没有论文可保存")
        return
    
    # 准备数据
    data = []
    for paper in papers:
        row = {
            '标题': paper['title'],
            '发表日期': paper['published'].strftime('%Y-%m-%d'),
            '作者': ', '.join(paper['authors']),
            '分类': ', '.join(paper['categories']),
            '链接': paper['url'],
            '英文摘要': paper['abstract'],
            '中文介绍': generate_chinese_summary(paper['abstract'])
        }
        data.append(row)
    
    # 创建DataFrame并保存
    df = pd.DataFrame(data)
    try:
        # 获取当前工作目录
        current_dir = os.getcwd()
        full_path = os.path.join(current_dir, filename)
        print(f"当前工作目录: {current_dir}")
        print(f"文件将保存到: {full_path}")
        
        df.to_csv(full_path, index=False, encoding='utf-8-sig')
        print(f"论文信息已保存到 {full_path}")
    except Exception as e:
        print(f"保存文件时出错: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    print("开始检索Arxiv上的多模态大模型Router相关论文...")
    print("=" * 50)
    
    try:
        # 检索多模态Router论文
        papers = search_multimodal_router_papers(months_back=3)
        
        # 显示结果
        display_multimodal_papers(papers)
        
        # 保存到CSV文件
        save_multimodal_to_csv(papers)
        
        print(f"\n检索完成！共找到 {len(papers)} 篇多模态Router相关论文。")
        
    except Exception as e:
        print(f"程序执行出错: {e}")

if __name__ == "__main__":
    main()