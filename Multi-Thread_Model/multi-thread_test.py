import torch
import torch.nn as nn
from transformers import BertModel, BertTokenizer
import asyncio
import threading
import time
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Union, Optional
import gc
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BertTextClassifier(nn.Module):
    """基于BERT的文本分类模型"""
    
    def __init__(self, num_classes: int = 2, model_name: str = 'bert-base-chinese'):
        super().__init__()
        self.model_name = model_name
        self.num_classes = num_classes
        
        # BERT编码器
        self.bert = BertModel.from_pretrained(model_name)
        self.hidden_size = self.bert.config.hidden_size
        
        # 分类头
        self.dropout = nn.Dropout(0.1)
        self.classifier = nn.Linear(self.hidden_size, num_classes)
        
        # 初始化tokenizer
        self.tokenizer = BertTokenizer.from_pretrained(model_name)
        
        # 设备管理
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.to(self.device)
        
        # 推理模式设置
        self.eval()
        self._lock = threading.Lock()
        
        logger.info(f"模型初始化完成，使用设备: {self.device}")
    
    def forward(self, input_ids, attention_mask, token_type_ids=None):
        """前向传播"""
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids
        )
        
        # 使用[CLS] token的输出进行分类
        pooled_output = outputs.last_hidden_state[:, 0, :]
        pooled_output = self.dropout(pooled_output)
        logits = self.classifier(pooled_output)
        return logits
    
    def predict(self, texts: Union[str, List[str]], max_length: int = 128) -> Dict:
        """同步推理接口"""
        if isinstance(texts, str):
            texts = [texts]
        
        # Tokenize
        inputs = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt"
        )
        
        # 移动到设备
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # 推理（加锁保证线程安全，如果需要严格顺序）
        with self._lock:
            with torch.no_grad():
                logits = self.forward(**inputs)
                probs = torch.softmax(logits, dim=-1)
                predictions = torch.argmax(probs, dim=-1)
        
        return {
            'logits': logits.cpu().numpy(),
            'probabilities': probs.cpu().numpy(),
            'predictions': predictions.cpu().numpy(),
            'labels': predictions.cpu().tolist()
        }
    
    async def predict_async(self, texts: Union[str, List[str]], max_length: int = 128) -> Dict:
        """异步推理接口 - 在线程池中执行同步推理"""
        loop = asyncio.get_event_loop()
        # 使用线程池执行同步推理，避免阻塞事件循环
        return await loop.run_in_executor(None, self.predict, texts, max_length)
    
    def batch_predict(self, texts: List[str], batch_size: int = 32, max_length: int = 128) -> List[Dict]:
        """批量推理，自动分批处理"""
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            result = self.predict(batch, max_length)
            # 将批量结果拆分为单个结果
            for j in range(len(batch)):
                results.append({
                    'text': batch[j],
                    'prediction': result['labels'][j],
                    'probability': result['probabilities'][j].tolist()
                })
        return results
    
    def release(self):
        """释放模型资源和GPU内存"""
        logger.info("开始释放模型资源...")
        
        # 删除模型组件
        del self.bert
        del self.classifier
        del self.dropout
        
        # 清空CUDA缓存
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        
        # 强制垃圾回收
        gc.collect()
        
        logger.info("模型资源已释放，GPU内存已清理")


