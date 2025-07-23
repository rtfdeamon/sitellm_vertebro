# YaLLM

Using Yandex GPT 5 with LLAMA CCP

## Dependencies
1. gcc or clang
2. cmake
3. openblas
4. [CUDA](https://developer.nvidia.com/cuda-toolkit)

## Python Deps
`CMAKE_ARGS="-DGGML_CUDA=on -DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS -DGGML_VULKAN=on" uv sync`