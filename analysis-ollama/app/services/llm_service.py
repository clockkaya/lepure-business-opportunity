"""
LLM 服务

负责调用 Ollama 进行文章分析和信息提取
"""
import json
import requests
from typing import Optional, Dict, Any
from loguru import logger


class LLMService:
    """
    LLM 服务类
    
    使用 Ollama 本地服务进行文章分析和结构化信息提取
    """
    
    def __init__(self, ollama_base_url: str, model_name: str):
        """
        初始化 LLM 服务
        
        Args:
            ollama_base_url: Ollama 服务地址
            model_name: 模型名称
        """
        self.ollama_base_url = ollama_base_url
        self.model_name = model_name
        
        # 系统提示词
        self.system_prompt = """
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

注意：如果你发现文章不包含实质性的商业项目、临床突破或新融资信息(例如纯科普文)，company_name 必须反馈 null，但 summary 需要保留。
"""
    
    def analyze_article(self, title: str, content: str) -> Optional[Dict[str, Any]]:
        """
        分析文章并提取结构化信息
        
        Args:
            title: 文章标题
            content: 清洗后的文章文本内容
            
        Returns:
            Dict | None: 提取的结构化数据
            {
                "company_name": str | None,
                "province": str | None,
                "city": str | None,
                "client_type": str | None,
                "application_scene": str | None,
                "project_name": str | None,
                "project_stage": str | None,
                "summary": str
            }
            
            如果 LLM 调用失败或超时，返回 None
        """
        if not content.strip():
            logger.warning("提供的内容为空，无法进行 LLM 分析")
            return None
        
        # 截断内容以防止 OOM 或超时（保留前 4000 字符）
        user_prompt = f"标题：{title}\n\n内容：\n{content[:4000]}"
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "format": "json"  # Ollama 的严格 JSON 约束选项
        }
        
        try:
            logger.info(f"正在请求 Ollama 推理: {title}")
            response = requests.post(
                f"{self.ollama_base_url}/api/chat",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            result_json = response.json()
            content_text = result_json.get("message", {}).get("content", "")
            
            # 解析返回的 JSON
            # 如果 LLM 仍然输出被反引号包裹的 JSON，清理它
            if content_text.startswith("```json"):
                content_text = content_text[7:]
            if content_text.endswith("```"):
                content_text = content_text[:-3]
            
            parsed_data = json.loads(content_text.strip())
            logger.info(f"成功分析文章: {title}")
            return parsed_data
            
        except requests.exceptions.Timeout:
            logger.error(f"LLM 分析超时（120 秒）: {title}")
            return None
        except requests.exceptions.ConnectionError as e:
            logger.error(f"调用 Ollama 连接错误 ({title}): {e}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.error(f"调用 Ollama HTTP 错误 ({title}): {e.response.status_code} - {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析错误 ({title}): {e}")
            logger.error(f"LLM 响应内容: {content_text[:500]}")
            return None
        except Exception as e:
            logger.error(f"分析文章时发生意外错误 ({title}): {e}", exc_info=True)
            return None
