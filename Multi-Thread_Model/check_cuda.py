
import torch
import torch.nn as nn
import torch.nn.functional as F
import asyncio
import threading
import time
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import List, Dict, Optional, Union, Tuple
import numpy as np
from contextlib import contextmanager
import gc
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

# 设置随机种子保证可复现
torch.manual_seed(42)
np.random.seed(42)

print("PyTorch版本:", torch.__version__)
print("CUDA是否可用:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("CUDA设备:", torch.cuda.get_device_name(0))
    print(f"GPU内存: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
