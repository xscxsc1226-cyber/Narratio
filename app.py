import streamlit as st
from openai import OpenAI
import time
import re
import json
from PIL import Image
import base64
from datetime import datetime
from uuid import uuid4
import hashlib
from supabase import create_client, Client
from io import BytesIO
import random
import string
import html

# ===================== 0. 全局设置 =====================
st.set_page_config(page_title="Echoem", page_icon="🪽", layout="wide", initial_sidebar_state="collapsed")

# 注入全局优化 CSS（全面升级视觉体验 + 移动端适配）
st.markdown("""
<!-- 关键：强制移动端使用设备宽度，防止页面被缩放 -->
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">

<style>
    /* 1. 基础重置 - 彻底清理原生样式 */
    [data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {
        display: none !important;
    }
    .block-container { 
        padding-top: 1rem !important; 
        padding-bottom: 80px !important; 
        max-width: 650px; 
        margin: 0 auto !important;
    }

    /* 2. 整体视觉风格 - 更贴近真实聊天APP */
    .stApp { 
        background-color: #F0F2F5; 
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }
    
    /* 3. 底部导航栏 - 更精致的固定导航 */
    .nav-wrapper {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: #FFFFFF;
        border-top: 1px solid #E5E7EB;
        z-index: 1000;
        padding: 8px 0;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.03);
    }

    /* 4. 聊天气泡 - 优化视觉层次和交互感 */
    .chat-bubble-row { 
        display: flex; 
        margin-bottom: 16px; 
        align-items: center;
        position: relative;
    }
    .chat-bubble-row.me { justify-content: flex-end; }
    .chat-bubble-avatar { 
        width: 40px; 
        height: 40px; 
        border-radius: 50%;
        overflow: hidden; 
        margin: 0 8px; 
        flex-shrink: 0; 
        background-color: #F3F4F6;
        display: flex; 
        align-items: center; 
        justify-content: center; 
        font-size: 18px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .chat-bubble-avatar img { 
        width: 100%; 
        height: 100%; 
        object-fit: cover; 
    }
    .chat-bubble-content { 
        max-width: 70%; 
        padding: 14px 18px; 
        border-radius: 20px; 
        font-size: 15px; 
        line-height: 1.45;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        position: relative;
    }
    .chat-bubble-other { 
        background-color: #FFFFFF; 
        border: 1px solid #E5E7EB;
        border-bottom-left-radius: 6px;
        color: #111827;
    }
    .chat-bubble-me { 
        background-color: #3B82F6;
        color: #FFFFFF;
        border-bottom-right-radius: 6px;
    }
    
    /* 5. 朋友圈卡片 */
    .moment-card { 
        background: transparent; 
        padding: 12px 0 16px 0; 
        border-radius: 0; 
        margin-bottom: 0; 
        border-bottom: 1px solid #E5E7EB;
        box-shadow: none;
    }
    .comment-area { 
        background: transparent; 
        padding: 8px 0 0 0; 
        margin-top: 8px; 
        font-size: 14px; 
    }
    .comment-item { 
        padding: 8px 0; 
        border-bottom: 1px solid #E5E5E5;
        line-height: 1.4;
    }
    .comment-item:last-child { border-bottom: none; }
    .comment-user { 
        color: #576B95; 
        font-weight: 500; 
        margin-right: 4px; 
    }

    /* 6. 底部导航按钮 */
    .nav-wrapper .stButton>button {
        border-radius: 12px !important;
        padding: 8px 6px !important;
        font-size: 12px !important;
        color: #6B7280 !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        font-weight: 500;
    }
    .nav-wrapper .stButton>button[kind="primary"] {
        background-color: #EFF6FF !important;
        color: #3B82F6 !important;
        font-weight: 600;
    }

    /* 7. 普通按钮 */
    .stButton>button { 
        border-radius: 0 !important; 
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 6px 0 !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #111827 !important;
    }
    .stButton>button:hover { background-color: #F9FAFB !important; }

    /* 8. 转账卡片 */
    .transfer-card {
        background: linear-gradient(135deg, #F59E0B, #FBBF24);
        border-radius: 18px;
        padding: 12px 16px;
        min-width: 220px;
        color: #FFFFFF;
        display: flex;
        flex-direction: column;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
    }
    .transfer-title { font-size: 12px; opacity: 0.9; margin-bottom: 2px; }
    .transfer-amount { font-size: 24px; font-weight: 700; margin: 4px 0; }
    .transfer-note { font-size: 13px; opacity: 0.95; margin-bottom: 4px; }
    .transfer-status { font-size: 11px; margin-top: 4px; opacity: 0.9; text-align: right; }
    .transfer-card.received {
        background: linear-gradient(135deg, #FEF3C7, #FDE68A);
        color: #92400E;
    }

    /* 9. 登录/注册页面 */
    .auth-container { max-width: 400px; margin: 0 auto; padding: 40px 20px; }
    .auth-title { font-size: 28px; font-weight: 700; color: #111827; margin-bottom: 8px; }
    .auth-subtitle { color: #6B7280; margin-bottom: 30px; }

    /* 10. 消息列表项 */
    .chat-item {
        display: flex;
        padding: 12px 16px;
        background: #FFFFFF;
        border-bottom: 0.5px solid #E5E5E7;
        transition: background 0.2s;
        cursor: pointer;
    }
    .chat-item:active { background-color: #F2F2F7; }

    /* 小箭头按钮 */
    .chat-arrow .stButton>button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        width: 32px !important;
        height: 32px !important;
        padding: 0 !important;
        border-radius: 16px !important;
        font-size: 18px !important;
        color: #9CA3AF !important;
    }
    .chat-arrow .stButton>button:hover {
        background: #F3F4F6 !important;
        color: #6B7280 !important;
    }

    /* ================= 关键：移动端适配优化 ================= */
    @media (max-width: 768px) {
        /* 强制页面宽度为设备宽度，防止溢出 */
        html, body {
            width: 100vw !important;
            overflow-x: hidden !important;
            max-width: 100% !important;
        }
        
        /* 主容器宽度适配 */
        .block-container {
            max-width: 100% !important;
            padding-left: 12px !important;
            padding-right: 12px !important;
            padding-bottom: 100px !important; /* 增加底部padding防止被导航栏遮挡 */
        }

        /* Streamlit 主容器 */
        .stApp {
            width: 100vw !important;
            max-width: 100% !important;
            overflow-x: hidden !important;
        }

        /* 强制所有 columns 保持横向排列（导航栏关键） */
        div[data-testid="stHorizontalBlock"] {
            flex-direction: row !important;
            flex-wrap: nowrap !important;
            align-items: center !important;
            width: 100% !important;
            gap: 0 !important;
        }
        
        /* 均匀分布列 */
        div[data-testid="column"] {
            width: auto !important;
            flex: 1 1 0% !important;
            min-width: 0 !important;
            padding: 0 2px !important;
        }
        
        /* 导航栏按钮适配 */
        div[data-testid="column"] button {
            padding-left: 0 !important;
            padding-right: 0 !important;
            font-size: 11px !important;
            width: 100% !important;
        }

        /* 聊天气泡宽度优化 */
        .chat-bubble-content {
            max-width: 82% !important;
            font-size: 14px !important;
        }

        /* 消息列表卡片缩紧 */
        .chat-item {
            padding: 10px 12px !important;
        }

        /* 头像缩小 */
        .chat-bubble-avatar {
            width: 34px !important;
            height: 34px !important;
        }

        /* 导航栏更紧凑 */
        .nav-wrapper {
            padding: 6px 0 !important;
        }
        .nav-wrapper .stButton>button {
            font-size: 11px !important;
            padding: 6px 2px !important;
        }
    }

    /* 超小屏幕额外优化（如iPhone SE） */
    @media (max-width: 375px) {
        .block-container {
            padding-left: 8px !important;
            padding-right: 8px !important;
        }
        
        .chat-bubble-content {
            max-width: 85% !important;
            padding: 12px 14px !important;
            font-size: 13px !important;
        }
        
        .nav-wrapper .stButton>button {
            font-size: 10px !important;
        }
    }

    /* 11. 收款按钮 */
    .receive-btn {
        background-color: #FFFFFF !important;
        color: #F59E0B !important;
        border: 1px solid #F59E0B !important;
        border-radius: 8px !important;
        padding: 4px 12px !important;
        font-size: 13px !important;
        margin-top: 8px !important;
        width: auto !important;
    }

    /* 12. 发现页互动工具栏 */
    .interaction-toolbar {
        display: flex;
        align-items: center;
        justify-content: flex-start;
        gap: 15px;
        margin-top: 12px;
        margin-bottom: 15px;
    }
    .interaction-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 6px 16px;
        border-radius: 8px;
        background-color: #F9FAFB;
        border: 1px solid #E5E7EB;
        font-size: 13px;
        color: #6B7280;
        width: 90px;
        height: 32px;
        text-align: center;
    }
    .interaction-toolbar .stButton>button {
        width: 90px !important;
        height: 32px !important;
        padding: 6px 16px !important;
        border-radius: 8px !important;
        background-color: #F9FAFB !important;
        border: 1px solid #E5E7EB !important;
        font-size: 13px !important;
        color: #6B7280 !important;
        text-align: center !important;
        justify-content: center !important;
    }
    .comment-input-container {
        margin-top: 10px;
        padding-top: 10px;
        border-top: 1px solid #F3F4F6;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .comment-input { flex: 1; }
    .comment-send-btn {
        width: 60px !important;
        padding: 6px 0 !important;
        border-radius: 8px !important;
        background-color: #3B82F6 !important;
        color: white !important;
        text-align: center !important;
        justify-content: center !important;
    }

    /* 消息列表：摘要单行、与昵称左对齐 */
    .chat-list-item .stButton>button {
        padding: 0 !important;
        margin: 0 !important;
        width: 100% !important;
        text-align: left !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        font-size: 14px !important;
        color: #6B7280 !important;
        font-weight: normal !important;
        padding-left: 0 !important;
        margin-left: 0 !important;
        border-radius: 0 !important;
    }
    
    /* 记忆库展示样式 */
    .memory-bank-info {
        background: #F0F9FF;
        border: 1px solid #BAE6FD;
        border-radius: 8px;
        padding: 10px 14px;
        margin: 10px 0;
        font-size: 13px;
        color: #0369A1;
    }
    .memory-item {
        background: #F9FAFB;
        border-radius: 6px;
        padding: 8px 12px;
        margin: 6px 0;
        font-size: 13px;
        color: #374151;
        border-left: 3px solid #3B82F6;
    }
</style>
""", unsafe_allow_html=True)

