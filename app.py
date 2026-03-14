import streamlit as st
from openai import OpenAI
import time
import re
import json
import os
import ssl
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
try:
    import httpx
except ImportError:
    httpx = None

# ===================== 0. 全局设置 =====================
st.set_page_config(page_title="Echoem", page_icon="🪽", layout="wide", initial_sidebar_state="collapsed")

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
            blk.style.maxWidth = '100%';
            blk.style.width = '100%';
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
    /* 1. 基础重置 - 彻底杜绝横向溢出，手机端一屏内 */
    html, body {
        width: 100vw !important;
        max-width: 100vw !important;
        overflow-x: hidden !important;
        margin: 0 !important;
        padding: 0 !important;
        box-sizing: border-box !important;
    }
    @media (max-width: 768px) {
        html, body { min-height: 100dvh !important; height: auto !important; }
        .stApp { min-height: 100dvh !important; }
    }
    * {
        box-sizing: border-box !important;
        max-width: 100vw !important; /* 所有元素最大宽度不超过屏幕 */
    }
    [data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {
        display: none !important;
    }
    .block-container { 
        padding-top: 0.8rem !important; 
        padding-bottom: 1.5rem !important;
        max-width: 100vw !important; /* 核心：主容器宽度100vw */
        width: 100% !important;
        margin: 0 auto !important;
        padding-left: 6px !important;  /* 移动端收紧内边距 */
        padding-right: 6px !important;
    }
    /* 手机端：极简留白 + 严格限宽，禁止顶栏/底栏/列表行撑破屏 */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 0.25rem !important;
            padding-bottom: 1rem !important;
            padding-left: 4px !important;
            padding-right: 4px !important;
            width: 100% !important;
            max-width: 100vw !important;
            overflow-x: hidden !important;
        }
        [data-testid="stVerticalBlock"] {
            gap: 0 !important;
            margin-bottom: 0 !important;
            max-width: 100% !important;
        }
        [data-testid="stVerticalBlock"] > div {
            min-height: 0 !important;
        }
        [data-testid="stHorizontalBlock"] {
            width: 100% !important;
            max-width: 100% !important;
            min-width: 0 !important;
            overflow: hidden !important;
        }
        [data-testid="column"] {
            min-width: 0 !important;
            max-width: 100% !important;
            overflow: hidden !important;
        }
        .block-container > [data-testid="stVerticalBlock"]:first-child {
            padding-top: 0 !important;
            margin-bottom: 2px !important;
            max-width: 100% !important;
        }
        .block-container .stButton > button {
            padding-top: 4px !important;
            padding-bottom: 4px !important;
            max-width: 100% !important;
        }
        .block-container h3, .block-container [class*="stMarkdown"] h3 {
            margin: 4px 0 8px 0 !important;
            font-size: 1rem !important;
        }
        .chat-item {
            padding: 6px 4px !important;
        }
        .chat-bubble-row { margin-bottom: 8px !important; }
        .chat-bubble-content { padding: 10px 12px !important; }
    }
    /* 2. 整体视觉风格 - 保留原设计 */
    .stApp { 
        background-color: #F0F2F5; 
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        width: 100vw !important;
        max-width: 100vw !important;
        overflow-x: hidden !important;
    }
    /* 2.1 左上角菜单栏 - 点击召唤左侧导航 */
    .nav-top-bar { margin-bottom: 4px !important; }
    .nav-top-title { font-size: 1rem !important; color: #6B7280 !important; font-weight: 600 !important; }
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
    .chat-header-center-wrap .chat-name { font-size: 15px !important; font-weight: 600 !important; color: #111827 !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; line-height: 1.2 !important; }
    .chat-header-center-wrap .chat-typing { font-size: 11px !important; color: #9CA3AF !important; min-height: 14px !important; line-height: 1.2 !important; }
    /* 聊天页顶栏：返回|昵称|设置 强制单行横排（含手机端，覆盖 Streamlit 默认纵向堆叠） */
    body.chat-view .block-container [data-testid="stHorizontalBlock"]:first-of-type {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: center !important;
        gap: 0 !important;
        width: 100% !important;
    }
    body.chat-view .block-container [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"]:first-child,
    body.chat-view .block-container [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"]:last-child {
        flex-shrink: 0 !important;
        flex: 0 0 44px !important;
        width: 44px !important;
        min-width: 44px !important;
        max-width: 48px !important;
    }
    body.chat-view .block-container [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"]:nth-child(2) {
        flex: 1 1 0% !important;
        min-width: 0 !important;
        overflow: hidden !important;
    }
    @media (max-width: 640px) {
        body.chat-view .block-container [data-testid="stHorizontalBlock"]:first-of-type {
            flex-direction: row !important;
            flex-wrap: nowrap !important;
        }
        body.chat-view .block-container [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"]:first-child,
        body.chat-view .block-container [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"]:last-child {
            flex: 0 0 40px !important;
            min-width: 40px !important;
        }
    }
    /* 聊天页顶栏固定：昵称栏透明底色，不随消息滚动 */
    body.chat-view .block-container [data-testid="stVerticalBlock"]:has([data-testid="stHorizontalBlock"]:first-of-type) {
        position: sticky !important;
        top: 0 !important;
        z-index: 100 !important;
        background: transparent !important;
        padding-bottom: 6px !important;
        box-shadow: none !important;
    }
    body.chat-view [data-testid="stPopover"] > button {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    @media (max-width: 768px) {
        body.chat-view .block-container [data-testid="stVerticalBlock"]:has([data-testid="stHorizontalBlock"]:first-of-type) {
            padding-bottom: 2px !important;
            padding-left: 0 !important;
            margin-left: 0 !important;
        }
        /* 手机端：顶栏左对齐，取消左右空列占位，昵称与会话页面对齐 */
        body.chat-view .block-container [data-testid="stHorizontalBlock"]:first-of-type,
        body.chat-view .chat-header-marker + [data-testid="stVerticalBlock"] [data-testid="stHorizontalBlock"] {
            justify-content: flex-start !important;
            margin-left: 0 !important;
            padding-left: 0 !important;
            width: 100% !important;
        }
        body.chat-view .chat-header-marker + [data-testid="stVerticalBlock"] {
            margin-left: 0 !important;
            padding-left: 0 !important;
        }
        body.chat-view .block-container [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"]:first-child,
        body.chat-view .block-container [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"]:last-child,
        body.chat-view .chat-header-marker + [data-testid="stVerticalBlock"] [data-testid="column"]:first-child,
        body.chat-view .chat-header-marker + [data-testid="stVerticalBlock"] [data-testid="column"]:last-child {
            flex: 0 0 0 !important;
            width: 0 !important;
            min-width: 0 !important;
            max-width: 0 !important;
            overflow: hidden !important;
        }
        body.chat-view .block-container [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"]:nth-child(2),
        body.chat-view .chat-header-marker + [data-testid="stVerticalBlock"] [data-testid="column"]:nth-child(2) {
            flex: 1 1 auto !important;
            max-width: 100% !important;
            text-align: left !important;
            margin-left: 0 !important;
            padding-left: 0 !important;
        }
        body.chat-view .block-container [data-testid="stHorizontalBlock"]:first-of-type [data-testid="column"] .stButton > button,
        body.chat-view [data-testid="stPopover"] button {
            padding: 2px 6px !important;
            min-height: 32px !important;
        }
        /* 顶部昵称栏、popover 触发按钮不撑破屏 */
        body.chat-view [data-testid="stPopover"] {
            max-width: 100% !important;
        }
        body.chat-view [data-testid="stPopover"] > button {
            width: 100% !important;
            max-width: 100% !important;
        }
    }
    /* 4. 聊天气泡 - 移动端进一步优化宽度 */
    .chat-bubble-row { 
        display: flex; 
        margin-bottom: 12px !important; 
        align-items: flex-end !important; /* 气泡与头像底部对齐，更自然 */
        position: relative;
        width: 100% !important;
    }
    .chat-bubble-row.me { justify-content: flex-end; }
    .chat-bubble-avatar { 
        width: 34px !important; /* 移动端固定小头像 */
        height: 34px !important;
        border-radius: 50%;
        overflow: hidden; 
        margin: 0 6px !important; /* 收紧头像边距 */
        flex-shrink: 0; 
        background-color: #F3F4F6;
        display: flex; 
        align-items: center; 
        justify-content: center; 
        font-size: 16px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    .chat-bubble-avatar img { 
        width: 100%; 
        height: 100%; 
        object-fit: cover; 
    }
    .chat-bubble-content { 
        max-width: 85% !important; /* 移动端气泡占比提高，避免留白 */
        padding: 12px 16px !important; /* 收紧气泡内边距 */
        border-radius: 18px !important;
        font-size: 14px !important; /* 移动端小字，适配小屏 */
        line-height: 1.4;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        position: relative;
        word-wrap: break-word !important; /* 强制换行，避免长文本撑宽 */
        word-break: break-all !important;
    }
    .chat-bubble-other { 
        background-color: #FFFFFF; 
        border: 1px solid #E5E7EB;
        border-bottom-left-radius: 4px !important;
        color: #111827;
    }
    .chat-bubble-me { 
        background-color: #3B82F6;
        color: #FFFFFF;
        border-bottom-right-radius: 4px !important;
    }
    
    /* 5. 朋友圈卡片 - 移动端适配 */
    .moment-card { 
        background: transparent; 
        padding: 10px 0 14px 0 !important; 
        border-radius: 0; 
        margin-bottom: 0; 
        border-bottom: 1px solid #E5E7EB;
        box-shadow: none;
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
        border-bottom: 1px solid #E5E5E5;
        line-height: 1.4;
        word-wrap: break-word !important;
    }
    .comment-item:last-child { border-bottom: none; }
    .comment-user { 
        color: #576B95; 
        font-weight: 500; 
        margin-right: 4px; 
    }
    /* 6. 普通按钮 - 保留原设计 */
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
    /* 8. 转账卡片 - 移动端适配，避免撑宽 */
    .transfer-card {
        background: linear-gradient(135deg, #F59E0B, #FBBF24);
        border-radius: 16px !important;
        padding: 10px 14px !important;
        min-width: 180px !important; /* 减小最小宽度 */
        max-width: 90% !important; /* 最大宽度不超过90%屏幕 */
        color: #FFFFFF;
        display: flex;
        flex-direction: column;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        word-wrap: break-word !important;
    }
    .transfer-title { font-size: 11px !important; opacity: 0.9; margin-bottom: 2px; }
    .transfer-amount { font-size: 20px !important; font-weight: 700; margin: 4px 0; }
    .transfer-note { font-size: 12px !important; opacity: 0.95; margin-bottom: 4px; }
    .transfer-status { font-size: 10px !important; margin-top: 4px; opacity: 0.9; text-align: right; }
    .transfer-card.received {
        background: linear-gradient(135deg, #FEF3C7, #FDE68A);
        color: #92400E;
    }
    /* 9. 登录/注册页面 - 移动端适配 */
    .auth-container { 
        max-width: 100vw !important; 
        width: 90% !important;
        margin: 0 auto !important;
        padding: 20px 10px !important; /* 收紧登录页内边距 */
    }
    .auth-title { font-size: 24px !important; font-weight: 700; color: #111827; margin-bottom: 8px; }
    .auth-subtitle { color: #6B7280; margin-bottom: 20px !important; font-size: 14px !important; }
    /* 1. 强制网格重叠：让 HTML 和按钮强行在同一个格子里 */
    [data-testid="stVerticalBlock"] > div:has(.chat-item-container) {
        display: grid !important;
        grid-template-areas: "overlay" !important;
    }

    .chat-item-container {
        grid-area: overlay !important;
        z-index: 1;
    }

    /* 2. 按钮容器：强行占领视觉层所在的空间 */
    [data-testid="stElementContainer"]:has(button[title^="jump_"]) {
        grid-area: overlay !important;
        z-index: 2 !important; /* 确保在上面 */
        height: 72px !important;
        margin: 0 !important;
    }

    /* 3. 视觉层样式（人物框） */
    .chat-item {
        display: flex;
        align-items: center;
        padding: 0 16px;
        background: #FFFFFF;
        border-bottom: 0.5px solid #E5E5E7;
        width: 100%;
        height: 72px;
        box-sizing: border-box;
        pointer-events: none; /* 让鼠标穿透它 */
    }

    /* 4. 透明按钮样式：全透明且铺满 */
    button[title^="jump_"] {
        width: 100% !important;
        height: 72px !important;
        min-height: 72px !important;
        background: transparent !important;
        color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        cursor: pointer !important;
        opacity: 0 !important; /* 调试时可以改成 0.1 看看位置 */
    }

    /* 移动端优化：点击时的反馈感 */
    button[title^="jump_"]:active {
        background: rgba(0,0,0,0.05) !important;
        opacity: 1 !important;
    }
    /* 11. 收款按钮 - 移动端适配 */
    .receive-btn {
        background-color: #FFFFFF !important;
        color: #F59E0B !important;
        border: 1px solid #F59E0B !important;
        border-radius: 6px !important;
        padding: 3px 10px !important;
        font-size: 12px !important;
        margin-top: 6px !important;
        width: auto !important;
    }
    /* 12. 发现页互动工具栏 - 移动端适配 */
    .interaction-toolbar {
        display: flex;
        align-items: center;
        justify-content: flex-start;
        gap: 8px !important; /* 收紧工具栏间距 */
        margin-top: 10px !important;
        margin-bottom: 12px !important;
        width: 100% !important;
        overflow-x: auto !important; /* 允许横向滚动，避免按钮挤压 */
        padding-bottom: 4px !important;
    }
    .interaction-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 5px 12px !important;
        border-radius: 6px !important;
        background-color: #F9FAFB;
        border: 1px solid #E5E7EB;
        font-size: 12px !important;
        color: #6B7280;
        min-width: 70px !important; /* 减小最小宽度 */
        height: 28px !important;
        text-align: center;
        flex-shrink: 0; /* 按钮不收缩 */
    }
    .interaction-toolbar .stButton>button {
        min-width: 70px !important;
        height: 28px !important;
        padding: 5px 12px !important;
        border-radius: 6px !important;
        background-color: #F9FAFB !important;
        border: 1px solid #E5E7EB !important;
        font-size: 12px !important;
        color: #6B7280 !important;
        text-align: center !important;
        justify-content: center !important;
        flex-shrink: 0;
    }
    .comment-input-container {
        margin-top: 8px !important;
        padding-top: 8px !important;
        border-top: 1px solid #F3F4F6;
        display: flex;
        align-items: center;
        gap: 6px !important;
        width: 100% !important;
    }
    .comment-input { flex: 1; }
    .comment-send-btn {
        width: 50px !important; /* 减小发送按钮宽度 */
        padding: 5px 0 !important;
        border-radius: 6px !important;
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
        font-size: 13px !important; /* 移动端小字 */
        color: #6B7280 !important;
        font-weight: normal !important;
        padding-left: 0 !important;
        margin-left: 0 !important;
        border-radius: 0 !important;
    }
    
    /* 记忆库展示样式 - 移动端适配 */
    .memory-bank-info {
        background: #F0F9FF;
        border: 1px solid #BAE6FD;
        border-radius: 6px !important;
        padding: 8px 12px !important;
        margin: 8px 0 !important;
        font-size: 12px !important;
        color: #0369A1;
        width: 100% !important;
    }
    .memory-item {
        background: #F9FAFB;
        border-radius: 4px !important;
        padding: 6px 10px !important;
        margin: 4px 0 !important;
        font-size: 12px !important;
        color: #374151;
        border-left: 3px solid #3B82F6;
        width: 100% !important;
        word-wrap: break-word !important;
    }

    /* ===== 超小屏优化（iPhone SE/小屏安卓）===== */
    @media (max-width: 375px) {
        .block-container {
            padding-left: 4px !important;
            padding-right: 4px !important;
        }
        .chat-bubble-content {
            max-width: 88% !important;
            padding: 10px 12px !important;
            font-size: 13px !important;
        }
        .chat-item {
            padding: 6px 4px !important;
        }
        .transfer-card {
            min-width: 160px !important;
            padding: 8px 12px !important;
        }
        .transfer-amount {
            font-size: 18px !important;
        }
    }

    /* 突破 Streamlit 的手机端限制，强制横向排列 + 底部栏压扁 */
    @media (max-width: 768px) {
        [data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
            flex-direction: row !important;
        }
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 0% !important;
        }
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
    _cookie_secret = getattr(st.secrets, "COOKIES_PASSWORD", None) or os.environ.get("COOKIES_PASSWORD", "echoem-remember-secret")
except Exception:
    _cookie_secret = os.environ.get("COOKIES_PASSWORD", "echoem-remember-secret")
cookies = EncryptedCookieManager(prefix="echoem/", password=_cookie_secret)
if not cookies.ready():
    st.stop()

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

def _is_network_or_ssl_error(e):
    """判断是否为网络/SSL 连接类错误（Supabase 请求失败时友好提示）"""
    if isinstance(e, ssl.SSLError):
        return True
    if httpx and isinstance(e, (httpx.ConnectError, httpx.ConnectTimeout)):
        return True
    msg = str(e).lower()
    return "ssl" in msg or "eof" in msg or "connection" in msg or "connect" in msg

def _supabase_request_with_retry(request_fn, max_attempts=2):
    """执行 Supabase 请求，失败时重试一次（应对瞬时 SSL/网络中断）"""
    last_err = None
    for attempt in range(max_attempts):
        try:
            return request_fn()
        except Exception as e:
            last_err = e
            if _is_network_or_ssl_error(e) and attempt < max_attempts - 1:
                time.sleep(1.5)
                continue
            raise
    if last_err is not None:
        raise last_err

def try_restore_session_from_cookie():
    """从持久化 Cookie 恢复登录状态（同一设备再次打开网页时免登录）"""
    val = cookies.get("echoem_login")
    if not val:
        return False
    try:
        data = json.loads(val)
        if data.get("exp", 0) <= time.time():
            return False  # 已过期
        username = data.get("username")
        if not username:
            return False
        try:
            res = _supabase_request_with_retry(
                lambda: supabase.table("user_data").select("*").eq("username", username).execute()
            )
        except Exception as e:
            if _is_network_or_ssl_error(e):
                return False  # 静默失败，让用户重新登录
            raise
        if not res.data:
            return False
        row = res.data[0]
        characters = row.get("characters") or []
        for char in characters:
            if "memory_bank" not in char:
                char["memory_bank"] = {"core_memories": [], "recent_context": []}
        st.session_state.update({
            "password_correct": True,
            "username": username,
            "user_profile": row.get("profile") or {},
            "characters": characters,
            "moments": row.get("moments") or []
        })
        return True
    except Exception:
        return False

def validate_username(username):
    """验证账号名是否为英文字母或数字"""
    return bool(re.match(r'^[a-zA-Z0-9]+$', username))

def check_password():
    # 未登录时先尝试从持久化 Cookie 恢复（同一设备再次打开直接进主页）
    if "password_correct" not in st.session_state and try_restore_session_from_cookie():
        st.rerun()
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
                try:
                    res = _supabase_request_with_retry(
                        lambda: supabase.table("user_data").select("*").eq("username", u).execute()
                    )
                except Exception as e:
                    if _is_network_or_ssl_error(e):
                        st.error("无法连接服务器，请检查网络或稍后重试。若使用代理，请确认 SSL 正常。")
                    else:
                        raise
                    res = None
                if res is None:
                    pass  # 已展示网络错误
                elif res.data and verify_password(p, res.data[0]["password_hash"]):
                    # 数据迁移：为旧角色添加memory_bank
                    characters = res.data[0]["characters"] or []
                    for char in characters:
                        if "memory_bank" not in char:
                            char["memory_bank"] = {
                                "core_memories": [],
                                "recent_context": []
                            }
                    # 持久登录：写入 Cookie，30 天内同一设备免登录
                    login_payload = json.dumps({"username": u, "exp": time.time() + 30 * 24 * 3600})
                    cookies["echoem_login"] = login_payload
                    cookies.save()
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
                        try:
                            res = _supabase_request_with_retry(
                                lambda: supabase.table("user_data").select("username").eq("username", nu).execute()
                            )
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
                        except Exception as e:
                            if _is_network_or_ssl_error(e):
                                st.error("无法连接服务器，请检查网络或稍后重试。若使用代理，请确认 SSL 正常。")
                            else:
                                raise
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
if "nav_drawer_open" not in st.session_state: st.session_state.nav_drawer_open = False

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
    st.markdown("<h3 style='text-align:center; margin:10px 0;'>消息</h3>", unsafe_allow_html=True)

    display_chars = st.session_state.characters or []
    # 类微信：按最近消息条数近似排序（真实项目可存 timestamp）
    def last_ts(c):
        return len(c.get("messages", []))
    display_chars = sorted(display_chars, key=last_ts, reverse=True)

    if not display_chars:
        st.markdown("""
        <div style='text-align:center; padding:60px 20px; color:#6B7280;'>
            <p style='font-size:16px;'>暂无聊天对象</p>
            <p style='font-size:14px; margin-top:8px;'>前往「通讯录」添加 AI 角色开始聊天吧</p>
        </div>
        """, unsafe_allow_html=True)
        return

    for char in display_chars:
        # 获取头像和最后消息
        avatar_html = get_avatar_html(char.get("avatar"))
        last_msg = (char.get("messages", [])[-1]["content"] if char.get("messages") else "暂无消息") or "暂无消息"
        last_msg = html.escape(str(last_msg)[:18])
        safe_name = html.escape(char["name"])

        # --- 步骤 1：视觉层（增加外层 div 让 CSS 识别“待重合”区域）---
        st.markdown(f"""
        <div class="chat-item-container">
            <div class="chat-item">
                <div style="margin-right: 12px;">{avatar_html}</div>
                <div style="flex-grow: 1; overflow: hidden;">
                    <div style="font-size: 16px; font-weight: 500; color: #1a1a1a;">{safe_name}</div>
                    <div style="font-size: 13px; color: #8e8e93; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        {last_msg}
                    </div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- 步骤 2：交互层（必须紧跟在上面的 markdown 后面）---
        if st.button("进入", key=f"btn_{char['id']}", help=f"jump_{char['id']}", use_container_width=True):
            st.session_state.current_char_id = char["id"]
            st.session_state.view_mode = "chat"
            st.rerun()

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

    # 居中显示昵称，点击后弹出悬浮菜单（手机端通过 CSS 左对齐与会话列表一致）
    st.markdown("<script>document.body.classList.add('chat-view');</script>", unsafe_allow_html=True)
    st.markdown('<div class="chat-header-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        # st.popover 会在点击后弹出一个气泡菜单，完美替代纵向堆叠
        with st.popover(char["name"], use_container_width=True):
            if st.button("⬅️ 返回消息列表", use_container_width=True):
                st.session_state.view_mode = "main"
                st.rerun()
            if st.button("⚙️ 角色设置", use_container_width=True):
                st.session_state.view_mode = "edit_char"
                st.rerun()
        typing_placeholder = st.empty()
    st.markdown("<hr style='margin:4px 0 6px 0; border:none; border-top:1px solid #E5E7EB;'/>", unsafe_allow_html=True)
    
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
            <p style='font-size:14px; margin-top:8px;'>发布一条动态，和好友互动吧</p>
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
                if "echoem_login" in cookies:
                    del cookies["echoem_login"]
                    cookies.save()
                st.session_state.clear()
                st.rerun()

# ===================== 6. 路由与固定导航 =====================

NAV_ITEMS = [("💬 消息", "Echoem"), ("👥 通讯录", "通讯录"), ("🌍 发现", "发现"), ("👤 我", "我")]

# 左上角菜单按钮（仅图标，无旁边标题/索引）
col_menu, _ = st.columns([0.1, 0.9])
with col_menu:
    if st.button("☰", key="nav_menu_toggle", use_container_width=True, type="secondary", help="打开导航"):
        st.session_state.nav_drawer_open = not st.session_state.nav_drawer_open
        st.rerun()

if st.session_state.nav_drawer_open:
    col_drawer, col_main = st.columns([0.28, 0.72])
    with col_drawer:
        st.markdown("### 🪽 导航")
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
            else:
                if st.session_state.active_tab == "Echoem":
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
        else:
            if st.session_state.active_tab == "Echoem":
                render_chat_list_page()
            elif st.session_state.active_tab == "通讯录":
                render_contacts_page()
            elif st.session_state.active_tab == "发现":
                render_moments_page()
            elif st.session_state.active_tab == "我":
                render_profile_page()
