import streamlit as st
from openai import OpenAI
import time
import re
import json
import os
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
import httpx

# ===================== 0. 全局设置 =====================
st.set_page_config(page_title="Narratio", page_icon="📜", layout="wide", initial_sidebar_state="collapsed")

# 关键修复：使用 JavaScript 强制设置 viewport（因为 Streamlit 不允许注入 head meta）
st.markdown("""
<script>
    // 关键修复1：强制viewport，优先级最高（覆盖Streamlit原生）
    const viewport = document.querySelector('meta[name="viewport"]');
    if (viewport) {
        viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
    } else {
        const meta = document.createElement('meta');
        meta.name = 'viewport';
        meta.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no';
        document.head.insertBefore(meta, document.head.firstChild);
    }

    // 关键修复2：页面加载后立即强制重绘，解决Streamlit布局延迟溢出
    window.addEventListener('load', () => {
        document.body.style.width = '100vw';
        document.body.style.overflowX = 'hidden';
        document.body.classList.remove('chat-view'); // 非聊天页时移除，由聊天页再添加
        const horizontalBlocks = document.querySelectorAll('[data-testid="stHorizontalBlock"]');
        horizontalBlocks.forEach(blk => {
            blk.style.width = '100vw';
            blk.style.overflowX = 'hidden';
        });
    });

    // 监听窗口大小变化，实时约束
    window.addEventListener('resize', () => {
        document.body.style.width = '100vw';
        document.body.style.overflowX = 'hidden';
    });
</script>
<style>
    /* ========== 1. 基础重置 - 极简 Ins 风格 ========== */
    html, body {
        width: 100vw !important;
        max-width: 100vw !important;
        overflow-x: hidden !important;
        margin: 0 !important;
        padding: 0 !important;
        box-sizing: border-box !important;
        background-color: #FAFAFA !important;
    }
    * { box-sizing: border-box !important; max-width: 100vw !important; }
    [data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer { display: none !important; }
    .block-container { 
        padding-top: 0 !important; 
        padding-bottom: 0 !important; 
        max-width: 100vw !important;
        width: 100% !important;
        margin: 0 auto !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
    }
    .stApp { 
        background-color: #FAFAFA !important; 
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        width: 100vw !important;
        max-width: 100vw !important;
        overflow-x: hidden !important;
    }
    /* 2. 导航栏 - 白底细边 */
    .nav-top-bar { 
        padding: 12px 16px !important;
        background: #FFFFFF !important;
        border-bottom: 1px solid #DBDBDB !important;
        margin-bottom: 0 !important;
    }
    .nav-top-title { 
        font-size: 1.15rem !important; 
        color: #000000 !important; 
        font-weight: 600 !important; 
        text-align: center;
    }
    /* 3. 聊天详情页顶栏 - 单行横向，贴合聊天习惯，移动端不纵向堆叠 */
    .chat-header-marker ~ [data-testid="stVerticalBlock"] [data-testid="stHorizontalBlock"]:first-child,
    .chat-header-marker + [data-testid="stVerticalBlock"] [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 0 !important;
    }
    .chat-header-marker ~ [data-testid="stVerticalBlock"] [data-testid="stHorizontalBlock"] [data-testid="column"],
    .chat-header-marker + [data-testid="stVerticalBlock"] [data-testid="stHorizontalBlock"] [data-testid="column"] {
        min-width: 0 !important;
    }
    .chat-header-marker ~ [data-testid="stVerticalBlock"] [data-testid="stHorizontalBlock"] [data-testid="column"]:first-child,
    .chat-header-marker ~ [data-testid="stVerticalBlock"] [data-testid="stHorizontalBlock"] [data-testid="column"]:last-child,
    .chat-header-marker + [data-testid="stVerticalBlock"] [data-testid="stHorizontalBlock"] [data-testid="column"]:first-child,
    .chat-header-marker + [data-testid="stVerticalBlock"] [data-testid="stHorizontalBlock"] [data-testid="column"]:last-child {
        flex: 0 0 44px !important;
        max-width: 48px !important;
    }
    .chat-header-marker ~ [data-testid="stVerticalBlock"] [data-testid="stHorizontalBlock"] [data-testid="column"]:nth-child(2),
    .chat-header-marker + [data-testid="stVerticalBlock"] [data-testid="stHorizontalBlock"] [data-testid="column"]:nth-child(2) {
        flex: 1 1 auto !important;
        overflow: hidden !important;
    }
    .chat-header-center-wrap { display: flex !important; align-items: center !important; justify-content: center !important; flex-direction: column !important; gap: 0 !important; min-height: 40px !important; text-align: center !important; overflow: hidden !important; }
    .chat-header-center-wrap .chat-name { font-size: 15px !important; font-weight: 600 !important; color: #000000 !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; line-height: 1.2 !important; }
    .chat-header-center-wrap .chat-typing { font-size: 11px !important; color: #8E8E8E !important; min-height: 14px !important; line-height: 1.2 !important; }
    body.chat-view .block-container [data-testid="stHorizontalBlock"]:first-of-type { flex-wrap: nowrap !important; align-items: center !important; gap: 0 !important; }
    body.chat-view .block-container [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"]:first-child,
    body.chat-view .block-container [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"]:last-child { flex: 0 0 44px !important; max-width: 48px !important; min-width: 0 !important; }
    body.chat-view .block-container [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"]:nth-child(2) { flex: 1 1 auto !important; min-width: 0 !important; overflow: hidden !important; }
    /* 3. 聊天气泡 - Ins 风格：对方黑底白字，我方白底黑框 */
    .chat-bubble-row { 
        display: flex !important; 
        margin-bottom: 20px !important; 
        align-items: flex-end !important;
        position: relative;
        width: 100% !important;
        animation: bubbleFade 0.25s ease !important;
    }
    @keyframes bubbleFade { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
    .chat-bubble-row.me { justify-content: flex-end; }
    .chat-bubble-avatar { 
        width: 38px !important;
        height: 38px !important;
        border-radius: 50%;
        overflow: hidden; 
        margin: 0 10px !important;
        flex-shrink: 0; 
        background-color: #EFEFEF;
        display: flex; 
        align-items: center; 
        justify-content: center; 
        font-size: 18px !important;
        border: 1px solid #EFEFEF;
    }
    .chat-bubble-avatar img { width: 100%; height: 100%; object-fit: cover; }
    .chat-bubble-content { 
        max-width: 72% !important;
        padding: 12px 18px !important;
        border-radius: 20px !important;
        font-size: 15px !important;
        line-height: 1.5;
        position: relative;
        word-wrap: break-word !important;
        word-break: break-word !important;
    }
    .chat-bubble-other { 
        background-color: #000000 !important; 
        color: #FFFFFF !important; 
        border: 1px solid #000000 !important; 
        border-bottom-left-radius: 4px !important;
    }
    .chat-bubble-me { 
        background-color: #FFFFFF !important; 
        color: #000000 !important;
        border: 1px solid #000000 !important; 
        border-bottom-right-radius: 4px !important;
    }
    .message-time { font-size: 11px !important; color: #8E8E8E !important; margin-top: 6px !important; text-align: right !important; }
    .chat-bubble-row.me .message-time { color: #8E8E8E !important; }
    .chat-bubble-row:not(.me) .message-time { color: rgba(255,255,255,0.6) !important; }
    
    /* 4. 朋友圈 / 发现 */
    .moment-card { 
        background: #FFFFFF !important; 
        padding: 20px !important; 
        border-radius: 0; 
        margin-bottom: 12px !important; 
        border-bottom: 1px solid #EFEFEF;
        border-top: 1px solid #EFEFEF;
        width: 100% !important;
    }
    .comment-area { 
        background: transparent; 
        padding: 6px 0 0 0 !important; 
        margin-top: 6px !important; 
        font-size: 13px !important;
        width: 100% !important;
    }
    .comment-item { 
        padding: 6px 0 !important; 
        border-bottom: 1px solid #EFEFEF;
        line-height: 1.4;
        word-wrap: break-word !important;
    }
    .comment-item:last-child { border-bottom: none; }
    .comment-user { color: #262626; font-weight: 600; margin-right: 6px; }
    /* 5. 通用按钮 - 极简 */
    .stButton>button { 
        border-radius: 8px !important; 
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 8px 12px !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: #000000 !important;
        transition: background 0.2s ease !important;
    }
    .stButton>button:hover { background-color: #FAFAFA !important; }
    /* 6. 转账卡片 - Ins 黑/白主题 */
    .transfer-card {
        background: #000000 !important;
        border-radius: 16px !important;
        padding: 12px 16px !important;
        min-width: 200px !important;
        max-width: 280px !important;
        color: #FFFFFF !important;
        display: flex;
        flex-direction: column;
        border: 1px solid #000000;
        word-wrap: break-word !important;
    }
    .chat-bubble-row.me .transfer-card { background: #FFFFFF !important; color: #000000 !important; border-color: #000000 !important; }
    .transfer-title { font-size: 11px !important; opacity: 0.9; margin-bottom: 2px; }
    .transfer-amount { font-size: 20px !important; font-weight: 700; margin: 4px 0; }
    .transfer-note { font-size: 12px !important; opacity: 0.95; margin-bottom: 4px; }
    .transfer-status { font-size: 10px !important; margin-top: 4px; opacity: 0.9; text-align: right; }
    .transfer-card.received { background: #F0F0F0 !important; color: #262626 !important; border-color: #DBDBDB !important; }
    /* 7. 登录/注册 */
    .auth-container { 
        max-width: 100vw !important; 
        width: 90% !important;
        margin: 0 auto !important;
        padding: 24px 16px !important;
    }
    .auth-title { font-size: 26px !important; font-weight: 700 !important; color: #000000 !important; margin-bottom: 8px !important; }
    .auth-subtitle { color: #8E8E8E !important; margin-bottom: 24px !important; font-size: 14px !important; }
    /* 8. 消息列表项 */
    .chat-item {
        display: flex;
        align-items: center;
        padding: 16px !important;
        background: #FFFFFF !important;
        border-bottom: 1px solid #FAFAFA !important;
        transition: background 0.2s ease;
        cursor: pointer;
        width: 100% !important;
        max-width: 100vw !important;
        box-sizing: border-box !important;
        overflow: hidden !important;
    }
    .chat-item:hover { background-color: #FAFAFA !important; }
    .chat-list-container { padding-top: 8px !important; }
    .chat-avatar-wrap { position: relative; margin-right: 12px; flex-shrink: 0; }
    .chat-avatar-wrap img { width: 48px !important; height: 48px !important; border-radius: 50% !important; object-fit: cover !important; }
    .online-indicator { display: none; }
    .chat-content { flex: 1; min-width: 0; }
    .chat-name-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
    .chat-name { font-size: 16px !important; font-weight: 600 !important; color: #000000 !important; }
    .chat-time { font-size: 12px !important; color: #8E8E8E !important; }
    .chat-preview { font-size: 13px !important; color: #8E8E8E !important; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .unread-badge { background: #ED4956; color: #FFF; font-size: 11px; padding: 2px 6px; border-radius: 10px; }
    .chat-arrow .stButton>button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        width: 32px !important;
        height: 32px !important;
        padding: 0 !important;
        border-radius: 50% !important;
        font-size: 18px !important;
        color: #8E8E8E !important;
    }
    .chat-arrow .stButton>button:hover { background: #EFEFEF !important; color: #262626 !important; }
    .receive-btn {
        background: #000000 !important;
        color: #FFFFFF !important;
        border: 1px solid #000000 !important;
        border-radius: 20px !important;
        padding: 8px 16px !important;
        font-size: 13px !important;
        margin-top: 8px !important;
    }
    .interaction-toolbar {
        display: flex;
        align-items: center;
        gap: 12px !important;
        margin-top: 10px !important;
        margin-bottom: 12px !important;
        width: 100% !important;
        overflow-x: auto !important;
        padding-bottom: 4px !important;
    }
    .interaction-toolbar .stButton>button, .interaction-btn {
        min-width: 64px !important;
        height: 32px !important;
        padding: 6px 14px !important;
        border-radius: 8px !important;
        background: #FAFAFA !important;
        border: 1px solid #DBDBDB !important;
        font-size: 13px !important;
        color: #262626 !important;
        text-align: center !important;
        justify-content: center !important;
    }
    /* 通讯录页多选好友时，已选昵称标签样式：黑底白字 */
    [data-testid="stMultiSelect"] [data-baseweb="tag"] {
        background-color: #000000 !important;
        color: #FFFFFF !important;
        border-radius: 999px !important;
    }
    [data-testid="stMultiSelect"] [data-baseweb="tag"] span {
        color: #FFFFFF !important;
    }
    .comment-input-container {
        margin-top: 8px !important;
        padding-top: 8px !important;
        border-top: 1px solid #EFEFEF;
        display: flex;
        align-items: center;
        gap: 8px !important;
        width: 100% !important;
    }
    .comment-input { flex: 1; }
    .comment-send-btn {
        min-width: 56px !important;
        padding: 8px 12px !important;
        border-radius: 20px !important;
        background: #000000 !important;
        color: #FFFFFF !important;
        text-align: center !important;
        justify-content: center !important;
    }
    .chat-list-item .stButton>button {
        padding: 0 !important;
        margin: 0 !important;
        width: 100% !important;
        text-align: left !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        font-size: 13px !important;
        color: #8E8E8E !important;
        font-weight: normal !important;
        border-radius: 0 !important;
    }
    .memory-bank-info {
        background: #EFEFEF;
        border: 1px solid #DBDBDB;
        border-radius: 12px !important;
        padding: 10px 14px !important;
        margin: 8px 0 !important;
        font-size: 13px !important;
        color: #262626;
        width: 100% !important;
    }
    .memory-item {
        background: #FAFAFA;
        border-radius: 8px !important;
        padding: 8px 12px !important;
        margin: 4px 0 !important;
        font-size: 13px !important;
        color: #262626;
        border-left: 3px solid #000000;
        width: 100% !important;
        word-wrap: break-word !important;
    }
    /* 空状态 */
    .empty-state {
        text-align: center;
        padding: 60px 24px;
        color: #8E8E8E;
    }
    .empty-icon { font-size: 48px !important; margin-bottom: 16px !important; opacity: 0.8; }
    .empty-title { font-size: 17px !important; font-weight: 600 !important; color: #262626 !important; margin-bottom: 8px !important; }
    .empty-desc { font-size: 14px !important; color: #8E8E8E !important; }
    /* 聊天页固定区域 */
    .chat-messages-container {
        padding: 16px 12px !important;
        background: #FAFAFA !important;
        overflow-y: auto !important;
        -webkit-overflow-scrolling: touch !important;
    }
    .chat-input-fixed {
        background: #FFFFFF !important;
        border-top: 1px solid #DBDBDB !important;
        padding: 12px 16px !important;
    }
    .chat-input-fixed .stChatInput > div {
        background: #FAFAFA !important;
        border: 1px solid #DBDBDB !important;
        border-radius: 24px !important;
        padding: 8px 16px !important;
        min-height: 44px !important;
    }
    .typing-dots {
        display: flex;
        gap: 4px;
        align-items: center;
        padding: 12px 18px;
    }
    .typing-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #8E8E8E;
        animation: typingBounce 1.4s ease-in-out infinite both;
    }
    .typing-dot:nth-child(2) { animation-delay: 0.2s; }
    .typing-dot:nth-child(3) { animation-delay: 0.4s; }
    @keyframes typingBounce { 0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; } 40% { transform: scale(1); opacity: 1; } }

    /* 创建角色按钮：黑底白字 */
    .new-char-form-marker ~ form button,
    .new-char-form-marker + form button {
        background-color: #000000 !important;
        color: #ffffff !important;
        border: 1px solid #000000 !important;
    }
    .new-char-form-marker ~ form button:hover,
    .new-char-form-marker + form button:hover {
        background-color: #262626 !important;
        color: #ffffff !important;
    }

    /* 发现页 发表/取消：黑底白字 */
    .new-post-form-marker ~ form button,
    .new-post-form-marker + form button {
        background-color: #000000 !important;
        color: #ffffff !important;
        border: 1px solid #000000 !important;
    }
    .new-post-form-marker ~ form button:hover,
    .new-post-form-marker + form button:hover {
        background-color: #262626 !important;
        color: #ffffff !important;
    }

    /* 个人中心 保存设置/修改密码/退出登录：黑底白字 */
    .profile-form-marker ~ form button,
    .profile-form-marker + form button {
        background-color: #000000 !important;
        color: #ffffff !important;
        border: 1px solid #000000 !important;
    }
    .profile-form-marker ~ form button:hover,
    .profile-form-marker + form button:hover {
        background-color: #262626 !important;
        color: #ffffff !important;
    }

    @media (max-width: 375px) {
        .block-container { padding-left: 4px !important; padding-right: 4px !important; }
        .chat-bubble-content { max-width: 85% !important; padding: 10px 14px !important; font-size: 14px !important; }
        .chat-item { padding: 12px !important; }
        .transfer-card { min-width: 160px !important; padding: 10px 14px !important; }
        .transfer-amount { font-size: 18px !important; }
    }
</style>
""", unsafe_allow_html=True)