# ===================== 1. 数据库逻辑 =====================

@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_supabase()

import bcrypt

def hash_password(password):
    # 生成盐并哈希，bcrypt 会自动处理加盐过程
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password, hashed):
    # 验证密码是否匹配
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False
        
def save_cloud_data():
    if "username" in st.session_state:
        # 优化保存逻辑，减少延迟
        try:
            supabase.table("user_data").update({
                "profile": st.session_state.user_profile,
                "characters": st.session_state.characters,
                "moments": st.session_state.moments
            }).eq("username", st.session_state.username).execute()
        except Exception as e:
            st.error(f"数据保存失败: {str(e)}")

def update_password(username, old_password, new_password):
    """修改密码函数"""
    # 验证原密码
    res = supabase.table("user_data").select("password_hash").eq("username", username).execute()
    if not res.data:
        return False, "用户不存在"
    
    if not verify_password(old_password, res.data[0]["password_hash"]):
        return False, "原密码错误"
    
    if old_password == new_password:
        return False, "新密码不能与原密码相同"
    
    # 更新密码
    supabase.table("user_data").update({
        "password_hash": hash_password(new_password)
    }).eq("username", username).execute()
    
    return True, "密码修改成功"

def process_uploaded_image(uploaded_file, target_size=None):
    if not uploaded_file: return None
    try:
        image = Image.open(uploaded_file)
        if target_size: image.thumbnail(target_size)
        buffered = BytesIO()
        fmt = uploaded_file.type.split("/")[1].upper()
        if fmt == "JPG": fmt = "JPEG"
        image.save(buffered, format=fmt, quality=80) 
        file_path = f"{st.session_state.username}/{uuid4().hex}.{uploaded_file.name.split('.')[-1]}"
        supabase.storage.from_("images").upload(path=file_path, file=buffered.getvalue(), file_options={"content-type": uploaded_file.type})
        return supabase.storage.from_("images").get_public_url(file_path)
    except: return None

def get_avatar_display(avatar_data, default_emoji):
    if avatar_data and isinstance(avatar_data, str) and (avatar_data.startswith("http") or avatar_data.startswith("data:image")):
        return avatar_data
    return default_emoji

def get_avatar_html(avatar_data):
    """根据头像数据返回用于消息列表的 HTML 片段"""
    av = get_avatar_display(avatar_data, "🪽")
    if isinstance(av, str) and av.startswith("http"):
        return f'<img src="{av}" style="width:44px;height:44px;border-radius:50%;object-fit:cover;">'
    else:
        return f'<div style="width:44px;height:44px;border-radius:50%;background:#F3F4F6;display:flex;align-items:center;justify-content:center;font-size:20px;">{av}</div>'

def safe_text(text):
    """将文本转义并处理换行符，用于 HTML 渲染"""
    if text is None:
        return ""
    return html.escape(str(text)).replace("\n", "<br>")

# ===================== 0.1 全局系统行为设定 =====================

BASE_SYSTEM_RULES = """
【通用行为规则】
1. 你只能扮演当前这个角色，不要引用或提及其他任何角色的记忆、设定或聊天内容，禁止“串台”。
2. 禁止使用任何括号包裹的动作描写，例如“（笑）”“(摸摸你)”“（揉揉你的头）”，只用自然语言表达你的想法和感受。
3. 回复尽量口语化、简短自然，每条消息不宜过长。
4. 当你一次性想表达多句内容时，请使用“｜”将不同条消息分隔开，例如：
   好呀｜那我们明天见｜路上注意安全
   系统会把这些分成多条气泡发送给对方。
5. 当你觉得剧情或情绪需要时，可以“自发”发起一笔转账，而不是等待对方选择。
   - 这时请专门用一条消息，格式严格为：转账卡|金额=XXX|备注=这里写一句简单备注
   - 例如：转账卡|金额=520|备注=这是提前给你的生日礼物
   - 不要在这一条消息里夹带其他对话内容，其他想说的话请用前后单独的消息表达。
"""

def build_system_prompt(char, scene: str = "chat") -> str:
    """为所有场景统一构造系统提示，确保不串台、不用括号动作等"""
    parts = [BASE_SYSTEM_RULES.strip()]
    parts.append(f"【当前角色】\n名字：{char['name']}\n人设：{char.get('persona','')}")
    
    # 添加核心记忆（来自AI自动提取的记忆库）
    memory_bank = char.get("memory_bank", {})
    core_memories = memory_bank.get("core_memories", [])
    if core_memories:
        parts.append(f"【核心记忆库】\n" + "\n".join([f"- {m}" for m in core_memories]))
    
    # 保留旧版手动设置的记忆（兼容）
    mem = char.get("memory", "")
    if mem:
        parts.append(f"【角色记忆】\n{mem}")
    
    user_self = st.session_state.user_profile.get("self_persona", "") if "user_profile" in st.session_state else ""
    if user_self:
        parts.append(f"【对话对象设定】\n{user_self}")
    if scene == "moment":
        parts.append("【当前场景】你正在朋友圈的评论区，用轻松、简短的语气回复对方的动态。对方刚刚回复了你，你需要针对这条回复做出回应。")
    else:
        parts.append("【当前场景】你正在与对方进行一对一私聊，请保持亲切、自然。")
    return "\n\n".join(parts)

