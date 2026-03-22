import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image, ImageDraw, ImageFont
from linebot import LineBotApi
from linebot.models import RichMenu, RichMenuSize, RichMenuArea, RichMenuBounds, URIAction
import io
import json

# --- 頁面設定 (手機優化) ---
st.set_page_config(page_title="LINE 專業選單製作", layout="centered")
st.title("📱 LINE 3x2 選單產生器")

# --- 金鑰檢查 ---
try:
    TOKEN = st.secrets["LINE_CHANNEL_ACCESS_TOKEN"]
    line_bot_api = LineBotApi(TOKEN)
except:
    st.error("❌ 請設定 Secrets: LINE_CHANNEL_ACCESS_TOKEN")
    st.stop()

# --- 初始化 Session State (用於載入/儲存) ---
if 'menu_config' not in st.session_state:
    st.session_state.menu_config = [{"name": f"功能 {i+1}", "url": "https://"} for i in range(6)]

# --- 側邊欄：樣式與存取功能 ---
with st.sidebar:
    st.header("⚙️ 樣式設定")
    line_color = st.color_picker("分隔線顏色", "#FFFFFF")
    line_width = st.slider("分隔線粗細", 1, 10, 3)
    font_size = st.slider("文字大小", 20, 100, 50)
    text_color = st.color_picker("文字顏色", "#FFFFFF")
    bg_opacity = st.slider("文字底色透明度", 0, 255, 120)
    
    st.divider()
    st.header("💾 存檔與載入")
    # 匯出設定
    config_json = json.dumps(st.session_state.menu_config)
    st.download_button("下載目前的設定檔 (.json)", config_json, file_name="rich_menu_config.json")
    
    # 匯入設定
    uploaded_config = st.file_uploader("載入舊的設定檔", type=['json'])
    if uploaded_config:
        st.session_state.menu_config = json.load(uploaded_config)
        st.success("設定已載入！")

# --- 步驟 1: 圖片處理 (框固定，圖縮放) ---
st.header("1. 調整背景圖")
img_file = st.file_uploader("上傳原始照片", type=['png', 'jpg', 'jpeg'])

if img_file:
    raw_img = Image.open(img_file).convert("RGB")
    
    # 手機版縮放介面
    cropped_img = st_cropper(
        raw_img, 
        aspect_ratio=(2500, 843), 
        box_color=line_color,
        key="main_cropper"
    )
    
    # 調整至標準尺寸
    base_img = cropped_img.resize((2500, 843))
    
    # --- 關鍵：自動繪製分隔線與文字 ---
    draw = ImageDraw.Draw(base_img, "RGBA")
    w, h = 2500, 843
    cw, ch = w // 3, h // 2
    
    # 繪製分隔線
    for i in range(1, 3): # 直線
        draw.line([(i*cw, 0), (i*cw, h)], fill=line_color, width=line_width)
    draw.line([(0, ch), (w, ch)], fill=line_color, width=line_width) # 橫線

    # --- 步驟 2: 設定 6 格資訊 ---
    st.header("2. 設定內容")
    updated_config = []
    
    # 使用直列排版，更適合手機滑動
    for i in range(6):
        pos_names = ["左上", "中上", "右上", "左下", "中下", "右下"]
        with st.expander(f"第 {i+1} 格 ({pos_names[i]}) 設定", expanded=(i==0)):
            name = st.text_input("顯示名稱", value=st.session_state.menu_config[i]["name"], key=f"n_{i}")
            url = st.text_input("LIFF URL", value=st.session_state.menu_config[i]["url"], key=f"u_{i}")
            updated_config.append({"name": name, "url": url})
            
            # 在圖片上繪製文字標籤
            row, col = i // 3, i % 3
            # 繪製文字背景半透明條
            draw.rectangle([col*cw, (row+1)*ch-80, (col+1)*cw, (row+1)*ch], fill=(0,0,0,bg_opacity))
            # 寫入文字 (這裡使用預設字體，若需中文字體需指定 .ttf 路徑)
            try:
                # 嘗試載入系統中文字體，若失敗則用預設
                font = ImageFont.truetype("Arial Unicode.ttf", font_size)
            except:
                font = ImageFont.load_default()
            
            draw.text((col*cw + 20, (row+1)*ch - 70), name, fill=text_color, font=font)

    st.session_state.menu_config = updated_config
    
    # 預覽最終合成圖
    st.header("預覽合成效果")
    st.image(base_img, use_container_width=True)

    # --- 步驟 3: 發布 ---
    if st.button("🚀 壓縮並發布至 LINE", use_container_width=True):
        try:
            with st.spinner("同步中..."):
                # 1. 建立選單結構
                areas = [
                    RichMenuArea(
                        bounds=RichMenuBounds(x=(i%3)*cw, y=(i//3)*ch, width=cw, height=ch),
                        action=URIAction(label=updated_config[i]["name"], uri=updated_config[i]["url"])
                    ) for i in range(6)
                ]
                rm_obj = RichMenu(
                    size=RichMenuSize(width=2500, height=843),
                    selected=True,
                    name="Advanced_Menu",
                    chat_bar_text="打開選單",
                    areas=areas
                )
                
                rm_id = line_bot_api.create_rich_menu(rich_menu=rm_obj)
                
                # 2. 圖片瘦身
                img_io = io.BytesIO()
                base_img.save(img_io, format='JPEG', quality=85)
                img_bytes = img_io.getvalue()
                
                # 3. 上傳與設為預設
                line_bot_api.set_rich_menu_image(rm_id, 'image/jpeg', img_bytes)
                line_bot_api.set_default_rich_menu(rm_id)
                
                # 4. 清理舊選單
                for m in line_bot_api.get_rich_menu_list():
                    if m.rich_menu_id != rm_id:
                        line_bot_api.delete_rich_menu(m.rich_menu_id)
                
                st.success("✅ 選單更新成功！")
                st.balloons()
        except Exception as e:
            st.error(f"錯誤: {e}")
else:
    st.info("👋 請上傳一張照片開始製作。")