# ===================== 1. 数据库逻辑 =====================

@st.cache_resource
def init_supabase() -> Client:
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_supabase()

# 持久登录 Cookie：同一设备只需登录一次，关闭浏览器后再打开仍保持登录（除非主动退出）
from streamlit_cookies_manager import EncryptedCookieManager
try:
    _cookie_secret = getattr(st.secrets, "COOKIES_PASSWORD", None) or os.environ.get("COOKIES_PASSWORD", "narratio-remember-secret")
except Exception:
    _cookie_secret = os.environ.get("COOKIES_PASSWORD", "narratio-remember-secret")
cookies = EncryptedCookieManager(prefix="narratio/", password=_cookie_secret)
# 这里不再在 cookies 尚未 ready 时直接 st.stop()，否则在首次加载或退出登录后
# 可能出现整页空白。即便 cookies 暂未就绪，后续读取将返回 None，
# 登录页面仍可正常渲染。

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
                "moments": st.session_state.moments,
                # 新增群聊数据
                "groups": st.session_state.get("groups", [])
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
    av = get_avatar_display(avatar_data, "📜")
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
    # 好感度：0-100，影响角色对对方的语气与态度
    fav = int(char.get("favorability", 30))
    fav_desc = "冷淡、疏离" if fav < 30 else "一般、客气" if fav < 60 else "亲近、信任"
    parts.append(f"【当前好感度】数值：{fav}（0-100）。含义：{fav_desc}。请根据当前好感度调整你对对方的语气、亲密度和态度，数值越高越亲近自然，越低越保持距离或冷淡。")
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