def get_context_messages(char):
    """获取用于API调用的上下文消息（最近10条 + 当前消息）"""
    memory_bank = char.get("memory_bank", {})
    recent_context = memory_bank.get("recent_context", [])
    
    # 合并最近上下文和当前消息历史，去重并保持顺序
    all_msgs = recent_context + char.get("messages", [])
    
    # 去重：基于content和role
    seen = set()
    unique_msgs = []
    for m in all_msgs:
        key = (m.get("role"), m.get("content"))
        if key not in seen:
            seen.add(key)
            unique_msgs.append(m)
    
    # 返回最后10条
    return unique_msgs[-10:]

def extract_memories(char, user_msg, ai_response):
    """让AI判断并提取重要记忆，返回需要存入核心记忆的内容列表"""
    api_key, model, base_url = get_api_info(char)
    if not api_key:
        return []
    
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        
        # 构建提取记忆的prompt
        extract_prompt = f"""你是{char['name']}，请分析刚才的对话，判断是否有需要长期记住的重要信息。

【你的设定】{char.get('persona', '')}

【用户刚说的话】{user_msg}

【你刚回复】{ai_response}

【现有核心记忆】
{chr(10).join([f"- {m}" for m in char.get('memory_bank', {}).get('core_memories', [])]) or "（暂无）"}

请判断：
1. 对话中是否包含需要长期记住的事实（如：用户的喜好、重要日期、承诺、约定、用户的身份背景等）
2. 如果已有记忆需要更新（如用户改变了喜好），请指出

输出格式（严格JSON）：
{{
    "new_memories": ["记忆1", "记忆2"],  // 新增的重要事实，没有则留空数组
    "update_memories": [{{"old": "原记忆", "new": "更新后记忆"}}],  // 需要更新的记忆，没有则留空数组
    "reason": "简要说明提取理由"
}}

注意：
- 只提取真正重要、长期有价值的信息
- 不要提取日常寒暄、临时性内容
- 记忆要简洁，一句话概括
- 如果没有重要信息，返回空数组"""

        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": extract_prompt}],
            temperature=0.3
        )
        
        raw = resp.choices[0].message.content.strip()
        
        # 尝试解析JSON
        try:
            # 处理可能的markdown代码块
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            
            result = json.loads(raw)
            new_memories = result.get("new_memories", [])
            update_memories = result.get("update_memories", [])
            
            # 处理更新：替换旧记忆
            current_memories = char.get("memory_bank", {}).get("core_memories", [])
            
            # 应用更新
            for update in update_memories:
                old_mem = update.get("old")
                new_mem = update.get("new")
                if old_mem in current_memories:
                    current_memories[current_memories.index(old_mem)] = new_mem
            
            # 添加新记忆（去重）
            for mem in new_memories:
                if mem not in current_memories:
                    current_memories.append(mem)
            
            # 限制核心记忆数量（最多20条，防止无限增长）
            if len(current_memories) > 20:
                current_memories = current_memories[-20:]
            
            return current_memories
            
        except json.JSONDecodeError:
            # 如果解析失败，返回空
            return []
            
    except Exception as e:
        # 静默失败，不影响主流程
        return []

def update_memory_bank(char, user_msg, ai_response):
    """更新角色的记忆库：维护最近10条上下文 + 提取核心记忆"""
    if "memory_bank" not in char:
        char["memory_bank"] = {
            "core_memories": [],
            "recent_context": []
        }
    
    memory_bank = char["memory_bank"]
    
    # 1. 更新最近上下文：添加新消息，保持最多10条
    recent_context = memory_bank.get("recent_context", [])
    
    # 添加用户消息
    recent_context.append({
        "role": "user",
        "content": user_msg,
        "time": datetime.now().isoformat()
    })
    
    # 添加AI回复（清理后的）
    clean_response = re.sub(r"[（(][^）)]*[）)]", "", ai_response).strip()
    if clean_response:
        # 处理多段回复，只取第一段作为上下文（避免转账指令等干扰）
        first_seg = re.split(r"[｜|]+", clean_response)[0].strip()
        if first_seg and not first_seg.startswith("转账卡"):
            recent_context.append({
                "role": "assistant", 
                "content": first_seg,
                "time": datetime.now().isoformat()
            })
    
    # 只保留最近10条
    if len(recent_context) > 10:
        recent_context = recent_context[-10:]
    
    memory_bank["recent_context"] = recent_context
    
    # 2. 提取核心记忆（异步，不阻塞回复）
    new_memories = extract_memories(char, user_msg, ai_response)
    if new_memories:
        memory_bank["core_memories"] = new_memories
    
    char["memory_bank"] = memory_bank

# ===================== 2. 身份验证 =====================

def validate_username(username):
    """验证账号名是否为英文字母或数字"""
    return bool(re.match(r'^[a-zA-Z0-9]+$', username))

