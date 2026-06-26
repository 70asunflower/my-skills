# CUDA Vector Add 入门

> **定位**：一篇短技术博客示例，用于测试 short_blog 模式。

## 背景

CUDA 编程的第一个例子通常是 **Vector Add**。

## 核心代码

```cpp
__global__ void vec_add(float* a, float* b, float* c, int n) {
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n) c[i] = a[i] + b[i];
}
```

## 核心要点

- 理解 thread/block/grid。
- 理解 global memory。
- 学会做 correctness check。

## 面试常问

**Q1：为什么要做边界检查？**

因为 grid size 通常向上取整，最后一个 block 可能有多余线程。