def compute_favorability_change(char, user_msg, ai_response):
    """由 AI 判断本次对话是否导致好感度变化，返回 -5～5 的增量（重大事项可超出），无需变化则返回 0。"""
    api_key, model, base_url = get_api_info(char)
    if not api_key:
        return 0
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        fav = int(char.get("favorability", 30))
        prompt = f"""你是{char['name']}的内心评判。仅根据下面这一轮对话，判断你对对方的「好感度」是否变化。
【当前好感度】{fav}（0-100）
【对方刚说】{user_msg}
【你刚回复】{ai_response}

规则：
- 不必每轮都变化，多数日常对话可不变（输出 0）。
- 若有变化：一般情况每次变化在 -5 到 +5 之间；只有重大事件（如背叛、深情告白、严重冒犯等）才可超出 ±5。
- 输出严格为一行 JSON，不要其他内容。格式：{{"change": 数字}}
例如：{{"change": 0}} 或 {{"change": 2}} 或 {{"change": -3}}"""
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        raw = (resp.choices[0].message.content or "").strip()
        if "```" in raw:
            raw = re.sub(r"```\w*\n?", "", raw).strip()
        obj = json.loads(raw)
        delta = int(obj.get("change", 0))
        return max(-20, min(20, delta))  # 单次最多 ±20 兜底
    except Exception:
        return 0

# ===================== 2. 身份验证 =====================

def try_restore_session_from_cookie():
    """从持久化 Cookie 恢复登录状态（同一设备再次打开网页时免登录）"""
    # 如果 Cookie 管理器尚未就绪，先不标记结果，等待下一轮重试，
    # 避免访问 cookies 时抛出 CookiesNotReady 异常。
    if not cookies.ready():
        return False
    val = cookies.get("narratio_login")
    if not val:
        return False
    try:
        data = json.loads(val)
        if data.get("exp", 0) <= time.time():
            return False  # 已过期
        username = data.get("username")
        if not username:
            return False
        res = supabase.table("user_data").select("*").eq("username", username).execute()
        if not res.data:
            return False
        row = res.data[0]
        characters = row.get("characters") or []
        for char in characters:
            if "memory_bank" not in char:
                char["memory_bank"] = {"core_memories": [], "recent_context": []}
            char.setdefault("favorability", 30)
        # 新增：群聊数据（兼容旧数据）
        groups = row.get("groups") or []
        st.session_state.update({
            "password_correct": True,
            "username": username,
            "user_profile": row.get("profile") or {},
            "characters": characters,
            "moments": row.get("moments") or [],
            "groups": groups
        })
        return True
    except Exception:
        return False

def validate_username(username):
    """验证账号名是否为英文字母或数字"""
    return bool(re.match(r'^[a-zA-Z0-9]+$', username))