def check_password():
    if "password_correct" not in st.session_state:
        # 优化登录页面布局
        st.markdown("""
        <div class="auth-container">
            <div style="text-align:center;">
                <h1 class="auth-title">🪽 Echoem</h1>
                <p class="auth-subtitle">AI 伴侣聊天空间</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        t1, t2 = st.tabs(["登录", "注册"])
        with t1:
            st.markdown("<div style='padding:0 20px;'>", unsafe_allow_html=True)
            u = st.text_input("账号", key="l_u", placeholder="请输入你的账号")
            p = st.text_input("密码", type="password", key="l_p", placeholder="请输入你的密码")
            if st.button("进入", use_container_width=True, type="primary"):
                res = supabase.table("user_data").select("*").eq("username", u).execute()
                if res.data and verify_password(p, res.data[0]["password_hash"]):
                    # 数据迁移：为旧角色添加memory_bank
                    characters = res.data[0]["characters"] or []
                    for char in characters:
                        if "memory_bank" not in char:
                            char["memory_bank"] = {
                                "core_memories": [],
                                "recent_context": []
                            }
                    
                    st.session_state.update({
                        "password_correct":True, 
                        "username":u, 
                        "user_profile":res.data[0]["profile"], 
                        "characters":characters, 
                        "moments":res.data[0]["moments"] or []
                    })
                    st.rerun()
                else: 
                    st.error("账号或密码错误", icon="❌")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with t2:
            st.markdown("<div style='padding:0 20px;'>", unsafe_allow_html=True)
            nu = st.text_input("新账号", key="r_u", placeholder="只能包含英文字母和数字")
            np = st.text_input("新密码", type="password", key="r_p", placeholder="请设置密码")
            
            # 账号名验证提示
            if nu and not validate_username(nu):
                st.warning("账号名只能包含英文字母和数字", icon="⚠️")
            
            if st.button("注册", use_container_width=True, type="primary"):
                if nu and np:
                    if not validate_username(nu):
                        st.error("账号名只能包含英文字母和数字", icon="❌")
                    else:
                        # 检查账号是否已存在
                        res = supabase.table("user_data").select("username").eq("username", nu).execute()
                        if res.data:
                            st.error("该账号已存在", icon="❌")
                        else:
                            supabase.table("user_data").insert({
                                "username":nu, 
                                "password_hash":hash_password(np), 
                                "profile":{"nickname":nu,"avatar":None,"global_api_key":"","global_provider":"deepseek","global_model":"deepseek-chat"}, 
                                "characters":[], 
                                "moments":[]
                            }).execute()
                            st.success("注册成功，请至登录页进入账号...", icon="✅")
                            time.sleep(1)
                            st.rerun()
                else:
                    st.warning("账号和密码不能为空", icon="⚠️")
            st.markdown("</div>", unsafe_allow_html=True)
        return False
    return True

if not check_password(): st.stop()

# ===================== 3. 核心工具 =====================

# 支持的 LLM 提供商（OpenAI 兼容接口）
LLM_PROVIDERS = [
    {"id": "deepseek", "name": "DeepSeek", "base_url": "https://api.deepseek.com", "default_model": "deepseek-chat",
     "models": ["deepseek-chat", "deepseek-reasoner", "deepseek-r1"]},
    {"id": "kimi", "name": "Kimi (月之暗面)", "base_url": "https://api.moonshot.cn/v1", "default_model": "moonshot-v1-8k",
     "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"]},
    {"id": "openai", "name": "OpenAI (GPT)", "base_url": "https://api.openai.com/v1", "default_model": "gpt-4o-mini",
     "models": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-4"]},
    {"id": "gemini", "name": "Google Gemini", "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "default_model": "gemini-1.5-flash",
     "models": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-1.0-pro"]},
    {"id": "qwen", "name": "通义千问 (Qwen)", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "default_model": "qwen-turbo",
     "models": ["qwen-turbo", "qwen-plus", "qwen-max"]},
    {"id": "zhipu", "name": "智谱 AI (GLM)", "base_url": "https://open.bigmodel.cn/api/paas/v4", "default_model": "glm-4-flash",
     "models": ["glm-4-flash", "glm-4", "glm-4-plus"]},
]

def _get_provider(provider_id):
    for p in LLM_PROVIDERS:
        if p["id"] == provider_id:
            return p
    return LLM_PROVIDERS[0]

def get_current_char():
    char_id = st.session_state.get("current_char_id")
    return next((c for c in st.session_state.characters if c["id"] == char_id), None)

def get_api_info(char):
    """返回 (api_key, model, base_url)"""
    key = char.get("api_key") or st.session_state.user_profile.get("global_api_key", "")
    provider_id = st.session_state.user_profile.get("global_provider", "deepseek")
    provider = _get_provider(provider_id)
    mod = char.get("model") or st.session_state.user_profile.get("global_model") or provider["default_model"]
    return key, mod, provider["base_url"]

if "active_tab" not in st.session_state: st.session_state.active_tab = "Echoem"
if "view_mode" not in st.session_state: st.session_state.view_mode = "main"
if "reply_to_comment" not in st.session_state: st.session_state.reply_to_comment = {}

# ===================== 4. 朋友圈 AI 互动引擎 =====================

def generate_ai_comment(post_text):
    """当玩家发布动态时，随机让一个已创建的 AI 角色评论"""
    if not st.session_state.characters: return None
    
    # 随机选一个 AI 角色
    char = random.choice(st.session_state.characters)
    api_key, model, base_url = get_api_info(char)
    if not api_key: return None

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        prompt = f"你是{char['name']}。你的设定是：{char['persona']}。你的好友刚刚发了一条朋友圈：'{post_text}'。请以你的身份写一条简短、自然的评论（20字以内）。"
        resp = client.chat.completions.create(model=model, messages=[{"role":"system","content":prompt}])
        return {"char_id": char["id"], "name": char['name'], "content": resp.choices[0].message.content}
    except:
        return None

def handle_moment_interaction(moment, user_text, target_char_name=None, reply_to_name=None):
    """朋友圈评论区多轮对话：玩家与某个 AI 角色持续互动，可指定目标角色，并支持“XX 回复 YY”展示"""
    if not st.session_state.characters: 
        return

    char = None
    # 如果玩家显式选择了角色，就按名字精确匹配
    if target_char_name:
        char = next((c for c in st.session_state.characters if c["name"] == target_char_name), None)

    # 否则回退到之前的绑定逻辑
    if not char:
        thread_char_id = moment.get("thread_char_id")
        if thread_char_id:
            char = next((c for c in st.session_state.characters if c["id"] == thread_char_id), None)
        if not char:
            char = random.choice(st.session_state.characters)
            moment["thread_char_id"] = char["id"]

    api_key, model, base_url = get_api_info(char)
    if not api_key: 
        return

    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        sys_prompt = build_system_prompt(char, scene="moment")

        # 根据已有评论构造对话历史
        msgs = [{"role": "system", "content": sys_prompt}]
        # 添加上下文：玩家回复的内容
        if reply_to_name:
            msgs.append({"role": "user", "content": f"{st.session_state.user_profile['nickname']}回复{reply_to_name}：{user_text}"})
        else:
            msgs.append({"role": "user", "content": user_text})

        resp = client.chat.completions.create(model=model, messages=msgs)
        ai_reply = resp.choices[0].message.content or ""
        # 朋友圈评论保持一句为主，同时清理括号动作
        ai_reply = re.sub(r"[（(][^）)]*[）)]", "", ai_reply).strip()

        # 记录双方发言
        moment.setdefault("comments", [])
        # 存储时拆分为「昵称」+「回复内容」，展示时渲染为“{玩家} 回复 {角色}: 内容”
        display_text = f"回复{reply_to_name}：{user_text}" if reply_to_name else user_text
        moment["comments"].append({
            "name": st.session_state.user_profile["nickname"],
            "content": display_text,
            "role": "user"
        })
        # AI角色回复
        moment["comments"].append({
            "name": char["name"],
            "content": ai_reply,
            "role": "assistant"
        })
        
        # 立即保存数据，减少延迟
        save_cloud_data()
    except Exception as e:
        st.error(f"评论回复失败: {str(e)}")
        return

# ===================== 5. 页面渲染 =====================

def render_chat_list_page():
    st.markdown("<h3 style='text-align:center; margin:10px 0 20px 0; color:#111827;'>消息</h3>", unsafe_allow_html=True)

    # 类微信：按最近消息条数近似排序（真实项目可存 timestamp）
    def last_ts(c):
        return len(c.get("messages", []))

    display_chars = sorted(st.session_state.characters, key=last_ts, reverse=True)

    if not display_chars:
        st.markdown("""
        <div style='text-align:center; padding:60px 20px; color:#6B7280;'>
            <p style='font-size:16px;'>暂无聊天对象</p>
            <p style='font-size:14px; margin-top:8px;'>前往「通讯录」添加 AI 角色开始聊天吧</p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # 预先整理每个角色的最后一条消息，用于摘要展示
    last_msgs = {}
    for c in display_chars:
        msgs = c.get("messages", [])
        last = msgs[-1]["content"] if msgs else "暂无消息"
        last_msgs[c["id"]] = (last or "暂无消息").replace("\n", " ").strip()

    # 渲染消息列表：左侧纯展示，右侧小箭头按钮负责跳转
    for char in display_chars:
        last_msg = last_msgs.get(char["id"], "暂无消息")
        safe_name = html.escape(char["name"])
        safe_last_msg = html.escape(last_msg)
        avatar_html = get_avatar_html(char.get("avatar"))

        # 左右布局：左侧纯展示，右侧是紧凑的小箭头按钮
        chat_html = f"""
        <div class="chat-item">
            <div style="display: flex; align-items: center; width: 100%;">
                <div style="flex-shrink: 0; margin-right: 12px;">
                    {avatar_html}
                </div>
                <div style="flex-grow: 1; display: flex; flex-direction: column; justify-content: center; overflow: hidden;">
                    <div style="
                        font-size: 16px; 
                        font-weight: 500; 
                        color: #1a1a1a; 
                        line-height: 1.4;
                        margin-bottom: 2px;
                        white-space: nowrap;
                        overflow: hidden;
                        text-overflow: ellipsis;
                    ">
                        {safe_name}
                    </div>
                    <div style="
                        font-size: 13px; 
                        color: #8e8e93; 
                        white-space: nowrap; 
                        overflow: hidden; 
                        text-overflow: ellipsis;
                        line-height: 1.2;
                    ">
                        {safe_last_msg}
                    </div>
                </div>
            </div>
        </div>
        """

        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            st.markdown(chat_html, unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="chat-arrow" style="display:flex;align-items:center;justify-content:center;height:100%;">', unsafe_allow_html=True)
            if st.button("›", key=f"go_{char['id']}", help=f"与 {char['name']} 聊天", use_container_width=True):
                st.session_state.current_char_id = char["id"]
                st.session_state.view_mode = "chat"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

def render_chat_session():
    char = get_current_char()
    if not char: 
        st.session_state.view_mode = "main"
        st.rerun()
        return
        
    # 背景定制保留（优化背景透明度）
    if char.get('bg'):
        st.markdown(f'''
        <style>
        .stApp {{ 
            background-image: url("{char["bg"]}"); 
            background-size: cover; 
            background-attachment: fixed;
            background-opacity: 0.95;
        }}
        </style>''', unsafe_allow_html=True)

    # 聊天头部：更紧凑的顶部栏，左右为返回/设置按钮，中间为昵称与“对方正在输入中...”提示
    c1, c2, c3 = st.columns([0.8, 3.4, 0.8])
    with c1:
        st.button("⬅️", on_click=lambda: st.session_state.update({"view_mode":"main"}), type="tertiary", use_container_width=True)
    with c2:
        safe_char_name = safe_text(char.get("name", ""))
        st.markdown(
            f"<div style='text-align:center; margin:2px 0 0 0;'>"
            f"<div style='font-size:16px; font-weight:600; color:#111827; line-height:1.1;'>{safe_char_name}</div>"
            f"<div id='typing-indicator' style='font-size:11px; color:#9CA3AF; margin-top:1px; min-height:14px;'></div>"
            f"</div>",
            unsafe_allow_html=True
        )
        # 在昵称容器内部占位“对方正在输入中...”
        typing_placeholder = st.empty()
    with c3:
        st.button("⚙️", on_click=lambda: st.session_state.update({"view_mode":"edit_char"}), type="tertiary", use_container_width=True)
    
    # 更紧凑的分割线
    st.markdown(
        "<hr style='margin:4px 0 6px 0; border:none; border-top:1px solid #E5E7EB;'/>",
        unsafe_allow_html=True
    )
    
    # 消息循环
    user_av = get_avatar_display(st.session_state.user_profile.get("avatar"), "👤")
    char_av = get_avatar_display(char.get("avatar"), "🪽")
    
    # 空消息提示
    if not char.get("messages", []):
        safe_char_name_for_tip = safe_text(char.get("name", ""))
        st.markdown("""
        <div style='text-align:center; padding:80px 20px; color:#6B7280;'>
            <p style='font-size:16px;'>开始和 {char_name} 聊天吧</p>
        </div>
        """.format(char_name=safe_char_name_for_tip), unsafe_allow_html=True)
    
    for idx, m in enumerate(char.get("messages", [])):
        msg_type = m.get("type", "text")
        is_u = m["role"] == "user"
        av = user_av if is_u else char_av
        
        if isinstance(av, str) and av.startswith("http"):
            av_html = f"<img src='{av}' style='width:100%;height:100%;object-fit:cover;'>"
        else:
            av_html = av

        if msg_type == "transfer":
            amount = m.get("amount", 0)
            note = m.get("note", "")
            status = m.get("status", "未收款")
            direction = m.get("direction", "to_char")
            # 根据方向/角色决定文案
            if direction == "to_user" or (not direction and not is_u):
                who = "TA 向你转账"
            else:
                who = "你向 TA 转账"
            card_cls = "transfer-card received" if status == "已收款" else "transfer-card"

            safe_who = safe_text(who)
            safe_note = safe_text(note)
            safe_status = safe_text(status)

            # 和普通气泡保持一致：自己在右、对方在左
            if is_u:
                # 自己发起的转账：卡片靠右，头像在右
                html = f"""
<div class="chat-bubble-row me">
  <div class="chat-bubble-content" style="background:transparent; padding:0; border-radius:0;">
    <div class="{card_cls}">
      <div class="transfer-title">{safe_who}</div>
      <div class="transfer-amount">¥ {amount}</div>
      <div class="transfer-note">{safe_note}</div>
      <div class="transfer-status">{safe_status}</div>
    </div>
  </div>
  <div class="chat-bubble-avatar">{av_html}</div>
</div>
"""
            else:
                # 对方转账：头像在左，卡片在右
                html = f"""
<div class="chat-bubble-row">
  <div class="chat-bubble-avatar">{av_html}</div>
  <div class="chat-bubble-content" style="background:transparent; padding:0; border-radius:0;">
    <div class="{card_cls}">
      <div class="transfer-title">{safe_who}</div>
      <div class="transfer-amount">¥ {amount}</div>
      <div class="transfer-note">{safe_note}</div>
      <div class="transfer-status">{safe_status}</div>
    </div>
  </div>
</div>
"""
            st.markdown(html, unsafe_allow_html=True)
            # 仅当是 TA 向你转账且当前状态为“未收款”时，展示收款交互
            if not is_u and direction == "to_user" and status != "已收款":
                # 优化收款按钮样式
                col = st.columns([1, 2, 1])
                with col[1]:
                    if st.button("点击收款", key=f"recv_{char['id']}_{idx}", use_container_width=True):
                        m["status"] = "已收款"
                        save_cloud_data()
                        st.rerun()
            continue

        # 普通文本消息 - 头像与消息内容垂直居中
        if is_u:
            safe_content = safe_text(m.get("content", ""))
            html = f"""
<div class="chat-bubble-row me">
  <div class="chat-bubble-content chat-bubble-me">{safe_content}</div>
  <div class="chat-bubble-avatar">{av_html}</div>
</div>
"""
        else:
            safe_content = safe_text(m.get("content", ""))
            html = f"""
<div class="chat-bubble-row">
  <div class="chat-bubble-avatar">{av_html}</div>
  <div class="chat-bubble-content chat-bubble-other">{safe_content}</div>
</div>
"""
        st.markdown(html, unsafe_allow_html=True)

    # 优化输入框位置和样式
    prompt = st.chat_input("发消息...", key="chat_input")
    if prompt:
        # 玩家消息也清理括号动作，防止引导对话变成“动作剧本”
        clean = re.sub(r"[（(][^）)]*[）)]", "", prompt).strip() or prompt
        char["messages"].append({"role": "user", "content": clean})
        # 立即保存并刷新，减少延迟
        save_cloud_data()
        st.rerun()

    if char["messages"] and char["messages"][-1]["role"] == "user":
        # 将“对方正在输入中...”提示固定在顶部昵称区域下方
        with typing_placeholder:
            with st.spinner("对方正在输入中..."):
                key, mod, base_url = get_api_info(char)
                if not key: 
                    st.error("缺失 API Key，请前往「我」页面配置全局 API Key 或为该角色单独配置", icon="❌")
                    return
                try:
                    client = OpenAI(api_key=key, base_url=base_url)
                    sys_prompt = build_system_prompt(char, scene="chat")
                    
                    # 使用记忆库的上下文（最近10条 + 核心记忆已在system prompt中）
                    context_msgs = get_context_messages(char)
                    
                    resp = client.chat.completions.create(
                        model=mod,
                        messages=[{"role": "system", "content": sys_prompt}] + context_msgs
                    )
                    raw = resp.choices[0].message.content or ""
                    
                    # 更新记忆库（在显示之前完成）
                    user_msg = char["messages"][-1]["content"]
                    update_memory_bank(char, user_msg, raw)
                    
                    # 支持转账写法：
                    # 1）标准指令：转账卡|金额=XXX|备注=...
                    # 2）拆成多条：转账卡｜金额=XXX｜备注=...
                    # 3）自然语言 fallback：转账 10 元。备注：XXX
                    pending_transfer = None
                    for seg in re.split(r"[｜|\n]+", raw):
                        seg = seg.strip()
                        if not seg:
                            continue

                        # 情况 A：一行写完的转账指令
                        if seg.startswith("转账卡|"):
                            try:
                                amt_match = re.search(r"金额=([0-9]+(?:\.[0-9]+)?)", seg)
                                note_match = re.search(r"备注=([^|]+)", seg)
                                amount = float(amt_match.group(1)) if amt_match else 0.0
                                note = note_match.group(1).strip() if note_match else ""
                            except Exception:
                                amount, note = 0.0, ""
                            desc = f"转账 {amount} 元。备注：{note}" if amount else (note or "转账")
                            clean_desc = re.sub(r"[（(][^）)]*[）)]", "", desc).strip() or desc
                            char["messages"].append({
                                "role": "assistant",
                                "content": clean_desc,
                                "type": "transfer",
                                "amount": round(float(amount), 2),
                                "note": note,
                                "direction": "to_user",
                                "status": "未收款"
                            })
                            continue

                        # 情况 B：拆成多条的转账指令（转账卡｜金额=XXX｜备注=...）
                        if seg == "转账卡":
                            pending_transfer = {"amount": None, "note": ""}
                            continue
                        if seg.startswith("金额="):
                            if pending_transfer is None:
                                pending_transfer = {"amount": None, "note": ""}
                            try:
                                pending_transfer["amount"] = float(seg.split("=", 1)[1])
                            except Exception:
                                pending_transfer["amount"] = 0.0
                            continue

                        # 情况 C：自然语言格式的转账描述（兜底）
                        # 例如：转账 10.0 元。备注：买骨头
                        if seg.startswith("转账") and "备注" in seg:
                            try:
                                m_amount = re.search(r"转账\s*([0-9]+(?:\.[0-9]+)?)", seg)
                                m_note = re.search(r"备注[:：]\s*(.+)", seg)
                                amount = float(m_amount.group(1)) if m_amount else 0.0
                                note = m_note.group(1).strip() if m_note else ""
                            except Exception:
                                amount, note = 0.0, ""
                            desc = f"转账 {amount} 元。备注：{note}" if amount else (note or "转账")
                            clean_desc = re.sub(r"[（(][^）)]*[）)]", "", desc).strip() or desc
                            char["messages"].append({
                                "role": "assistant",
                                "content": clean_desc,
                                "type": "transfer",
                                "amount": round(float(amount), 2),
                                "note": note,
                                "direction": "to_user",
                                "status": "未收款"
                            })
                            continue
                        if seg.startswith("备注="):
                            if pending_transfer is None:
                                pending_transfer = {"amount": None, "note": ""}
                            pending_transfer["note"] = seg.split("=", 1)[1].strip()
                            # 到这里视为信息齐全，可以落地一张转账卡
                            amount = pending_transfer.get("amount") or 0.0
                            note = pending_transfer.get("note", "")
                            desc = f"转账 {amount} 元。备注：{note}" if amount else (note or "转账")
                            clean_desc = re.sub(r"[（(][^）)]*[）)]", "", desc).strip() or desc
                            char["messages"].append({
                                "role": "assistant",
                                "content": clean_desc,
                                "type": "transfer",
                                "amount": round(float(amount), 2),
                                "note": note,
                                "direction": "to_user",
                                # 默认均为“未收款”，等待玩家点击收款后再变为“已收款”
                                "status": "未收款"
                            })
                            pending_transfer = None
                            continue

                        # 普通文本消息：清理括号动作
                        seg_clean = re.sub(r"[（(][^）)]*[）)]", "", seg).strip()
                        if not seg_clean:
                            continue
                        char["messages"].append({"role": "assistant", "content": seg_clean})
                    # 立即保存并刷新，减少延迟
                    save_cloud_data()
                    st.rerun()
                except Exception as e:
                    st.error(f"对话出错：{str(e)}", icon="❌")
                    return

def render_edit_persona():
    char = get_current_char()
    if not char: 
        st.session_state.view_mode = "main"
        st.rerun()
        return
        
    st.markdown(f"<h3 style='margin:10px 0 20px 0; color:#111827;'>编辑 {char['name']}</h3>", unsafe_allow_html=True)
    
    # 优化表单布局
    col1, col2 = st.columns(2)
    with col1:
        char['name'] = st.text_input("昵称", char['name'], placeholder="请输入角色昵称")
    with col2:
        char['api_key'] = st.text_input("角色专属 API Key", char.get('api_key', ''), type="password", placeholder="留空使用全局 API Key")
    
    # 模型：留空使用全局，也可从当前全局提供商中选
    provider_id = st.session_state.user_profile.get("global_provider", "deepseek")
    provider = _get_provider(provider_id)
    model_options = [""] + provider["models"]
    current_char_model = char.get("model") or ""
    if current_char_model and current_char_model not in model_options:
        model_options = [current_char_model] + [o for o in model_options if o]
    model_index = model_options.index(current_char_model) if current_char_model in model_options else 0
    char["model"] = st.selectbox("模型（选填，留空用全局）", options=model_options, index=model_index, format_func=lambda x: x or "使用全局设置")
    
    char['persona'] = st.text_area("人设 (Prompt)", char['persona'], height=150, placeholder="请详细描述角色的性格、语气、背景等")
    char['memory'] = st.text_area("核心记忆（手动设置）", char.get('memory',''), height=100, placeholder="角色需要记住的关键信息（AI自动提取的记忆会显示在下方）")
    
    # 显示AI自动维护的记忆库
    memory_bank = char.get("memory_bank", {})
    core_memories = memory_bank.get("core_memories", [])
    recent_context = memory_bank.get("recent_context", [])
    
    if core_memories or recent_context:
        st.markdown("---")
        st.subheader("🧠 AI 记忆库", divider="gray")
        
        if core_memories:
            st.markdown(f'<div class="memory-bank-info">💡 AI 已自动提取 {len(core_memories)} 条核心记忆</div>', unsafe_allow_html=True)
            for i, mem in enumerate(core_memories, 1):
                safe_mem = safe_text(mem)
                st.markdown(f'<div class="memory-item">{i}. {safe_mem}</div>', unsafe_allow_html=True)
                        
        if recent_context:
            with st.expander(f"📝 最近 {len(recent_context)} 条对话上下文（点击查看）"):
                for ctx in recent_context:
                    role = "👤" if ctx["role"] == "user" else "🪽"
                    content = ctx.get("content", "")[:50]
                    st.markdown(f"{role} {content}...")
    
    # 头像/背景定制保留（优化布局）
    st.markdown("<div style='margin:20px 0;'>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("头像设置", divider="gray")
        # 预览当前头像
        current_av = get_avatar_display(char.get("avatar"), "🪽")
        if isinstance(current_av, str) and current_av.startswith("http"):
            st.image(current_av, width=80)
        else:
            st.markdown(f"<div style='width:80px;height:80px;border-radius:50%;background:#F3F4F6;display:flex;align-items:center;justify-content:center;font-size:40px;'>{current_av}</div>", unsafe_allow_html=True)
        
        new_av = st.file_uploader("更换头像", type=['png','jpg'], key="avatar_upload")
        if st.button("保存头像", key="save_avatar", use_container_width=True):
            if new_av: 
                char['avatar'] = process_uploaded_image(new_av, (100,100))
                save_cloud_data()
                st.success("头像保存成功！", icon="✅")
                time.sleep(1)
                st.rerun()
    
    with col2:
        st.subheader("背景设置", divider="gray")
        # 预览当前背景
        if char.get('bg'):
            st.image(char['bg'], width=150)
        else:
            st.markdown("<p style='color:#6B7280;'>暂无背景图</p>", unsafe_allow_html=True)
        
        new_bg = st.file_uploader("更换背景图", type=['png','jpg'], key="bg_upload")
        if st.button("保存背景", key="save_bg", use_container_width=True):
            if new_bg: 
                char['bg'] = process_uploaded_image(new_bg, (1080,1920))
                save_cloud_data()
                st.success("背景保存成功！", icon="✅")
                time.sleep(1)
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 优化按钮布局
    col1, col2 = st.columns(2)
    with col1:
        if st.button("完成并返回", use_container_width=True, type="primary"): 
            st.session_state.view_mode = "chat"
            st.rerun()
    with col2:
        if st.button("删除角色", use_container_width=True, type="secondary"): 
            # 二次确认
            if st.checkbox("确认删除该角色（不可恢复）"):
                st.session_state.characters.remove(char)
                save_cloud_data()
                st.session_state.view_mode = "main"
                st.success("角色已删除", icon="✅")
                time.sleep(1)
                st.rerun()

def render_moments_page():
    st.markdown("<h3 style='text-align:center; margin:10px 0 20px 0; color:#111827;'>发现</h3>", unsafe_allow_html=True)
    
    # 优化发布动态区域
    with st.expander("📷 发布新动态", expanded=False):
        with st.form("new_post", clear_on_submit=True):
            txt = st.text_area("这一刻的想法...", height=100, placeholder="分享你的心情、想法或故事...")
            img = st.file_uploader("添加配图（可选）", type=['png','jpg','jpeg'])
            col1, col2 = st.columns([4,1])
            with col1:
                submit = st.form_submit_button("发表", type="primary", use_container_width=True)
            with col2:
                cancel = st.form_submit_button("取消", use_container_width=True)
            
            if submit and txt.strip():
                new_post = {
                    "id": uuid4().hex, 
                    "text": txt, 
                    "image": process_uploaded_image(img, (800,800)), 
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M"), 
                    "comments": [],
                    "likes": 0,
                    "liked": False
                }
                # AI 互动逻辑插入：首条评论 & 绑定线程角色
                ai_reply = generate_ai_comment(txt)
                if ai_reply: 
                    new_post["thread_char_id"] = ai_reply["char_id"]
                    new_post["comments"].append({
                        "name": ai_reply["name"],
                        "content": ai_reply["content"],
                        "role": "assistant"
                    })
                st.session_state.moments.append(new_post)
                save_cloud_data()
                st.success("发布成功！", icon="✅")
                time.sleep(1)
                st.rerun()
            elif submit and not txt.strip():
                st.warning("动态内容不能为空", icon="⚠️")

    # 展示朋友圈动态
    moments = list(reversed(st.session_state.moments))[:20]
    
    if not moments:
        st.markdown("""
        <div style='text-align:center; padding:60px 20px; color:#6B7280;'>
            <p style='font-size:16px;'>暂无动态</p>
            <p style='font-size:14px; margin-top:8px;'>发布一条动态，和 AI 好友互动吧</p>
        </div>
        """, unsafe_allow_html=True)
        return

    for m in moments:
        # 兼容旧数据：如果没有 id，则补一个
        if "id" not in m:
            m["id"] = uuid4().hex
        m_id = m["id"]

        # 兼容点赞数据：likes 可能是 list（旧数据谁点赞）或 int（点赞数），统一为 int
        if isinstance(m.get("likes"), list):
            liked_list = m["likes"]
            m["likes"] = len(liked_list)
            m["liked"] = st.session_state.username in liked_list
        if not isinstance(m.get("likes"), int):
            m["likes"] = 0
        m.setdefault("liked", False)

        st.markdown('<div class="moment-card">', unsafe_allow_html=True)
        # 动态发布者信息
        safe_poster_name = safe_text(st.session_state.user_profile.get('nickname', ''))
        st.markdown(f"<span style='color:#3B82F6; font-weight:600; font-size:16px;'>{safe_poster_name}</span>", unsafe_allow_html=True)
        # 动态内容
        safe_text_content = safe_text(m.get('text',''))
        st.markdown(f"<p style='margin:12px 0; line-height:1.5; color:#111827;'>{safe_text_content}</p>", unsafe_allow_html=True)
        # 动态图片
        if m.get("image"):
            st.image(m["image"], use_column_width=True)
        # 动态时间
        st.markdown(f"<small style='color:#9CA3AF;'>{m.get('time','')}</small>", unsafe_allow_html=True)

        # 互动工具栏（仅点赞）- 水平齐平
        st.markdown('<div class="interaction-toolbar">', unsafe_allow_html=True)
        like_label = f"❤️ {m['likes']}" if m['liked'] else f"🤍 {m['likes']}"
        if st.button(like_label, key=f"like_{m_id}", use_container_width=False):
            # 乐观更新点赞状态
            if m["liked"]:
                m["liked"] = False
                m["likes"] = max(0, m["likes"] - 1)
            else:
                m["liked"] = True
                m["likes"] += 1
            save_cloud_data()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

        # 评论展示区
        reply_key = f"reply_to_{m_id}"
        # 初始化回复状态
        if reply_key not in st.session_state:
            st.session_state[reply_key] = ""
        
        if m.get("comments"):
            st.markdown('<div class="comment-area">', unsafe_allow_html=True)
            for idx, c in enumerate(m["comments"]):
                raw_name = c.get("name", "") or ""
                raw_content = (c.get("content") or "").strip()
                # 兼容旧数据：如果内容以“{name}回复”开头，去掉前面的名字，避免“双重名字”
                if c.get("role") == "user" and raw_content.startswith(f"{raw_name}回复"):
                    raw_content = raw_content[len(raw_name):].lstrip()

                name = html.escape(raw_name)
                content = html.escape(raw_content)

                comment_key = f"comment_click_{m_id}_{idx}"
                col_comment, col_reply = st.columns([5, 1])
                with col_comment:
                    st.markdown(
                        f'<div class="comment-item"><span class="comment-user">{name}</span>{content}</div>',
                        unsafe_allow_html=True
                    )
                with col_reply:
                    if st.button("回复", key=comment_key):
                        st.session_state[reply_key] = name
                        st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        # 评论输入框：点击评论后显示，输入框+发送按钮横向布局
        reply_to_name = st.session_state.get(reply_key, "")
        input_key = f"cm_{m_id}"
        # 如果上一轮发送后打了清空标记，先在本轮渲染前清理输入框的值
        if st.session_state.get(f"clear_{input_key}", False):
            st.session_state.pop(input_key, None)
            st.session_state[f"clear_{input_key}"] = False

        if reply_to_name or st.session_state.get(f"show_input_{m_id}", False):
            st.markdown('<div class="comment-input-container">', unsafe_allow_html=True)
            placeholder = f"回复 {reply_to_name} ..." if reply_to_name else "发表评论..."
            col1, col2 = st.columns([4,1])
            with col1:
                # 当前 Streamlit 版本不支持 class_，仅隐藏 label
                user_q = st.text_input(placeholder, key=input_key, label_visibility="collapsed")
            with col2:
                send_btn = st.button("发送", key=f"cm_btn_{m_id}", use_container_width=True)
            
            if send_btn and user_q.strip():
                # 默认优先与被回复的AI角色互动
                target_name = reply_to_name if reply_to_name else None
                if target_name and not any(c for c in st.session_state.characters if c["name"] == target_name):
                    # 如果被回复的不是AI角色，找当前动态绑定的AI角色
                    ai_names = [c.get("name") for c in m.get("comments", []) if c.get("role") == "assistant"]
                    if ai_names:
                        target_name = ai_names[0]
                
                handle_moment_interaction(m, user_q.strip(), target_char_name=target_name, reply_to_name=reply_to_name)
                # 清空回复对象和输入框
                st.session_state[reply_key] = ""
                st.session_state[f"clear_{input_key}"] = True
                save_cloud_data()
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

def render_contacts_page():
    st.markdown("<h3 style='text-align:center; margin:10px 0 20px 0; color:#111827;'>通讯录</h3>", unsafe_allow_html=True)
    
    # 展示现有角色
    if st.session_state.characters:
        st.markdown("<p style='color:#6B7280; margin:0 0 10px 10px;'>我的 AI 好友</p>", unsafe_allow_html=True)
        for char in st.session_state.characters:
            st.markdown('<div style="padding:10px 0; border-bottom:1px solid #F3F4F6;">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 3, 2])
            with col1:
                av = get_avatar_display(char.get("avatar"), "🪽")
                if isinstance(av, str) and av.startswith("http"):
                    st.markdown(f'<img src="{av}" style="width:40px;height:40px;border-radius:50%;object-fit:cover;">', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="width:40px;height:40px;border-radius:50%;background:#F3F4F6;display:flex;align-items:center;justify-content:center;font-size:20px;">{av}</div>', unsafe_allow_html=True)
            with col2:
                safe_name = safe_text(char.get("name", ""))
                st.markdown(f"<b style='font-size:15px; color:#111827;'>{safe_name}</b>", unsafe_allow_html=True)
            with col3:
                if st.button("开始聊天", key=f"cont_{char['id']}", use_container_width=True, type="primary"): 
                    st.session_state.current_char_id = char['id']
                    st.session_state.view_mode = "chat"
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style='text-align:center; padding:40px 20px; color:#6B7280;'>
            <p style='font-size:16px;'>暂无 AI 好友</p>
            <p style='font-size:14px; margin-top:8px;'>添加一个 AI 角色开始聊天吧</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # 添加新角色
    with st.expander("➕ 添加新 AI 角色", expanded=True):
        with st.form("new_char", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                n = st.text_input("角色名称", placeholder="给你的 AI 好友起个名字")
            with col2:
                _provider = _get_provider(st.session_state.user_profile.get("global_provider", "deepseek"))
                _model_opts = [""] + _provider["models"]
                mod = st.selectbox("模型（选填）", options=_model_opts, format_func=lambda x: x or "使用全局设置")
                mod = mod or None  # 留空时不用传 model，用全局
            
            p = st.text_area("角色人设", height=150, placeholder="详细描述角色的性格、语气、背景、说话方式等\n例如：温柔的邻家姐姐，说话亲切，喜欢用叠词，关心人的感受...")
            mem = st.text_area("核心记忆（选填）", height=80, placeholder="角色需要记住的关键信息\n例如：记住我的生日是10月1日，喜欢吃草莓蛋糕...")
            
            if st.form_submit_button("创建角色", type="primary", use_container_width=True):
                if n and p:
                    new_char = {
                        "id":uuid4().hex, 
                        "name":n, 
                        "persona":p, 
                        "memory":mem,
                        "model":mod,
                        "api_key":"",
                        "messages":[], 
                        "avatar":None, 
                        "bg":None,
                        "memory_bank": {
                            "core_memories": [],
                            "recent_context": []
                        }
                    }
                    st.session_state.characters.append(new_char)
                    save_cloud_data()
                    st.success(f"成功创建 {n}！", icon="✅")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("角色名称和人设不能为空", icon="⚠️")

def render_profile_page():
    st.markdown("<h3 style='text-align:center; margin:10px 0 20px 0; color:#111827;'>个人中心</h3>", unsafe_allow_html=True)
    
    prof = st.session_state.user_profile

    raw_nickname = prof.get("nickname", "未设置")
    safe_nickname = safe_text(raw_nickname)
    safe_username = safe_text(st.session_state.username)
    
    # 优化个人信息展示
    st.markdown("<div style='text-align:center; margin-bottom:30px;'>", unsafe_allow_html=True)
    av_display = get_avatar_display(prof.get("avatar"), "")
    if av_display:
        if isinstance(av_display, str) and av_display.startswith("http"):
            st.markdown(f"<img src='{av_display}' style='width:90px;height:90px;border-radius:50%;object-fit:cover;border:3px solid #F3F4F6;'>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='width:90px;height:90px;border-radius:50%;background:#F3F4F6;display:flex;align-items:center;justify-content:center;font-size:40px;margin:0 auto;'>{av_display or '👤'}</div>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='margin:10px 0; color:#111827;'>{safe_nickname}</h4>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#6B7280; font-size:13px;'>账号：{safe_username}（不可修改）</p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 个人设置表单
    with st.form("profile_form", clear_on_submit=False):
        st.subheader("基本设置", divider="gray")
        prof["nickname"] = st.text_input("昵称", prof["nickname"], placeholder="修改你的显示昵称")
        
        # 头像上传
        st.markdown("<p style='margin:15px 0 5px 0; color:#374151;'>我的头像</p>", unsafe_allow_html=True)
        new_av = st.file_uploader("上传新头像", type=['png','jpg','jpeg'], label_visibility="collapsed")
        if new_av:
            av_url = process_uploaded_image(new_av, (200, 200))
            if av_url:
                prof["avatar"] = av_url
                st.success("头像已更新！", icon="✅")
        
        st.subheader("AI 设置", divider="gray")
        # 选择 LLM 提供商
        provider_options = [p["name"] for p in LLM_PROVIDERS]
        current_provider_id = prof.get("global_provider", "deepseek")
        current_provider = _get_provider(current_provider_id)
        current_provider_index = next((i for i, p in enumerate(LLM_PROVIDERS) if p["id"] == current_provider_id), 0)
        selected_name = st.selectbox(
            "选择模型服务",
            options=provider_options,
            index=current_provider_index,
            help="选择 DeepSeek、Kimi、GPT、Gemini 等（需对应 API Key）"
        )
        selected_provider = next((p for p in LLM_PROVIDERS if p["name"] == selected_name), LLM_PROVIDERS[0])
        prof["global_provider"] = selected_provider["id"]
        # 选择该提供商下的模型
        model_options = selected_provider["models"]
        current_model = prof.get("global_model") or selected_provider["default_model"]
        if current_model not in model_options:
            model_options = [current_model] + model_options
        model_index = model_options.index(current_model) if current_model in model_options else 0
        prof["global_model"] = st.selectbox(
            "选择模型",
            options=model_options,
            index=model_index,
            help="不同服务商的模型名称不同，选错可能无法调用"
        )
        prof["global_api_key"] = st.text_input(
            "API Key", 
            prof.get("global_api_key",""), 
            type="password",
            placeholder=f"{selected_provider['name']} API Key（所有角色默认使用）"
        )
        prof["self_persona"] = st.text_area(
            "我的人设", 
            prof.get("self_persona", ""), 
            height=120,
            placeholder="描述你的身份、性格、喜好等，让 AI 更了解你\n例如：25岁的程序员，喜欢旅行和美食，性格开朗..."
        )
        
        # 密码修改功能
        st.subheader("密码修改", divider="gray")
        old_pwd = st.text_input("原密码", type="password", placeholder="请输入当前密码")
        new_pwd = st.text_input("新密码", type="password", placeholder="请设置新密码")
        
        # 按钮区域
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.form_submit_button("保存设置", use_container_width=True, type="primary"): 
                save_cloud_data()
                st.success("设置已同步到云端！", icon="✅")
        with col2:
            if st.form_submit_button("修改密码", use_container_width=True):
                if not old_pwd or not new_pwd:
                    st.warning("原密码和新密码都不能为空", icon="⚠️")
                else:
                    success, msg = update_password(st.session_state.username, old_pwd, new_pwd)
                    if success:
                        st.success(msg, icon="✅")
                        time.sleep(2)
                    else:
                        st.error(msg, icon="❌")
        with col3:
            if st.form_submit_button("退出登录", use_container_width=True, type="secondary"): 
                st.session_state.clear()
                st.rerun()

# ===================== 6. 路由与固定导航 =====================

# 确保在所有页面都渲染底部导航栏
main_content_container = st.container()

with main_content_container:
    if st.session_state.view_mode == "chat":
        render_chat_session()
    elif st.session_state.view_mode == "edit_char":
        render_edit_persona()
    else:
        # 页面主体内容
        if st.session_state.active_tab == "Echoem": 
            render_chat_list_page()
        elif st.session_state.active_tab == "通讯录": 
            render_contacts_page()
        elif st.session_state.active_tab == "发现": 
            render_moments_page()
        elif st.session_state.active_tab == "我": 
            render_profile_page()

# 固定底部导航栏渲染（确保在所有页面都显示）
st.markdown('<div class="nav-wrapper">', unsafe_allow_html=True)
cols = st.columns(4)
nav_items = [("💬 消息", "Echoem"), ("👥 通讯录", "通讯录"), ("🌍 发现", "发现"), ("👤 我", "我")]
for i, (label, tab_name) in enumerate(nav_items):
    with cols[i]:
        if st.button(
            label, 
            key=f"nav_{tab_name}", 
            use_container_width=True, 
            type="primary" if st.session_state.active_tab == tab_name else "tertiary"
        ):
            st.session_state.active_tab = tab_name
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)