"""
LLM 分析器

使用 Ollama Python SDK 调用本地部署的 LLM 进行文章分析
"""
import json
from typing import Optional, Dict, Any

from ollama import Client
from loguru import logger


# ============================================================================
# 模型注册表
# ============================================================================
# 每个模型的 base_url、调优参数等在此统一管理。
# 新增模型只需在此添加一条配置。
MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    # 核心推理模型：适合复杂逻辑、深层理解
    "deepseek-r1:32b": {
        "base_url": "http://192.168.10.43:11434",
        "temperature": 0.6,  # R1 系列最佳实践：保持 0.6 以防思考过程陷入死循环假死
        "top_p": 0.9,
        "num_predict": 4096,
        "timeout": 120,
    },
    # 核心指令模型：适合结构化输出、多任务处理
    "qwen3:32b": {
        "base_url": "http://192.168.10.45:11434",
        "temperature": 0.1,  # 指令模型可以使用极低温度以提高提取稳定性
        "top_p": 0.8,
        "num_predict": 4096,
        "timeout": 120,
    },
    # # 业务定制模型 (基于推理模型)
    # "lepure-deepseek:32b": {
    #     "base_url": "http://192.168.10.43:11434",
    #     "temperature": 0.6,
    #     "top_p": 0.9,
    #     "num_predict": 4096,
    #     "timeout": 120,
    # },
    # "lepure-deepseek-en:32b": {
    #     "base_url": "http://192.168.10.43:11434",
    #     "temperature": 0.6,
    #     "top_p": 0.9,
    #     "num_predict": 4096,
    #     "timeout": 120,
    # },
    # "lepure-deepseek-zh_en:32b": {
    #     "base_url": "http://192.168.10.43:11434",
    #     "temperature": 0.6,
    #     "top_p": 0.9,
    #     "num_predict": 4096,
    #     "timeout": 120,
    # },
    # 轻量推理模型：适合简单摘要、初步筛选
    "deepseek-r1:1.5b": {
        "base_url": "http://192.168.10.43:11434",
        "temperature": 0.6,
        "top_p": 0.9,
        "num_predict": 2048,
        "timeout": 60,
    },
    # 大型通用模型
    "llama3.3:70b-instruct-q2_k": {
        "base_url": "http://192.168.10.46:11434",
        "temperature": 0.1,
        "top_p": 0.9,
        "num_predict": 4096,
        "timeout": 180,
    },
}


class LLMAnalyzer:
    """
    LLM 分析器

    使用 Ollama SDK 调用本地部署的模型进行文章分析和结构化信息提取。
    通过 MODEL_REGISTRY 自动路由到正确的服务器。
    """

    # 系统提示词（类变量，所有实例共享）
    SYSTEM_PROMPT = """\
你是一个针对细胞与基因治疗(CGT)行业资深的商业情报辅助AI。
你的任务是从提供的新闻或文章内容中，抽取涉及到的具体企业、临床项目、研究场景等结构化信息。
请提取以下字段，并严格只输出JSON格式文本（不允许带有 markdown 的解释或者思考内容，所有思考请在内部完成）：

{
    "company_name": "公司或企业名称(如没有明确提到某个重点实体则为null)",
    "province": "省份(如没有则为null)",
    "city": "城市(如没有则为null)",
    "client_type": "客户类型(如严肃医疗、大健康、CRO等，如未知则为null)",
    "application_scene": "应用场景(如MSC, IPSC, AAV, 外泌体, Car-T, TIL, NK等，如未知则为null)",
    "project_name": "具体管线或项目名称(如没有则为null)",
    "project_stage": "项目所处阶段(如临床前, IND, I期, II期, III期, IIT等，如未知则为null)",
    "summary": "请用一段不超过100字的文章内容简要商业价值总结提取"
}

注意：如果你发现文章不包含实质性的商业项目、临床突破或新融资信息(例如纯科普文)，company_name 必须反馈 null，但 summary 需要保留。\
"""

    def __init__(self, default_model: str = "qwen3:32b"):
        """
        初始化 LLM 分析器

        Args:
            default_model: 默认使用的模型名称（必须在 MODEL_REGISTRY 中注册）
        """
        if default_model not in MODEL_REGISTRY:
            raise ValueError(
                f"模型 '{default_model}' 未在 MODEL_REGISTRY 中注册。"
                f"可用模型: {list(MODEL_REGISTRY.keys())}"
            )
        self.default_model = default_model
        # 为每个 base_url 缓存一个 Client 实例（避免重复创建）
        self._clients: Dict[str, Client] = {}
        logger.info(f"LLM 分析器已初始化，默认模型: {default_model}")

    def _get_client(self, base_url: str) -> Client:
        """获取或创建指定 base_url 的 Ollama Client"""
        if base_url not in self._clients:
            self._clients[base_url] = Client(host=base_url)
            logger.debug(f"创建 Ollama Client: {base_url}")
        return self._clients[base_url]

    def analyze_article(
        self,
        title: str,
        content: str,
        model_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        分析文章并提取结构化信息

        Args:
            title: 文章标题
            content: 清洗后的文章文本内容
            model_name: 指定模型名称，None 则使用默认模型

        Returns:
            Dict | None: 提取的结构化数据，调用失败返回 None
        """
        model = model_name or self.default_model

        if model not in MODEL_REGISTRY:
            logger.error(f"模型 '{model}' 未注册。可用: {list(MODEL_REGISTRY.keys())}")
            return None

        if not content.strip():
            logger.warning("提供的内容为空，无法进行 LLM 分析")
            return None

        config = MODEL_REGISTRY[model]
        client = self._get_client(config["base_url"])
        timeout = config.get("timeout", 120)

        # 适当放宽截断限制：现代模型支持 128k context，微信文章通常在 5000-15000 字之间。
        # 限制为前 30000 字符可确保 99.9% 的文章被完整读取，同时防止异常或恶意超长输入导致 OOM。
        user_prompt = f"标题：{title}\n\n内容：\n{content[:30000]}"

        try:
            logger.info(f"正在请求 Ollama 推理 [{model}]: {title}")

            response = client.chat(
                model=model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                format="json",
                options={
                    "temperature": config.get("temperature", 0.0),
                    "top_p": config.get("top_p", 0.9),
                    "num_predict": config.get("num_predict", 4096),
                },
            )

            content_text = response.message.content or ""

            # 清理可能的 markdown 包裹
            if content_text.startswith("```json"):
                content_text = content_text[7:]
            if content_text.endswith("```"):
                content_text = content_text[:-3]

            parsed_data = json.loads(content_text.strip())
            logger.info(f"成功分析文章 [{model}]: {title}")
            return parsed_data

        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析错误 ({title}): {e}")
            logger.error(f"LLM 响应内容: {content_text[:500]}")
            return None
        except Exception as e:
            logger.error(f"LLM 分析失败 [{model}] ({title}): {e}", exc_info=True)
            return None

    @staticmethod
    def list_models() -> list[str]:
        """列出所有已注册的模型"""
        return list(MODEL_REGISTRY.keys())