def check_password():
    # 未登录时先尝试从持久化 Cookie 恢复（同一设备再次打开直接进主页）。
    # 恢复逻辑分两步：
    # 1）等待 cookies.ready() 为 True，再决定是否有可用登录信息；
    # 2）只在确认 cookies.ready() 后做一次最终判定，避免在登录页输入过程中
    #    反复被之前账号“抢回去”。
    if "password_correct" not in st.session_state:
        if not st.session_state.get("auto_restore_finalized", False):
            if cookies.ready():
                if try_restore_session_from_cookie():
                    # 成功从 Cookie 恢复，直接进入主页
                    st.session_state["auto_restore_finalized"] = True
                    st.rerun()
                else:
                    # cookies 已就绪但没有有效登录信息，本轮之后不再尝试自动恢复
                    st.session_state["auto_restore_finalized"] = True
    if "password_correct" not in st.session_state:
        # 优化登录页面布局
        st.markdown("""
        <div class="auth-container">
            <div style="text-align:center;">
                <h1 class="auth-title">📜 Narratio</h1>
                <p class="auth-subtitle">Narratio 聊天空间</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        t1, t2 = st.tabs(["登录", "注册"])
        with t1:
            st.markdown("<div style='padding:0 20px;'>", unsafe_allow_html=True)
            u = st.text_input("账号", key="l_u", placeholder="请输入你的账号")
            p = st.text_input("密码", type="password", key="l_p", placeholder="请输入你的密码")
            if st.button("进入", use_container_width=True, type="primary"):
                try:
                    res = supabase.table("user_data").select("*").eq("username", u).execute()
                except (httpx.ConnectError, httpx.ConnectTimeout, OSError) as e:
                    st.error(
                        "无法连接至 Supabase 服务器（连接被拒绝或超时）。请检查：\n\n"
                        "1. `.streamlit/secrets.toml` 中的 `SUPABASE_URL` 是否填写正确；\n"
                        "2. 本机网络是否正常、是否需要代理；\n"
                        "3. Supabase 服务是否可用。"
                    )
                    st.stop()
                if res.data and verify_password(p, res.data[0]["password_hash"]):
                    # 数据迁移：为旧角色添加memory_bank
                    characters = res.data[0]["characters"] or []
                    for char in characters:
                        if "memory_bank" not in char:
                            char["memory_bank"] = {
                                "core_memories": [],
                                "recent_context": []
                            }
                        char.setdefault("favorability", 30)
                    groups = res.data[0].get("groups") or []
                    # 持久登录：写入 Cookie，30 天内同一设备免登录
                    login_payload = json.dumps({"username": u, "exp": time.time() + 30 * 24 * 3600})
                    cookies["narratio_login"] = login_payload
                    cookies.save()
                    st.session_state.update({
                        "password_correct":True, 
                        "username":u, 
                        "user_profile":res.data[0]["profile"], 
                        "characters":characters, 
                        "moments":res.data[0]["moments"] or [],
                        "groups": groups
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
                        try:
                            res = supabase.table("user_data").select("username").eq("username", nu).execute()
                        except (httpx.ConnectError, httpx.ConnectTimeout, OSError):
                            st.error("无法连接至 Supabase 服务器，请检查 SUPABASE_URL 与网络后重试。")
                            st.stop()
                        if res.data:
                            st.error("该账号已存在", icon="❌")
                        else:
                            try:
                                supabase.table("user_data").insert({
                                    "username": nu,
                                    "password_hash": hash_password(np),
                                    "profile": {"nickname": nu, "avatar": None, "global_api_key": "", "global_provider": "deepseek", "global_model": "deepseek-chat"},
                                    "characters": [],
                                    "moments": []
                                }).execute()
                            except (httpx.ConnectError, httpx.ConnectTimeout, OSError):
                                st.error("无法连接至 Supabase 服务器，请检查 SUPABASE_URL 与网络后重试。")
                                st.stop()
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

def get_current_group():
    group_id = st.session_state.get("current_group_id")
    return next((g for g in st.session_state.get("groups", []) if g["id"] == group_id), None)

def get_api_info(char):
    """返回 (api_key, model, base_url)"""
    key = char.get("api_key") or st.session_state.user_profile.get("global_api_key", "")
    provider_id = st.session_state.user_profile.get("global_provider", "deepseek")
    provider = _get_provider(provider_id)
    # 先取全局模型；若不属于当前服务商，自动回退默认模型
    global_model = st.session_state.user_profile.get("global_model")
    if not global_model or global_model not in provider["models"]:
        global_model = provider["default_model"]

    # 角色自定义模型仅在属于当前服务商时生效，避免切换服务商后仍卡在旧模型
    char_model = (char.get("model") or "").strip()
    mod = char_model if char_model and char_model in provider["models"] else global_model
    return key, mod, provider["base_url"]

if "active_tab" not in st.session_state: st.session_state.active_tab = "Narratio"
if "view_mode" not in st.session_state: st.session_state.view_mode = "main"
if "reply_to_comment" not in st.session_state: st.session_state.reply_to_comment = {}
if "nav_drawer_open" not in st.session_state: st.session_state.nav_drawer_open = False
if "groups" not in st.session_state: st.session_state.groups = []
if "current_group_id" not in st.session_state: st.session_state.current_group_id = None
if "view_mode" in st.session_state and st.session_state.view_mode not in ("main", "chat", "edit_char", "chat_group", "edit_group"):
    st.session_state.view_mode = "main"

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
    st.markdown("<h3 style='text-align:center; margin:12px 0 20px 0; color:#000000; font-weight:600; font-size:1.2rem;'>消息</h3>", unsafe_allow_html=True)

    # 单聊按最近消息条数近似排序（真实项目可存 timestamp）
    def last_ts_single(c):
        return len(c.get("messages", []))

    display_chars = sorted(st.session_state.characters, key=last_ts_single, reverse=True)

    # 群聊同样按消息条数排序
    def last_ts_group(g):
        return len(g.get("messages", []))

    display_groups = sorted(st.session_state.get("groups", []), key=last_ts_group, reverse=True)

    if not display_chars and not display_groups:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">💬</div>
            <div class="empty-title">暂无聊天对象</div>
            <div class="empty-desc">前往「通讯录」添加 AI 角色开始聊天吧</div>
        </div>
        """, unsafe_allow_html=True)
        return
    
    # 预先整理每个角色的最后一条消息，用于摘要展示
    last_msgs = {}
    for c in display_chars:
        msgs = c.get("messages", [])
        last = msgs[-1]["content"] if msgs else "暂无消息"
        last_msgs[c["id"]] = (last or "暂无消息").replace("\n", " ").strip()

    # 渲染单聊会话：左侧纯展示，右侧小箭头按钮负责跳转
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
                    <div style="font-size:16px; font-weight:600; color:#000000; line-height:1.4; margin-bottom:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{safe_name}</div>
                    <div style="font-size:13px; color:#8E8E8E; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; line-height:1.2;">{safe_last_msg}</div>
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

    # 渲染群聊会话列表
    for group in display_groups:
        last_msg = (group.get("messages", [])[-1]["content"]
                    if group.get("messages") else "暂无消息")
        safe_name = html.escape(group.get("name", "未命名群聊"))
        safe_last_msg = html.escape((last_msg or "暂无消息").replace("\n", " ").strip())
        # 群聊头像：简单用一个圆形图标表示
        avatar_html = "<div style='width:44px;height:44px;border-radius:50%;background:#F3F4F6;display:flex;align-items:center;justify-content:center;font-size:22px;'>👩‍👧‍👦</div>"

        chat_html = f"""
        <div class="chat-item">
            <div style="display: flex; align-items: center; width: 100%;">
                <div style="flex-shrink: 0; margin-right: 12px;">
                    {avatar_html}
                </div>
                <div style="flex-grow: 1; display: flex; flex-direction: column; justify-content: center; overflow: hidden;">
                    <div style="font-size:16px; font-weight:600; color:#000000; line-height:1.4; margin-bottom:2px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{safe_name}</div>
                    <div style="font-size:13px; color:#8E8E8E; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; line-height:1.2;">{safe_last_msg}</div>
                </div>
            </div>
        </div>
        """

        col1, col2 = st.columns([0.9, 0.1])
        with col1:
            st.markdown(chat_html, unsafe_allow_html=True)
        with col2:
            st.markdown('<div class="chat-arrow" style="display:flex;align-items:center;justify-content:center;height:100%;">', unsafe_allow_html=True)
            if st.button("›", key=f"go_group_{group['id']}", help=f"进入群聊 {group.get('name','')}", use_container_width=True):
                st.session_state.current_group_id = group["id"]
                st.session_state.view_mode = "chat_group"
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

    # 聊天头部：仅保留可点击昵称，点击展开下拉菜单（返回 / 设置）
    st.markdown(
        "<script>document.body.classList.add('chat-view');</script><div class=\"chat-header-marker\" aria-hidden=\"true\"></div>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<style>"
        "body.chat-view [data-testid=\"stHorizontalBlock\"]:has(.stPopover) { "
        "width: 100% !important; display: flex !important; justify-content: center !important; align-items: center !important; "
        "padding: 4px 0 6px 0 !important; min-height: 0 !important; "
        "}"
        "body.chat-view [data-testid=\"stHorizontalBlock\"]:has(.stPopover) [data-testid=\"column\"] { "
        "flex: 0 0 auto !important; max-width: none !important; "
        "display: flex !important; justify-content: center !important; align-items: center !important; padding: 0 4px !important; "
        "}"
        "body.chat-view [data-testid=\"stHorizontalBlock\"]:has(.stPopover) .stPopover > button { "
        "background: transparent !important; border: none !important; box-shadow: none !important; "
        "font-size: 15px !important; font-weight: 600 !important; color: #000000 !important; "
        "padding: 6px 10px !important; border-radius: 8px !important; "
        "}"
        "body.chat-view [data-testid=\"stHorizontalBlock\"]:has(.stPopover) .stPopover > button:hover { background: #FAFAFA !important; }"
        "</style>",
        unsafe_allow_html=True
    )
    st.markdown(
        "<script>"
        "function centerNicknameRow(){"
        "  var rows=document.querySelectorAll('[data-testid=stHorizontalBlock]');"
        "  for(var i=0;i<rows.length;i++){"
        "    if(rows[i].querySelector('.stPopover')){"
        "      var r=rows[i];"
        "      r.style.setProperty('width','100%','important');"
        "      r.style.setProperty('display','flex','important');"
        "      r.style.setProperty('justify-content','center','important');"
        "      r.style.setProperty('align-items','center','important');"
        "      var cols=r.querySelectorAll('[data-testid=column]');"
        "      for(var j=0;j<cols.length;j++){"
        "        cols[j].style.setProperty('flex','0 0 auto','important');"
        "        cols[j].style.setProperty('display','flex','important');"
        "        cols[j].style.setProperty('justify-content','center','important');"
        "      }"
        "      return;"
        "    }"
        "  }"
        "}"
        "centerNicknameRow();"
        "setTimeout(centerNicknameRow,150);"
        "setTimeout(centerNicknameRow,500);"
        "</script>",
        unsafe_allow_html=True
    )
    col_left, col_center, col_right = st.columns([1, 1, 1])
    with col_left:
        st.write("")
    with col_center:
        with st.popover(char.get("name", "聊天")):
            if st.button("🔙 返回消息列表", key="chat_header_back", use_container_width=True):
                st.session_state.view_mode = "main"
                st.rerun()
            if st.button("⚙️ 设置人物详情", key="chat_header_settings", use_container_width=True):
                st.session_state.view_mode = "edit_char"
                st.rerun()
        typing_placeholder = st.empty()
    with col_right:
        st.write("")
    st.markdown("<hr style='margin:2px 0 4px 0; border:none; border-top:1px solid #DBDBDB;'/>", unsafe_allow_html=True)
    
    # 消息循环
    user_av = get_avatar_display(st.session_state.user_profile.get("avatar"), "👤")
    char_av = get_avatar_display(char.get("avatar"), "📜")
    
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
            # 好感度：由 AI 判断本轮是否增减
            delta = compute_favorability_change(char, user_msg, raw)
            if delta != 0:
                fav = int(char.get("favorability", 30))
                char["favorability"] = max(0, min(100, fav + delta))
            
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
        
    st.markdown(f"<h3 style='margin:12px 0 20px 0; color:#000000; font-weight:600; font-size:1.2rem;'>编辑 {char['name']}</h3>", unsafe_allow_html=True)
    
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
    current_char_model = (char.get("model") or "").strip()
    if current_char_model not in model_options:
        current_char_model = ""
    model_index = model_options.index(current_char_model) if current_char_model in model_options else 0
    char["model"] = st.selectbox("模型（选填，留空用全局）", options=model_options, index=model_index, format_func=lambda x: x or "使用全局设置")
    
    char['persona'] = st.text_area("人设 (Prompt)", char['persona'], height=150, placeholder="请详细描述角色的性格、语气、背景等")
    char['memory'] = st.text_area("核心记忆（手动设置）", char.get('memory',''), height=100, placeholder="角色需要记住的关键信息（AI自动提取的记忆会显示在下方）")
    
    # 好感度条：0-100，初始 30，聊天中由 AI 酌情增减，用户可在此手动调节
    fav = int(char.get("favorability", 30))
    char["favorability"] = st.slider(
        "好感度",
        min_value=0,
        max_value=100,
        value=fav,
        step=1,
        help="当前角色对你的好感度（0-100）。聊天过程中会随剧情由 AI 自动微调，也可在此手动调节。"
    )
    
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
                    role = "👤" if ctx["role"] == "user" else "📜"
                    content = ctx.get("content", "")[:50]
                    st.markdown(f"{role} {content}...")
    
    # 头像 / 背景 / 操作按钮 纵向排列
    st.markdown("<div style='margin:20px 0;'>", unsafe_allow_html=True)
    
    st.subheader("头像设置", divider="gray")
    current_av = get_avatar_display(char.get("avatar"), "📜")
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
    
    st.subheader("背景设置", divider="gray")
    if char.get('bg'):
        st.image(char['bg'], width=150)
    else:
        st.markdown("<p style='color:#8E8E8E;'>暂无背景图</p>", unsafe_allow_html=True)
    new_bg = st.file_uploader("更换背景图", type=['png','jpg'], key="bg_upload")
    if st.button("保存背景", key="save_bg", use_container_width=True):
        if new_bg:
            char['bg'] = process_uploaded_image(new_bg, (1080,1920))
            save_cloud_data()
            st.success("背景保存成功！", icon="✅")
            time.sleep(1)
            st.rerun()
    
    if st.button("完成并返回", use_container_width=True, type="primary"):
        save_cloud_data()
        st.session_state.view_mode = "chat"
        st.rerun()
    if st.button("清空聊天记录", use_container_width=True, type="secondary"):
        char["messages"] = []
        # 只清空最近对话，不动长期记忆与好感度
        if "memory_bank" in char:
            char["memory_bank"]["recent_context"] = []
        save_cloud_data()
        st.success("已清空与该角色的聊天记录。", icon="✅")
        time.sleep(1)
        st.rerun()
    if st.button("删除角色", use_container_width=True):
        if st.checkbox("确认删除该角色（不可恢复）", key="confirm_delete_char"):
            st.session_state.characters.remove(char)
            save_cloud_data()
            st.session_state.view_mode = "main"
            st.success("角色已删除", icon="✅")
            time.sleep(1)
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_edit_group():
    """群聊设置页：修改名称、成员、头像，支持解散群聊"""
    group = get_current_group()
    if not group:
        st.session_state.view_mode = "main"
        st.rerun()
        return

    st.markdown(
        f"<h3 style='margin:12px 0 20px 0; color:#000000; font-weight:600; font-size:1.2rem;'>编辑群聊：{html.escape(group.get('name','群聊'))}</h3>",
        unsafe_allow_html=True
    )

    # 基本信息
    group["name"] = st.text_input("群聊名称", group.get("name", ""), placeholder="请输入群聊名称")

    # 成员增删：用已有角色多选
    st.subheader("群成员", divider="gray")
    all_chars = st.session_state.characters
    if not all_chars:
        st.info("当前还没有任何 AI 好友，请先在通讯录中创建角色。")
    else:
        name_to_id = {c["name"]: c["id"] for c in all_chars}
        current_names = [c["name"] for c in all_chars if c["id"] in group.get("member_ids", [])]
        selected_names = st.multiselect(
            "选择群聊成员",
            options=list(name_to_id.keys()),
            default=current_names
        )
        group["member_ids"] = [name_to_id[n] for n in selected_names]

    # 群头像
    st.subheader("群头像", divider="gray")
    current_avatar = group.get("avatar")
    if current_avatar:
        st.image(current_avatar, width=80)
    else:
        st.markdown(
            "<div style='width:80px;height:80px;border-radius:50%;background:#F3F4F6;display:flex;align-items:center;justify-content:center;font-size:40px;'>👩‍👧‍👦</div>",
            unsafe_allow_html=True
        )
    new_group_av = st.file_uploader("上传新的群头像", type=["png", "jpg", "jpeg"], key="group_avatar_upload")
    if st.button("保存群头像", key="save_group_avatar", use_container_width=True):
        if new_group_av:
            group["avatar"] = process_uploaded_image(new_group_av, (200, 200))
            save_cloud_data()
            st.success("群头像已更新！", icon="✅")
            time.sleep(1)
            st.rerun()

    st.markdown("---")
    # 按钮区纵向排列：保存返回 / 清空聊天记录 / 解散群聊
    if st.button("保存设置并返回群聊", use_container_width=True, type="primary"):
        save_cloud_data()
        st.session_state.view_mode = "chat_group"
        st.rerun()

    if st.button("清空群聊聊天记录", use_container_width=True, type="secondary"):
        group["messages"] = []
        group["last_user_msg"] = ""
        group["need_ai_reply"] = False
        save_cloud_data()
        st.success("已清空该群聊的聊天记录。", icon="✅")
        time.sleep(1)
        st.rerun()

    confirm_key = f"confirm_disband_group_{group['id']}"
    st.checkbox("确认解散该群聊（不可恢复）", key=confirm_key)
    if st.button("解散该群聊", use_container_width=True):
        if st.session_state.get(confirm_key):
            # 从会话中移除该群
            st.session_state.groups = [g for g in st.session_state.groups if g["id"] != group["id"]]
            save_cloud_data()
            st.session_state.current_group_id = None
            st.session_state.view_mode = "main"
            st.success("群聊已解散。", icon="✅")
            time.sleep(1)
            st.rerun()

