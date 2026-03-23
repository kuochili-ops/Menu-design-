import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image, ImageDraw, ImageFont
from linebot import LineBotApi
from linebot.models import RichMenu, RichMenuSize, RichMenuArea, RichMenuBounds, URIAction
import google.generativeai as genai
import io
import json

# --- 頁面初始設定 ---
st.set_page_config(page_title="White 6 智能選單助手", layout="centered")
st.title("🤖 White 6 選單與 AI 助手")

# --- 從 Secrets 讀取金鑰 ---
try:
    LINE_TOKEN = st.secrets["LINE_CHANNEL_ACCESS_TOKEN"]
    GEMINI_KEY = st.secrets["GEMINI_API_KEY"]
    
    line_bot_api = LineBotApi(LINE_TOKEN)
    genai.configure(api_key=GEMINI_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"❌ 請檢查 Secrets 設定 (LINE_TOKEN 或 GEMINI_KEY)")
    st.stop()

# --- 側邊欄：AI 聊天測試與存檔 ---
with st.sidebar:
    st.header("🧠 White 6 AI 測試")
    user_input = st.text_input("對 White 6 說點什麼...", placeholder="例如：幫我寫段選單文案")
    if user_input:
        with st.spinner("White 6 思考中..."):
            response = ai_model.generate_content(f"你是助理White 6，請回覆：{user_input}")
            st.write(f"**White 6:** {response.text}")
    
    st.divider()
    st.header("🎨 樣式與存檔")
    line_color = st.color_picker("線條與文字顏色", "#FFFFFF")
    font_size = st.slider("標籤字體大小", 30, 80, 50)
    
    # 載入與匯出 JSON
    uploaded_json = st.file_uploader("載入設定檔 (.json)", type=['json'])
    if 'menu_config' not in st.session_state:
        st.session_state.menu_config = [{"name": f"功能 {i+1}", "url": "https://"} for i in range(6)]
    
    if uploaded_json:
        st.session_state.menu_config = json.load(uploaded_json)
        st.success("設定已載入")

# --- 第一步：固定框圖片處理 ---
st.header("1. 製作選單背景")
st.info("💡 手機操作：請用手指**縮放或拖動照片**，讓畫面進入白色框內。")
img_file = st.file_uploader("上傳背景圖", type=['png', 'jpg', 'jpeg'])

if img_file:
    # 讀取並標準化
    raw_img = Image.open(img_file).convert("RGB")
    
    # 核心：固定比例裁切 (框不動，圖動)
    cropped_img = st_cropper(
        raw_img, 
        aspect_ratio=(2500, 843), 
        box_color=line_color,
        key="white6_cropper"
    )
    
    # 強制重繪為 LINE 規格
    final_canvas = cropped_img.resize((2500, 843))
    draw = ImageDraw.Draw(final_canvas, "RGBA")
    w, h = 2500, 843
    cw, ch = w // 3, h // 2

    # 繪製分隔線
    draw.line([(cw, 0), (cw, h)], fill=line_color, width=5)
    draw.line([(cw*2, 0), (cw*2, h)], fill=line_color, width=5)
    draw.line([(0, ch), (w, ch)], fill=line_color, width=5)

    # --- 第二步：設定格點資訊 ---
    st.header("2. 設定 App 名稱與連結")
    new_data = []
    
    # 針對手機直式螢幕優化，使用摺疊選單
    for i in range(6):
        pos_labels = ["左上", "中上", "右上", "左下", "中下", "右下"]
        with st.expander(f"第 {i+1} 格 ({pos_labels[i]})", expanded=(i==0)):
            name = st.text_input("App 名稱", value=st.session_state.menu_config[i]["name"], key=f"n_{i}")
            url = st.text_input("LIFF URL", value=st.session_state.menu_config[i]["url"], key=f"u_{i}")
            new_data.append({"name": name, "url": url})
            
            # 在圖片上繪製標籤 (半透明黑底+白字)
            row, col = i // 3, i % 3
            draw.rectangle([col*cw, (row+1)*ch-80, (col+1)*cw, (row+1)*ch], fill=(0,0,0,100))
            draw.text((col*cw + 20, (row+1)*ch - 75), name, fill=line_color) # 預設字體

    st.session_state.menu_config = new_data

    # 預覽合成成果
    st.image(final_canvas, caption="📸 合成預覽：包含分隔線與標籤", use_container_width=True)

    # --- 第三步：發布 ---
    if st.button("🚀 發布並更新 LINE 選單", use_container_width=True):
        try:
            with st.spinner("White 6 正在連線 LINE 伺服器..."):
                # 1. 建立點擊區域
                areas = [
                    RichMenuArea(
                        bounds=RichMenuBounds(x=(i%3)*cw, y=(i//3)*ch, width=cw, height=ch),
                        action=URIAction(label=new_data[i]["name"], uri=new_data[i]["url"])
                    ) for i in range(6)
                ]
                
                # 2. 建立選單物件
                rm_obj = RichMenu(
                    size=RichMenuSize(width=2500, height=843),
                    selected=True,
                    name="White6_AI_Menu",
                    chat_bar_text="打開選單",
                    areas=areas
                )
                
                # 3. 註冊與上傳 (自動瘦身)
                rm_id = line_bot_api.create_rich_menu(rich_menu=rm_obj)
                img_io = io.BytesIO()
                final_canvas.save(img_io, format='JPEG', quality=85, optimize=True)
                line_bot_api.set_rich_menu_image(rm_id, 'image/jpeg', img_io.getvalue())
                
                # 4. 設為預設並清理
                line_bot_api.set_default_rich_menu(rm_id)
                for m in line_bot_api.get_rich_menu_list():
                    if m.rich_menu_id != rm_id:
                        line_bot_api.delete_rich_menu(m.rich_menu_id)
                
                st.success("✅ 發布成功！請查看手機 LINE。")
                st.balloons()
        except Exception as e:
            st.error(f"❌ 發生錯誤: {e}")

else:
    st.info("👋 你好！我是 White 6，請先上傳一張背景圖，我會幫你製作精美的選單。")
