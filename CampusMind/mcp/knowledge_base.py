"""
RAG 知识库 —— 基于 ChromaDB 的真实检索实现。

功能：
  1. 文档导入：将文本切片后存入 ChromaDB（自动生成 Embedding）
  2. 语义检索：根据 query 从知识库中检索最相关的文档片段
  3. 与 MCP 工具框架集成：作为 knowledge_search 工具的真实 handler

ChromaDB 在这里的角色：
  - memory/ 中用于存储对话记忆（情景记忆 + 用户画像）
  - 这里用于存储知识库文档（RAG 检索）
  两者是不同的 collection，互不干扰。
"""
import hashlib
import logging
from typing import Any, Dict, List, Optional

import chromadb

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """
    基于 ChromaDB 的 RAG 知识库。

    ChromaDB 内置了 Embedding 模型（all-MiniLM-L6-v2），
    调用 add() 时自动生成向量，query() 时自动做语义匹配。
    不需要额外调用 LLM Embedding API。
    """

    COLLECTION_NAME = "campus_knowledge_base"

    def __init__(
        self,
        chroma_host: str = "localhost",
        chroma_port: int = 8000,
        chroma_path: str = "./data/chroma",
    ):
        # 优先连接独立 ChromaDB 服务（服务端内置 embedding 模型，客户端无需下载）
        self._use_server = False
        try:
            # HttpClient 默认也会初始化 ChromaDB telemetry；显式关闭避免 posthog 兼容性错误日志。
            self._client = chromadb.HttpClient(
                host=chroma_host,
                port=chroma_port,
                settings=chromadb.Settings(anonymized_telemetry=False),
            )
            self._client.heartbeat()
            self._use_server = True
            logger.info(f"知识库 ChromaDB 已连接: {chroma_host}:{chroma_port}")
        except Exception:
            logger.info(f"知识库 ChromaDB 服务不可用，使用本地模式: {chroma_path}")
            self._client = chromadb.PersistentClient(
                path=chroma_path,
                settings=chromadb.Settings(anonymized_telemetry=False),
            )

        # 使用服务端时不传 embedding_function，让服务端处理
        # 本地模式时也不传，使用 ChromaDB 默认的（会触发模型下载）
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"description": "CampusMind 校园政策与服务知识库"},
        )

        # 如果知识库为空，导入默认文档
        if self._collection.count() == 0:
            self._load_default_docs()

    # ── 文档管理 ──────────────────────────────────────────────────────────────

    def add_documents(self, documents: List[Dict[str, str]]) -> int:
        """
        批量导入文档到知识库。

        documents 格式: [{"title": "...", "content": "..."}, ...]
        长文档会自动切片（每片 500 字）。
        """
        ids, docs, metas = [], [], []

        for doc in documents:
            title   = doc.get("title", "")
            content = doc.get("content", "")
            chunks  = self._chunk_text(content, chunk_size=500)

            for i, chunk in enumerate(chunks):
                doc_id = hashlib.md5(f"{title}_{i}_{chunk[:50]}".encode()).hexdigest()
                ids.append(doc_id)
                docs.append(chunk)
                metas.append({"title": title, "chunk_index": i, "total_chunks": len(chunks)})

        if ids:
            # ChromaDB 会自动生成 Embedding
            self._collection.add(ids=ids, documents=docs, metadatas=metas)
            logger.info(f"知识库导入 {len(ids)} 个文档片段")

        return len(ids)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        语义检索：根据 query 返回最相关的文档片段。

        ChromaDB 内部自动将 query 转为向量，与存储的文档向量做余弦相似度匹配。
        """
        results = self._collection.query(
            query_texts=[query],
            n_results=top_k,
        )

        items = []
        if results["documents"] and results["documents"][0]:
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                items.append({
                    "title":    meta.get("title", ""),
                    "content":  doc,
                    "score":    round(1.0 - dist, 4),  # ChromaDB 返回距离，转为相似度
                    "chunk":    meta.get("chunk_index", 0),
                })

        return items

    @property
    def doc_count(self) -> int:
        return self._collection.count()

    # ── MCP 工具 handler ─────────────────────────────────────────────────────

    async def search_handler(self, params: Dict[str, Any], context: Any) -> List[Dict]:
        """
        作为 MCP 工具的 handler 注册。

        MCPToolManager.register(Tool(
            name="knowledge_search",
            handler=kb.search_handler,
            ...
        ))
        """
        query = params.get("query", "")
        top_k = params.get("top_k", 5)
        return self.search(query, top_k=top_k)

    # ── 内部方法 ──────────────────────────────────────────────────────────────

    def _chunk_text(self, text: str, chunk_size: int = 500) -> List[str]:
        """将长文本按 chunk_size 切片，保留语义完整性（按句号/换行切分）。"""
        if len(text) <= chunk_size:
            return [text] if text.strip() else []

        chunks = []
        current = ""
        # 按句子切分
        sentences = text.replace("\n", "。").split("。")
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            if len(current) + len(sent) + 1 > chunk_size:
                if current:
                    chunks.append(current)
                current = sent
            else:
                current = f"{current}。{sent}" if current else sent

        if current:
            chunks.append(current)

        return chunks

    def _load_default_docs(self) -> None:
        """导入 CampusMind 演示知识。真实部署时应替换为学校官方材料。"""
        default_docs = [
            {
                "title": "在读证明办理示例",
                "content": (
                    "在读证明通常通过学校网上办事大厅或教务系统申请。"
                    "学生应先核对姓名、学号、学院和培养层次，再选择证明用途。"
                    "部分学校支持电子签章后直接下载，纸质证明可能需要到指定窗口领取。"
                    "具体入口、办理时限和是否需要导师或学院审核，应以本校当前通知为准。"
                ),
            },
            {
                "title": "奖助学金咨询示例",
                "content": (
                    "奖学金和助学金通常按学年发布评定通知。"
                    "申请人需要确认成绩、科研、综合测评或家庭经济情况等条件，并在截止时间前提交材料。"
                    "学院初审、公示和学校复核是常见环节，但不同学校和项目要求不同。"
                    "CampusMind 只能提供流程说明，不能判断申请人是否一定符合资格。"
                ),
            },
            {
                "title": "校园网认证排查",
                "content": (
                    "校园网无法认证时，先确认账号状态和所在区域是否存在集中故障。"
                    "重新连接网络并打开认证页面，检查系统时间、代理、VPN 和自定义 DNS。"
                    "如果同一账号在多台设备同时登录，可能触发并发限制。"
                    "仍无法连接时，应记录发生时间、楼栋区域、设备系统和错误码，再联系学校网络中心。"
                ),
            },
            {
                "title": "学校 VPN 使用指引",
                "content": (
                    "校外访问校内资源时，通常需要使用学校当前版本的 VPN 客户端或 Web VPN。"
                    "应从学校网络中心官网下载客户端和配置文件，不要使用来源不明的安装包。"
                    "连接失败时检查统一身份认证账号、系统时间、网络代理和客户端版本。"
                    "涉及账号锁定、证书错误或持续超时时，需要网络中心后台核验。"
                ),
            },
            {
                "title": "校园卡挂失与补办",
                "content": (
                    "校园卡遗失后应尽快通过学校官方 App、公众号、自助终端或一卡通中心挂失。"
                    "补卡通常需要本人有效证件，部分学校会收取工本费。"
                    "新卡启用后，余额和身份信息可能需要一定同步时间。"
                    "不要向任何人提供支付密码、短信验证码或完整银行卡号。"
                ),
            },
            {
                "title": "宿舍报修与安全处理",
                "content": (
                    "普通宿舍故障可通过学校后勤报修平台提交楼栋、房间、故障类型和照片。"
                    "提交后保留报修单号，超过处理时限可联系宿管或后勤值班人员。"
                    "如出现漏电、冒烟、火情或大面积漏水，应立即远离危险区域并联系宿管、保卫处或紧急服务。"
                    "CampusMind 不会创建真实报修工单。"
                ),
            },
        ]
        self.add_documents(default_docs)
        logger.info(f"已导入默认校园知识库: {len(default_docs)} 篇文档")