def render_group_chat_session():
    """群聊会话：多个 AI 好友共同参与"""
    group = get_current_group()
    if not group:
        st.session_state.view_mode = "main"
        st.rerun()
        return

    members = [c for c in st.session_state.characters if c["id"] in group.get("member_ids", [])]
    if not members:
        st.warning("该群聊还没有有效的成员，请在通讯录中为该账号添加好友后重新创建群聊。")
        return

    # 顶部：以群聊名称作为下拉菜单按键（返回 / 设置）
    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_left:
        st.write("")
    with col_center:
        group_title = html.escape(group.get("name", "群聊"))
        with st.popover(group_title):
            if st.button("🔙 返回消息列表", key="group_header_back", use_container_width=True):
                st.session_state.view_mode = "main"
                st.rerun()
            if st.button("⚙️ 群聊设置", key="group_header_settings", use_container_width=True):
                st.session_state.view_mode = "edit_group"
                st.rerun()
    with col_right:
        st.write("")

    st.markdown("<hr style='margin:4px 0 8px 0; border:none; border-top:1px solid #DBDBDB;'/>", unsafe_allow_html=True)

    user_av = get_avatar_display(st.session_state.user_profile.get("avatar"), "👤")

    # 消息渲染：支持显示发送者昵称与转账卡片
    for idx, m in enumerate(group.get("messages", [])):
        is_user = m.get("role") == "user"
        sender_name = m.get("sender_name", st.session_state.user_profile.get("nickname") if is_user else "")
        if is_user:
            av = user_av
        else:
            char = next((c for c in members if c["id"] == m.get("char_id")), None)
            av = get_avatar_display(char.get("avatar"), "📜") if char else "📜"
            sender_name = char["name"] if char else (sender_name or "好友")

        if isinstance(av, str) and av.startswith("http"):
            av_html = f"<img src='{av}' style='width:100%;height:100%;object-fit:cover;'>"
        else:
            av_html = av

        msg_type = m.get("type", "text")
        # 转账卡片（仅用于 AI -> 用户的转账展示）
        if msg_type == "transfer" and not is_user:
            amount = m.get("amount", 0)
            note = m.get("note", "")
            status = m.get("status", "未收款")
            who = "TA 向你转账"
            card_cls = "transfer-card received" if status == "已收款" else "transfer-card"

            safe_who = safe_text(who)
            safe_note = safe_text(note)
            safe_status = safe_text(status)

            html_block = f"""
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
            st.markdown(html_block, unsafe_allow_html=True)
            # 群聊中也支持“收款”：当状态为未收款时，提供一个收款按钮，
            # 点击后将当前转账标记为“已收款”，并切换为浅色卡片。
            if status != "已收款":
                col = st.columns([1, 2, 1])
                with col[1]:
                    if st.button("点击收款", key=f"group_recv_{group['id']}_{m.get('id', idx)}", use_container_width=True):
                        m["status"] = "已收款"
                        save_cloud_data()
                        st.rerun()
            continue

        safe_content = safe_text(m.get("content", ""))
        safe_sender = safe_text(sender_name)

        if is_user:
            html_block = f"""
