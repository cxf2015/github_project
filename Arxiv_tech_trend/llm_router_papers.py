import arxiv
import re
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Dict
import time
import os

def search_llm_router_papers(months_back: int = 6) -> List[Dict]:
    """
    专门检索 Model Routing（模型路由/模型选择）相关的论文
    即从多个模型中选择合适模型的研究
    
    Args:
        months_back: 检索几个月内的论文，默认 6 个月
    
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
    
    # 定义 Model Routing 相关的搜索关键词
    model_routing_keywords = [
        "Model Routing",
        "Model Selection",
        "Model Choice",
        "Model Switching",
        "Model Pool",
        "Adaptive Model Selection",
        "Dynamic Model Selection",
        "Instance-based Model Selection",
        "Input-dependent Model Selection",
        "Query-based Model Selection",
        "Task-based Model Selection",
        "Multi-Model Selection",
        "Model Ensemble Selection",
        "Per-Input Model Selection",
        "Contextual Model Selection",
        "Learned Model Selection",
        "Neural Model Selector",
        "Gating Network for Models",
        "Model Dispatcher",
        "Model Orchestrator",
        "Model Coordinator"
    ]
    
    # 排除 MoE (Mixture of Experts) 相关术语
    exclude_keywords = [
        "Mixture of Experts",
        "MoE",
        "Expert Routing",
        "Sparse MoE",
        "Switch Transformer",
        "GShard",
        "GLaM"
    ]
    
    # 构建搜索查询
    search_queries = []
    
    # 处理 Model Routing 关键词
    for keyword in model_routing_keywords:
        search_queries.append(f'all:"{keyword}"')
    
    # 添加一些组合查询
    combination_queries = [
        'all:"model selection" AND (all:"multiple models" OR all:"model pool" OR all:"candidate models")',
        'all:"routing" AND (all:"which model" OR all:"choose model" OR all:"select model")',
        'all:"adaptive" AND all:"model" AND (all:"selection" OR all:"choosing")'
    ]
    search_queries.extend(combination_queries)
    
    # 合并所有查询
    combined_query = " OR ".join(search_queries)
    
    # 添加时间限制
    date_filter = f" AND submittedDate:[{start_date.strftime('%Y%m%d')}000000 TO {end_date.strftime('%Y%m%d')}235959]"
    final_query = combined_query + date_filter
    
    print(f"LLM Router搜索查询: {final_query}")
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
                # 检查是否是真正的模型路由论文
                title_lower = paper.title.lower()
                abstract_lower = paper.summary.lower()
                
                # 确认包含模型选择/路由相关术语
                model_selection_terms = ["model selection", "model routing", "model choice", 
                                     "model switching", "model pool", "multiple models"]
                has_model_selection = any(term in title_lower or term in abstract_lower 
                                      for term in model_selection_terms)
                
                # 或者包含"选择哪个模型"的语义
                selection_phrases = ["which model", "choose model", "select model", 
                               "picking model", "decide model"]
                has_selection_semantic = any(phrase in title_lower or phrase in abstract_lower 
                                        for phrase in selection_phrases)
                
                # 排除 MoE 相关论文
                moe_keywords = ["mixture of experts", "moe", "expert routing", 
                           "sparse mixture", "switch transformer", "gshard", "glam"]
                should_exclude = any(keyword in title_lower or keyword in abstract_lower 
                                for keyword in moe_keywords)
                
                # 确保不是单纯的模型融合或集成学习
                pure_ensemble_terms = ["ensemble learning", "model averaging", "weighted average"]
                is_pure_ensemble = any(term in title_lower and term not in title_lower 
                                  for term in pure_ensemble_terms)
                
                if (has_model_selection or has_selection_semantic) and not should_exclude and not is_pure_ensemble:
                    paper_info = {
                        'title': paper.title,
                        'authors': [str(author) for author in paper.authors],
                        'published': paper_published,
                        'abstract': paper.summary,
                        'url': paper.entry_id,
                        'categories': paper.categories,
                        'score': calculate_relevance_score(title_lower, abstract_lower)
                    }
                    papers.append(paper_info)
                
    except Exception as e:
        print(f"搜索过程中出现错误：{e}")
        import traceback
        traceback.print_exc()
    
    # 按相关性得分排序
    papers.sort(key=lambda x: x['score'], reverse=True)
    
    return papers

def calculate_relevance_score(title: str, abstract: str) -> float:
    """
    计算论文与 Model Routing（模型选择）主题的相关性得分
    
    Args:
        title: 论文标题（小写）
        abstract: 论文摘要（小写）
    
    Returns:
        相关性得分
    """
    score = 0.0
    
    # 核心关键词权重 - 模型选择相关
    core_keywords = {
        "model routing": 10,
        "model selection": 10,
        "model choice": 8,
        "model switching": 8,
        "model pool": 7,
        "multiple models": 6,
        "candidate models": 6,
        "select model": 5,
        "choose model": 5,
        "which model": 5
    }
    
    # 技术关键词权重 - 描述如何选择的机制
    tech_keywords = {
        "adaptive": 3,
        "dynamic": 3,
        "instance-based": 4,
        "input-dependent": 4,
        "query-based": 3,
        "task-based": 3,
        "contextual": 3,
        "learned": 3,
        "neural selector": 4,
        "gating network": 4,
        "dispatcher": 3,
        "orchestrator": 3
    }
    
    # 应用场景关键词
    application_keywords = {
        "pre-trained models": 2,
        "foundation models": 2,
        "language models": 2,
        "different models": 2,
        "heterogeneous models": 3,
        "model family": 2
    }
    
    # 计算核心关键词得分
    for keyword, weight in core_keywords.items():
        if keyword in title:
            score += weight * 2.5  # 标题中的关键词权重更高
        elif keyword in abstract:
            score += weight
    
    # 计算技术关键词得分
    for keyword, weight in tech_keywords.items():
        if keyword in title:
            score += weight * 2
        elif keyword in abstract:
            score += weight
    
    # 计算应用场景关键词得分
    for keyword, weight in application_keywords.items():
        if keyword in title or keyword in abstract:
            score += weight
    
    return score

def generate_llm_router_summary(abstract: str) -> str:
    """
    为 Model Routing（模型选择）论文生成专业的中文介绍
    
    Args:
        abstract: 英文论文摘要
    
    Returns:
        中文简介
    """
    # 关键词映射字典 - 聚焦于模型选择
    keyword_mapping = {
        # 核心概念
        'model routing': '模型路由',
        'model selection': '模型选择',
        'model choice': '模型选择',
        'model switching': '模型切换',
        'model pool': '模型池',
        'multiple models': '多个模型',
        'candidate models': '候选模型',
        
        # 技术特性
        'adaptive': '自适应',
        'dynamic': '动态',
        'instance-based': '基于实例的',
        'input-dependent': '依赖于输入的',
        'query-based': '基于查询的',
        'task-based': '基于任务的',
        'contextual': '上下文化的',
        'learned': '可学习的',
        
        # 功能描述
        'select model': '选择模型',
        'choose model': '选择模型',
        'which model': '哪个模型',
        'model dispatcher': '模型调度器',
        'model orchestrator': '模型协调器',
        
        # 性能指标
        'efficiency': '效率',
        'performance': '性能',
        'accuracy': '准确率',
        'latency': '延迟',
        'throughput': '吞吐量',
        'scalability': '可扩展性',
        'cost-effectiveness': '成本效益'
    }
    
    # 清理和预处理摘要
    clean_abstract = re.sub(r'\s+', ' ', abstract.strip().lower())
    
    # 提取关键特征 - 关注模型选择相关特性
    features = {
        'has_adaptive': 'adaptive' in clean_abstract,
        'has_dynamic': 'dynamic' in clean_abstract,
        'has_instance_based': 'instance-based' in clean_abstract or 'per-instance' in clean_abstract,
        'has_input_dependent': 'input-dependent' in clean_abstract or 'input dependent' in clean_abstract,
        'has_multiple_models': 'multiple models' in clean_abstract or 'model pool' in clean_abstract,
        'has_learned': 'learned' in clean_abstract or 'learning' in clean_abstract,
        'has_efficiency': 'efficiency' in clean_abstract or 'efficient' in clean_abstract,
        'has_performance': 'performance' in clean_abstract,
        'has_cost_aware': 'cost' in clean_abstract and ('aware' in clean_abstract or 'effective' in clean_abstract),
        'has_scalability': 'scalability' in clean_abstract or 'scalable' in clean_abstract
    }
    
    # 生成中文关键词
    chinese_words = []
    for eng_word, chi_word in keyword_mapping.items():
        if eng_word.lower() in clean_abstract and len(chinese_words) < 15:
            if chi_word not in chinese_words:
                chinese_words.append(chi_word)
    
    # 如果关键词太少，补充通用词汇
    if len(chinese_words) < 5:
        basic_words = ['大语言模型', '路由器', '路由', '方法', '系统', '技术']
        chinese_words.extend(basic_words[:min(6, 15 - len(chinese_words))])
    
    # 构造专业中文介绍 - 强调从多个模型中选择
    if features['has_adaptive'] and features['has_multiple_models']:
        intro = f"本文提出了一种{chinese_words[0]}方法，能够从{chinese_words[1]}中自适应地选择最适合的模型。"
    elif features['has_instance_based'] or features['has_input_dependent']:
        intro = f"该研究设计了一种{chinese_words[0]}机制，根据输入样本的特性动态{chinese_words[1]}最佳模型。"
    elif features['has_learned']:
        intro = f"作者开发了一个{chinese_words[0]}系统，通过学习如何从{chinese_words[1]}中进行选择。"
    elif features['has_dynamic']:
        intro = f"本文提出了一个动态{chinese_words[0]}框架，用于在{chinese_words[1]}场景中优化模型选择。"
    else:
        intro = f"该论文研究了如何从{chinese_words[0]}中{chinese_words[1]}的问题。"
    
    # 添加性能或贡献描述
    if features['has_efficiency'] and features['has_performance']:
        intro += "实验结果表明该方法在效率和预测性能方面均有显著提升。"
    elif features['has_efficiency']:
        intro += "在计算资源利用和推理速度方面表现出色。"
    elif features['has_cost_aware']:
        intro += "在保证性能的同时有效降低了计算成本。"
    elif 'accuracy' in clean_abstract:
        intro += "在任务准确率方面达到了先进水平。"
    elif features['has_scalability']:
        intro += "具有良好的可扩展性和实用性。"
    else:
        intro += "为模型选择领域提供了创新性的技术方案。"
    
    return intro

def display_llm_router_papers(papers: List[Dict]):
    """
    显示LLM Router论文信息
    
    Args:
        papers: 论文信息列表
    """
    if not papers:
        print("未找到相关LLM Router论文")
        return
    
    print(f"\n找到 {len(papers)} 篇LLM Router相关论文:")
    print("=" * 100)
    
    for i, paper in enumerate(papers, 1):
        print(f"\n{i}. {paper['title']}")
        print(f"   相关性得分: {paper['score']:.1f}")
        print(f"   发表日期: {paper['published'].strftime('%Y-%m-%d')}")
        print(f"   作者: {', '.join(paper['authors'][:3])}" + 
              (f" 等{len(paper['authors'])}人" if len(paper['authors']) > 3 else ""))
        print(f"   分类: {', '.join(paper['categories'])}")
        print(f"   链接: {paper['url']}")
        print(f"   英文摘要: {paper['abstract'][:300]}..." if len(paper['abstract']) > 300 else f"   英文摘要: {paper['abstract']}")
        print(f"   中文介绍: {generate_llm_router_summary(paper['abstract'])}")
        print("-" * 100)

def save_llm_router_to_csv(papers: List[Dict], filename: str = "llm_router_papers.csv"):
    """
    将LLM Router论文信息保存到CSV文件
    
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
            '相关性得分': paper['score'],
            '发表日期': paper['published'].strftime('%Y-%m-%d'),
            '作者': ', '.join(paper['authors']),
            '分类': ', '.join(paper['categories']),
            '链接': paper['url'],
            '英文摘要': paper['abstract'],
            '中文介绍': generate_llm_router_summary(paper['abstract'])
        }
        data.append(row)
    
    # 创建DataFrame并保存
    df = pd.DataFrame(data)
    try:
        current_dir = os.getcwd()
        full_path = os.path.join(current_dir, filename)
        print(f"文件将保存到: {full_path}")
        
        df.to_csv(full_path, index=False, encoding='utf-8-sig')
        print(f"LLM Router论文信息已保存到 {full_path}")
    except Exception as e:
        print(f"保存文件时出错: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数 - 检索 Model Routing（模型选择）相关论文"""
    print("开始检索 Arxiv 上的 Model Routing（模型路由/模型选择）相关论文...")
    print("Model Routing 指的是：从多个模型中选择合适模型的智能决策方法")
    print("=" * 60)
    
    try:
        # 检索论文
        papers = search_llm_router_papers(months_back=6)
        
        # 显示结果
        display_llm_router_papers(papers)
        
        # 保存到CSV文件
        save_llm_router_to_csv(papers)
        
        print(f"\n检索完成！共找到 {len(papers)} 篇LLM Router论文。")
        
    except Exception as e:
        print(f"程序执行出错：{e}")

if __name__ == "__main__":
    main()