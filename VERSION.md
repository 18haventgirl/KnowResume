基于版面结构的多模态简历智能解析系统
开发⼈员
项目描述：针对传统方案难以处理多栏排版和图片型简历的问题，构建融合版面检测、OCR互补与LLM抽取的解析系
统，支持PDF/图片/Office等格式，信息抽取准确率93.1%。
项目实现：
·文本提取采用pdfplumber+OCR双路融合，先黑化遮罩已提取文本区域再做OCR补充。异常PDF自动触发混合文本策
略，基本信息与其余字段走不同文本通道。
·Docx绕过python-docx直接解析底层word/document.xml，递归提取叶子表格和段落，同时从word/media/提取嵌入
图片OCR，避免表格信息丢失。
·版面检测基于ONNX YOLO模型，按布局中心坐标聚类重排阅读顺序，低占比布局自动取消分配，相邻文本块左右微
调。
·LLM抽取按basic_info/work_experience/education三类Prompt独立设计，并行调用支持多通道路由与主备切换，
json-repair修复断裂输出。支持远程API和vLLM进程内库两种部署模式。
遇到的问题：Word表格嵌套与合并单元格场景下常规库信息丢失严重，改为直接解析XML提取叶子表格解决。
技术栈：pdfplumber、RapidOCR、OpenAI SDK、vLLM、ONNX Runtime、OpenCV、BeautifulSoup4、json-repair、Gradio