<div class="chat-bubble-row me">
  <div class="chat-bubble-content chat-bubble-me">
    <div style="font-size:11px;color:#9CA3AF;margin-bottom:2px;text-align:right;">{safe_sender}</div>
    {safe_content}
  </div>
  <div class="chat-bubble-avatar">{av_html}</div>
</div>
"""
        else:
            html_block = f"""
<div class="chat-bubble-row">
  <div class="chat-bubble-avatar">{av_html}</div>
  <div class="chat-bubble-content chat-bubble-other">
    <div style="font-size:11px;color:#D1D5DB;margin-bottom:2px;text-align:left;">{safe_sender}</div>
    {safe_content}
  </div>
</div>
"""
        st.markdown(html_block, unsafe_allow_html=True)

    # 输入框：只负责写入自己的消息并触发一次 rerun，让消息立刻显示
    prompt = st.chat_input("在群里说点什么...", key="group_chat_input")
    if prompt:
        clean = re.sub(r"[（(][^）)]*[）)]", "", prompt).strip() or prompt
        group.setdefault("messages", [])
        group["messages"].append({
            "role": "user",
            "content": clean,
            "sender_name": st.session_state.user_profile.get("nickname", st.session_state.username)
        })
        # 记录最近一条用户消息，用于后续判断要由哪位群成员来回应
        group["last_user_msg"] = clean
        # 标记需要 AI 回复，交给下一轮渲染处理，避免发送后长时间无反馈
        group["need_ai_reply"] = True
        save_cloud_data()
        st.rerun()

    # 如果存在待处理的 AI 回复，在本轮渲染中统一处理
    if group.get("need_ai_reply"):
        # 根据用户最近一条消息内容，智能选择更合适的回应者：
        # - 如果明确提到了某个角色的名字，仅由被点名者回应；
        # - 如果提到了多个名字，从中选 1~2 位回应；
        # - 否则从所有成员中随机选 1 位主回应者，另加 0~1 位旁观回应者。
        import random as _rnd
        last_msg = group.get("last_user_msg", "")
        mentioned = []
        if last_msg:
            for c in members:
                name = c.get("name") or ""
                if name and name in last_msg:
                    mentioned.append(c)
        if mentioned:
            base = mentioned
        else:
            base = members

        if len(base) <= 1:
            responders = base
        else:
            # 至少一位，至多两位
            num_responders = min(len(base), 2)
            responders = _rnd.sample(base, num_responders)

        for char in responders:
            api_key, model, base_url = get_api_info(char)
            if not api_key:
                continue
            try:
                client = OpenAI(api_key=api_key, base_url=base_url)
                # 群聊场景 system prompt：在原有设定上补充「群聊」说明
                sys_prompt = build_system_prompt(char, scene="chat") + "\n\n【当前为群聊场景】你正在一个包含多位好友的群聊中回复对方，请保持自然、简短。"

                # 上下文：从群聊消息中抽取最近若干条。
                # 为了避免模型学会输出“某某: 内容”这种不真实的群聊格式，
                # 这里只提供纯内容，不再在前面加「人名+冒号」前缀；
                # 同时也不在群聊里鼓励使用“转账卡」指令。
                history = []
                for msg in group["messages"][-10:]:
                    content = msg.get("content", "")
                    if msg.get("role") == "user":
                        history.append({"role": "user", "content": content})
                    else:
                        history.append({"role": "assistant", "content": content})

                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": sys_prompt}] + history
                )
                raw = resp.choices[0].message.content or ""

                # 兼容“用竖线分多条消息”的写作方式，每段单独成气泡；
                # 同时去掉模型可能加上的「某某: 」前缀，只保留自然对话内容；
                # 并支持与私聊相同的转账卡片写法，在群聊中展示为 TA -> 你 的转账卡。
                pending_transfer = None
                for seg in re.split(r"[｜|\n]+", raw):
                    seg = seg.strip()
                    if not seg:
                        continue

                    # 情况 A：一行写完的转账指令：转账卡|金额=XXX|备注=...
                    if seg.startswith("转账卡|"):
                        try:
                            amt_match = re.search(r"金额=([0-9]+(?:\.[0-9]+)?)", seg)
                            note_match = re.search(r"备注=([^|]+)", seg)
                            amount = float(amt_match.group(1)) if amt_match else 0.0
                            note = note_match.group(1).strip() if note_match else ""
                        except Exception:
                            amount, note = 0.0, ""
                        group["messages"].append({
                            "role": "assistant",
                            "content": "",
                            "type": "transfer",
                            "amount": round(float(amount), 2),
                            "note": note,
                            "direction": "to_user",
                            "status": "未收款",
                            "char_id": char["id"],
                            "sender_name": char["name"]
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
                    if seg.startswith("备注="):
                        if pending_transfer is None:
                            pending_transfer = {"amount": None, "note": ""}
                        pending_transfer["note"] = seg.split("=", 1)[1].strip()
                        amount = pending_transfer.get("amount") or 0.0
                        note = pending_transfer.get("note", "")
                        group["messages"].append({
                            "role": "assistant",
                            "content": "",
                            "type": "transfer",
                            "amount": round(float(amount), 2),
                            "note": note,
                            "direction": "to_user",
                            "status": "未收款",
                            "char_id": char["id"],
                            "sender_name": char["name"]
                        })
                        pending_transfer = None
                        continue

                    # 普通文本：去掉类似「友人A:」「我：」这样的人称前缀与括号动作
                    seg = re.sub(r"^[^：:]{1,8}[：:]\s*", "", seg)
                    seg_clean = re.sub(r"[（(][^）)]*[）)]", "", seg).strip()
                    if not seg_clean:
                        continue
                    group["messages"].append({
                        "role": "assistant",
                        "content": seg_clean,
                        "char_id": char["id"],
                        "sender_name": char["name"]
                    })
            except Exception:
                continue

        group["need_ai_reply"] = False
        save_cloud_data()
        st.rerun()

def render_moments_page():
    st.markdown("<h3 style='text-align:center; margin:12px 0 20px 0; color:#000000; font-weight:600; font-size:1.2rem;'>发现</h3>", unsafe_allow_html=True)
    
    # 优化发布动态区域
    with st.expander("📷 发布新动态", expanded=False):
        st.markdown('<div class="new-post-form-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
        with st.form("new_post", clear_on_submit=True):
            txt = st.text_area("这一刻的想法...", height=100, placeholder="分享你的心情、想法或故事...")
            img = st.file_uploader("添加配图（可选）", type=['png','jpg','jpeg'])
            col1, col2 = st.columns([4,1])
            with col1:
                submit = st.form_submit_button("发表", use_container_width=True)
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
        <div class="empty-state">
            <div class="empty-icon">🌍</div>
            <div class="empty-title">暂无动态</div>
            <div class="empty-desc">发布一条动态，和好友互动吧</div>
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
        st.markdown(f"<span style='color:#000000; font-weight:600; font-size:16px;'>{safe_poster_name}</span>", unsafe_allow_html=True)
        # 动态内容
        safe_text_content = safe_text(m.get('text',''))
        st.markdown(f"<p style='margin:12px 0; line-height:1.5; color:#262626;'>{safe_text_content}</p>", unsafe_allow_html=True)
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
    st.markdown("<h3 style='text-align:center; margin:12px 0 20px 0; color:#000000; font-weight:600; font-size:1.2rem;'>通讯录</h3>", unsafe_allow_html=True)
    
    # 展示现有角色
    if st.session_state.characters:
        st.markdown("<p style='color:#6B7280; margin:0 0 10px 10px;'>我的 AI 好友</p>", unsafe_allow_html=True)
        for char in st.session_state.characters:
            st.markdown('<div style="padding:10px 0; border-bottom:1px solid #F3F4F6;">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 3, 2])
            with col1:
                av = get_avatar_display(char.get("avatar"), "📜")
                if isinstance(av, str) and av.startswith("http"):
                    st.markdown(f'<img src="{av}" style="width:40px;height:40px;border-radius:50%;object-fit:cover;">', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div style="width:40px;height:40px;border-radius:50%;background:#F3F4F6;display:flex;align-items:center;justify-content:center;font-size:20px;">{av}</div>', unsafe_allow_html=True)
            with col2:
                safe_name = safe_text(char.get("name", ""))
                st.markdown(f"<b style='font-size:15px; color:#000000;'>{safe_name}</b>", unsafe_allow_html=True)
            with col3:
                if st.button("开始聊天", key=f"cont_{char['id']}", use_container_width=True, type="primary"): 
                    st.session_state.current_char_id = char['id']
                    st.session_state.view_mode = "chat"
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">👥</div>
            <div class="empty-title">暂无 AI 好友</div>
            <div class="empty-desc">添加一个 AI 角色开始聊天吧</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    # 添加新角色
    with st.expander("➕ 添加新 AI 角色", expanded=True):
        st.markdown('<div class="new-char-form-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
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
            
            if st.form_submit_button("创建角色", use_container_width=True):
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
                        "favorability": 30,
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

    st.divider()

    # 新增：创建群聊
    with st.expander("👥 创建群聊", expanded=False):
        if not st.session_state.characters:
            st.info("请先创建至少一个 AI 好友，再来创建群聊。")
        else:
            group_name = st.text_input("群聊名称", key="new_group_name", placeholder="例如：深夜闲聊小组")
            # 以好友昵称多选
            options = {c["name"]: c["id"] for c in st.session_state.characters}
            selected_names = st.multiselect("选择要拉入群聊的好友", options=list(options.keys()))
            if st.button("确认创建群聊", use_container_width=True, key="create_group_btn"):
                if not group_name.strip():
                    st.warning("群聊名称不能为空", icon="⚠️")
                elif not selected_names:
                    st.warning("请至少选择一位好友加入群聊", icon="⚠️")
                else:
                    member_ids = [options[n] for n in selected_names]
                    new_group = {
                        "id": uuid4().hex,
                        "name": group_name.strip(),
                        "member_ids": member_ids,
                        "messages": []
                    }
                    st.session_state.groups.append(new_group)
                    save_cloud_data()
                    st.success("群聊创建成功，已出现在消息列表中。", icon="✅")
                    time.sleep(1)
                    st.rerun()

def render_profile_page():
    st.markdown("<h3 style='text-align:center; margin:12px 0 20px 0; color:#000000; font-weight:600; font-size:1.2rem;'>个人中心</h3>", unsafe_allow_html=True)
    
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
    st.markdown(f"<h4 style='margin:10px 0; color:#000000; font-weight:600;'>{safe_nickname}</h4>", unsafe_allow_html=True)
    st.markdown(f"<p style='color:#8E8E8E; font-size:13px;'>账号：{safe_username}（不可修改）</p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="profile-form-marker" aria-hidden="true"></div>', unsafe_allow_html=True)

    st.subheader("AI 设置", divider="gray")
    provider_options = [p["name"] for p in LLM_PROVIDERS]
    current_provider_id = prof.get("global_provider", "deepseek")
    current_provider_index = next((i for i, p in enumerate(LLM_PROVIDERS) if p["id"] == current_provider_id), 0)
    selected_name = st.selectbox(
        "选择模型服务",
        options=provider_options,
        index=current_provider_index,
        key="profile_global_provider_name",
        help="选择 DeepSeek、Kimi、GPT、Gemini 等（需对应 API Key）"
    )
    selected_provider = next((p for p in LLM_PROVIDERS if p["name"] == selected_name), LLM_PROVIDERS[0])
    prof["global_provider"] = selected_provider["id"]

    model_options = selected_provider["models"]
    current_model = prof.get("global_model") or selected_provider["default_model"]
    if current_model not in model_options:
        current_model = selected_provider["default_model"]
    model_index = model_options.index(current_model) if current_model in model_options else 0
    prof["global_model"] = st.selectbox(
        "选择模型",
        options=model_options,
        index=model_index,
        key="profile_global_model_name",
        help="不同服务商的模型名称不同，选错可能无法调用"
    )
    prof["global_api_key"] = st.text_input(
        "API Key",
        prof.get("global_api_key", ""),
        type="password",
        key="profile_global_api_key",
        placeholder=f"{selected_provider['name']} API Key（所有角色默认使用）"
    )
    prof["self_persona"] = st.text_area(
        "我的人设",
        prof.get("self_persona", ""),
        height=120,
        key="profile_self_persona",
        placeholder="描述你的身份、性格、喜好等，让 AI 更了解你\n例如：25岁的程序员，喜欢旅行和美食，性格开朗..."
    )
    if st.button("保存 AI 设置", use_container_width=True, key="save_ai_settings_btn"):
        save_cloud_data()
        st.success("AI 设置已同步到云端！", icon="✅")

    with st.form("profile_form", clear_on_submit=False):
        st.subheader("基本设置", divider="gray")
        prof["nickname"] = st.text_input("昵称", prof["nickname"], placeholder="修改你的显示昵称")

        st.markdown("<p style='margin:15px 0 5px 0; color:#374151;'>我的头像</p>", unsafe_allow_html=True)
        new_av = st.file_uploader("上传新头像", type=['png','jpg','jpeg'], label_visibility="collapsed")
        if new_av:
            av_url = process_uploaded_image(new_av, (200, 200))
            if av_url:
                prof["avatar"] = av_url
                st.success("头像已更新！", icon="✅")

        st.subheader("密码修改", divider="gray")
        old_pwd = st.text_input("原密码", type="password", placeholder="请输入当前密码")
        new_pwd = st.text_input("新密码", type="password", placeholder="请设置新密码")

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.form_submit_button("保存设置", use_container_width=True):
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
            if st.form_submit_button("退出登录", use_container_width=True):
                if "narratio_login" in cookies:
                    del cookies["narratio_login"]
                    cookies.save()
                st.session_state.clear()
                st.rerun()

# ===================== 6. 路由与固定导航 =====================

NAV_ITEMS = [("💬 消息", "Narratio"), ("👥 通讯录", "通讯录"), ("🌍 发现", "发现"), ("👤 我", "我")]

# 消息详情页、人物/群聊设置页不显示顶部菜单行，主内容全宽以便昵称栏居中
if st.session_state.view_mode not in ("chat", "edit_char", "chat_group", "edit_group"):
    col_menu, col_title = st.columns([0.1, 0.9])
    with col_menu:
        if st.button("☰", key="nav_menu_toggle", use_container_width=True, type="secondary", help="打开导航"):
            st.session_state.nav_drawer_open = not st.session_state.nav_drawer_open
            st.rerun()
    with col_title:
        pass

if st.session_state.nav_drawer_open:
    col_drawer, col_main = st.columns([0.28, 0.72])
    with col_drawer:
        st.markdown("### 📜 导航")
        st.caption("选择要去的页面")
        st.markdown("---")
        for label, tab_name in NAV_ITEMS:
            if st.button(
                label,
                key=f"nav_drawer_{tab_name}",
                use_container_width=True,
                type="primary" if st.session_state.active_tab == tab_name else "tertiary"
            ):
                st.session_state.active_tab = tab_name
                st.session_state.nav_drawer_open = False
                st.rerun()
        if st.button("✕ 关闭", key="nav_drawer_close", use_container_width=True):
            st.session_state.nav_drawer_open = False
            st.rerun()
    with col_main:
        main_content_container = st.container()
        with main_content_container:
            if st.session_state.view_mode == "chat":
                render_chat_session()
            elif st.session_state.view_mode == "edit_char":
                render_edit_persona()
            elif st.session_state.view_mode == "chat_group":
                render_group_chat_session()
            elif st.session_state.view_mode == "edit_group":
                render_edit_group()
            else:
                if st.session_state.active_tab == "Narratio":
                    render_chat_list_page()
                elif st.session_state.active_tab == "通讯录":
                    render_contacts_page()
                elif st.session_state.active_tab == "发现":
                    render_moments_page()
                elif st.session_state.active_tab == "我":
                    render_profile_page()
else:
    main_content_container = st.container()
    with main_content_container:
        if st.session_state.view_mode == "chat":
            render_chat_session()
        elif st.session_state.view_mode == "edit_char":
            render_edit_persona()
        elif st.session_state.view_mode == "chat_group":
            render_group_chat_session()
        elif st.session_state.view_mode == "edit_group":
            render_edit_group()
        else:
            if st.session_state.active_tab == "Narratio":
                render_chat_list_page()
            elif st.session_state.active_tab == "通讯录":
                render_contacts_page()
            elif st.session_state.active_tab == "发现":
                render_moments_page()
            elif st.session_state.active_tab == "我":
                render_profile_page()