class ModelManager:
    """模型管理器，支持单例模式和资源管理"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, num_classes: int = 2, model_name: str = 'bert-base-chinese'):
        if self._initialized:
            return
        
        self.model = BertTextClassifier(num_classes, model_name)
        self._initialized = True
        self._inference_count = 0
        self._count_lock = threading.Lock()
    
    def get_model(self) -> BertTextClassifier:
        return self.model
    
    def increment_count(self):
        with self._count_lock:
            self._inference_count += 1
    
    def get_inference_count(self) -> int:
        with self._count_lock:
            return self._inference_count
    
    def shutdown(self):
        if self.model:
            self.model.release()
            self.model = None
            ModelManager._instance = None
            self._initialized = False


# ==================== 多线程评测程序 ====================

class ThreadedBenchmark:
    """多线程模型推理评测器"""
    
    def __init__(self, num_classes: int = 2, max_workers: int = 4):
        self.manager = ModelManager(num_classes=num_classes)
        self.model = self.manager.get_model()
        self.max_workers = max_workers
        self.results_queue = queue.Queue()
        
    def single_inference_task(self, task_id: int, text: str) -> Dict:
        """单个推理任务"""
        thread_id = threading.current_thread().ident
        thread_name = threading.current_thread().name
        
        start_time = time.time()
        
        try:
            # 执行推理
            result = self.model.predict(text)
            inference_time = time.time() - start_time
            
            # 更新全局计数
            self.manager.increment_count()
            
            output = {
                'task_id': task_id,
                'thread_id': thread_id,
                'thread_name': thread_name,
                'text': text[:50] + '...' if len(text) > 50 else text,
                'prediction': result['labels'][0],
                'probabilities': [f"{p:.4f}" for p in result['probabilities'][0]],
                'inference_time_ms': round(inference_time * 1000, 2),
                'status': 'success',
                'gpu_memory_mb': self._get_gpu_memory()
            }
            
            logger.info(f"任务 {task_id} 完成，耗时: {output['inference_time_ms']}ms")
            return output
            
        except Exception as e:
            logger.error(f"任务 {task_id} 失败: {str(e)}")
            return {
                'task_id': task_id,
                'thread_name': thread_name,
                'status': 'failed',
                'error': str(e)
            }
    
    def _get_gpu_memory(self) -> Optional[float]:
        """获取当前GPU内存使用"""
        if torch.cuda.is_available():
            return round(torch.cuda.memory_allocated() / 1024**2, 2)
        return None
    
    def run_threaded_benchmark(self, texts: List[str], num_threads: int = 4) -> Dict:
        """运行多线程评测"""
        logger.info(f"\n{'='*60}")
        logger.info(f"开始多线程评测: {num_threads} 线程, {len(texts)} 条文本")
        logger.info(f"{'='*60}")
        
        start_time = time.time()
        results = []
        
        # 使用ThreadPoolExecutor进行多线程推理
        with ThreadPoolExecutor(max_workers=num_threads, thread_name_prefix='Inference') as executor:
            # 提交所有任务
            future_to_task = {
                executor.submit(self.single_inference_task, i, text): i 
                for i, text in enumerate(texts)
            }
            
            # 收集结果
            for future in as_completed(future_to_task):
                result = future.result()
                results.append(result)
                self.results_queue.put(result)
        
        total_time = time.time() - start_time
        
        # 统计分析
        successful = [r for r in results if r['status'] == 'success']
        failed = [r for r in results if r['status'] == 'failed']
        
        if successful:
            avg_time = sum(r['inference_time_ms'] for r in successful) / len(successful)
            min_time = min(r['inference_time_ms'] for r in successful)
            max_time = max(r['inference_time_ms'] for r in successful)
        else:
            avg_time = min_time = max_time = 0
        
        # 统计线程分布
        thread_counts = {}
        for r in successful:
            tid = r.get('thread_id', 'unknown')
            thread_counts[tid] = thread_counts.get(tid, 0) + 1
        
        report = {
            'total_tasks': len(texts),
            'successful': len(successful),
            'failed': len(failed),
            'total_time_sec': round(total_time, 2),
            'throughput_qps': round(len(texts) / total_time, 2),
            'avg_inference_time_ms': round(avg_time, 2),
            'min_inference_time_ms': round(min_time, 2),
            'max_inference_time_ms': round(max_time, 2),
            'thread_distribution': thread_counts,
            'total_inference_count': self.manager.get_inference_count(),
            'gpu_memory_final_mb': self._get_gpu_memory()
        }
        
        return report
    
    async def run_async_benchmark(self, texts: List[str], concurrency: int = 10) -> Dict:
        """运行异步并发评测"""
        logger.info(f"\n{'='*60}")
        logger.info(f"开始异步评测: 并发数 {concurrency}, {len(texts)} 条文本")
        logger.info(f"{'='*60}")
        
        semaphore = asyncio.Semaphore(concurrency)
        
        async def bounded_inference(task_id: int, text: str):
            async with semaphore:
                start = time.time()
                result = await self.model.predict_async(text)
                elapsed = (time.time() - start) * 1000
                self.manager.increment_count()
                return {
                    'task_id': task_id,
                    'inference_time_ms': round(elapsed, 2),
                    'prediction': result['labels'][0]
                }
        
        start_time = time.time()
        tasks = [bounded_inference(i, text) for i, text in enumerate(texts)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        avg_time = sum(r['inference_time_ms'] for r in results) / len(results)
        
        return {
            'mode': 'async',
            'total_tasks': len(texts),
            'concurrency': concurrency,
            'total_time_sec': round(total_time, 2),
            'throughput_qps': round(len(texts) / total_time, 2),
            'avg_inference_time_ms': round(avg_time, 2)
        }
    
    def cleanup(self):
        """清理资源"""
        self.manager.shutdown()


def generate_test_texts(num_samples: int = 100) -> List[str]:
    """生成测试文本"""
    templates = [
        "这部电影真是太精彩了，演员的表演非常出色，剧情也很吸引人。",
        "产品质量很差，用了两天就坏了，客服态度也不好，非常失望。",
        "服务态度很好，环境也很舒适，下次还会再来。",
        "物流太慢了，等了一个星期才收到，包装也有破损。",
        "性价比很高，功能齐全，操作简单，推荐购买。",
        "这本书写得很好，内容深入浅出，适合初学者阅读。",
        "软件经常崩溃，体验非常糟糕，希望能尽快修复bug。",
        "景色优美，空气清新，是一次很愉快的旅行体验。",
        "价格太贵了，不值这个钱，感觉被坑了。",
        "老师讲解得很清楚，学到了很多知识，受益匪浅。"
    ]
    
    texts = []
    for i in range(num_samples):
        # 随机组合或修改模板生成变体
        base = templates[i % len(templates)]
        texts.append(f"{base} [样本{i}]")
    
    return texts


def main():
    """主评测程序"""
    print("🚀 PyTorch BERT 多线程推理评测")
    print("=" * 60)
    
    # 检查GPU
    if torch.cuda.is_available():
        print(f"✅ GPU可用: {torch.cuda.get_device_name(0)}")
        print(f"   显存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
    else:
        print("⚠️  使用CPU推理")
    
    # 初始化评测器
    benchmark = ThreadedBenchmark(num_classes=2, max_workers=8)
    
    # 生成测试数据
    test_texts = generate_test_texts(num_samples=50)
    print(f"\n📊 生成测试数据: {len(test_texts)} 条文本")
    
    try:
        # # 1. 单线程基准测试
        # print("\n" + "="*60)
        # print("测试1: 单线程顺序推理")
        # print("="*60)
        # single_report = benchmark.run_threaded_benchmark(test_texts[:10], num_threads=1)
        # print(f"\n单线程结果:")
        # for key, value in single_report.items():
        #     print(f"  {key}: {value}")
        
        # # 2. 多线程并发测试
        # print("\n" + "="*60)
        # print("测试2: 多线程并发推理 (4线程)")
        # print("="*60)
        # thread_report = benchmark.run_threaded_benchmark(test_texts, num_threads=4)
        # print(f"\n多线程结果:")
        # for key, value in thread_report.items():
        #     print(f"  {key}: {value}")
        
        # # 3. 更多线程测试
        # print("\n" + "="*60)
        # print("测试3: 高并发测试 (8线程)")
        # print("="*60)
        # heavy_report = benchmark.run_threaded_benchmark(test_texts, num_threads=8)
        # print(f"\n高并发结果:")
        # for key, value in heavy_report.items():
        #     print(f"  {key}: {value}")
        
        # 4. 异步测试
        print("\n" + "="*60)
        print("测试4: 异步并发推理")
        print("="*60)
        async_report = asyncio.run(benchmark.run_async_benchmark(test_texts, concurrency=10))
        print(f"\n异步结果:")
        for key, value in async_report.items():
            print(f"  {key}: {value}")
        
        # # 5. 批量推理测试
        # print("\n" + "="*60)
        # print("测试5: 批量推理优化")
        # print("="*60)
        # start = time.time()
        # batch_results = benchmark.model.batch_predict(test_texts, batch_size=16)
        # batch_time = time.time() - start
        # print(f"批量推理: {len(test_texts)} 条, 总时间: {batch_time:.2f}s, QPS: {len(test_texts)/batch_time:.2f}")
        
        # # 结果对比
        # print("\n" + "="*60)
        # print("📈 性能对比总结")
        # print("="*60)
        # print(f"单线程 QPS:    {single_report['throughput_qps']}")
        # print(f"4线程 QPS:     {thread_report['throughput_qps']}")
        # print(f"8线程 QPS:     {heavy_report['throughput_qps']}")
        # print(f"异步模式 QPS:  {async_report['throughput_qps']}")
        # print(f"批量推理 QPS:  {len(test_texts)/batch_time:.2f}")
        
        # # 验证正确性
        # print("\n" + "="*60)
        # print("✅ 正确性验证")
        # print("="*60)
        # print(f"总推理次数: {benchmark.manager.get_inference_count()}")
        # print(f"所有任务成功完成，无异常")
        # print(f"GPU内存最终占用: {benchmark._get_gpu_memory()} MB")
        
    finally:
        # 清理资源
        print("\n" + "="*60)
        print("🧹 清理资源...")
        print("="*60)
        benchmark.cleanup()
        
        if torch.cuda.is_available():
            print(f"GPU内存清理后: {torch.cuda.memory_allocated() / 1024**2:.2f} MB")
        
        print("\n✨ 评测完成!")


if __name__ == "__main__":
    main()