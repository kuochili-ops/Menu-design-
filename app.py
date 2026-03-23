import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image, ImageDraw, ImageFont
from linebot import LineBotApi
from linebot.models import RichMenu, RichMenuSize, RichMenuArea, RichMenuBounds, URIAction
import google.generativeai as genai
import io
import json

# --- 1. 頁面初始設定 ---
st.set_page_config(page_title="White 6 智能選單助手", layout="centered")
st.title("🤖 White 6 選單與 AI 助手")

# --- 2. 從 Secrets 讀取金鑰 (偵錯版) ---
try:
    # 這裡會自動從 Streamlit Cloud 的 Secrets 抓取資料
    LINE_TOKEN = st.secrets["LINE_TOKEN"]
    GEMINI_KEY = st.secrets["GEMINI_KEY"]
    
    line_bot_api = LineBotApi(LINE_TOKEN)
    genai.configure(api_key=GEMINI_KEY)
    ai_model = genai.GenerativeModel('models/gemini-1.5-flash')
except Exception as e:
    st.error(f"❌ 金鑰讀取失敗，請確認 Secrets 設定。")
    st.info("💡 提示：請在 Secrets 檢查是否包含 LINE_TOKEN 與 GEMINI_KEY 標籤。")
    st.stop()

# --- 3. 側邊欄：AI 聊天與樣式設定 ---
with st.sidebar:
    st.header("🧠 White 6 AI 大腦")
    chat_input = st.text_input("對 White 6 說話...", placeholder="例如：幫我想 6 個選單標題")
    if chat_input:
        with st.spinner("思考中..."):
            response = ai_model.generate_content(f"你是助理White 6，請回覆：{chat_input}")
            st.write(f"**White 6:** {response.text}")
    
    st.divider()
    st.header("🎨 選單外觀設定")
    line_color = st.color_picker("分隔線與文字顏色", "#FFFFFF")
    
    # 載入歷史設定
    if 'menu_config' not in st.session_state:
        st.session_state.menu_config = [{"name": f"功能 {i+1}", "url": "https://"} for i in range(6)]
    
    uploaded_json = st.file_uploader("載入舊設定檔 (.json)", type=['json'])
    if uploaded_json:
        st.session_state.menu_config = json.load(uploaded_json)
        st.success("設定已載入！")

# --- 4. 製作區：固定框圖片處理 ---
st.header("1. 調整背景圖片")
st.write("操作：請用手指**縮放或拖動照片**，讓預期畫面進入**白色固定框**內。")
img_file = st.file_uploader("上傳照片 (JPG/PNG)", type=['png', 'jpg', 'jpeg'])

if img_file:
    # 讀取圖片並轉為 RGB
    raw_img = Image.open(img_file).convert("RGB")
    
    # 核心：固定比例裁切 (2500:843)
    # 框在畫面中間不動，使用者縮放移動底圖
    cropped_img = st_cropper(
        raw_img, 
        aspect_ratio=(2500, 843), 
        box_color=line_color,
        key="white6_cropper_v2"
    )
    
    # 強制重塑為 LINE 標準規格
    final_canvas = cropped_img.resize((2500, 843))
    draw = ImageDraw.Draw(final_canvas, "RGBA")
    w, h = 2500, 843
    cw, ch = w // 3, h // 2

    # --- 5. 設定格子資訊 (3x2 佈局) ---
    st.header("2. 設定 6 格功能與名稱")
    new_data = []
    
    # 使用 Expander 摺疊介面優化手機顯示
    for i in range(6):
        pos_names = ["左上", "中上", "右上", "左下", "中下", "右下"]
        with st.expander(f"第 {i+1} 格 ({pos_names[i]})", expanded=(i==0)):
            name = st.text_input("顯示名稱", value=st.session_state.menu_config[i]["name"], key=f"n_{i}")
            url = st.text_input("LIFF URL", value=st.session_state.menu_config[i]["url"], key=f"u_{i}")
            new_data.append({"name": name, "url": url})
            
            # 實時在圖片上繪製分隔線與文字標籤
            row, col = i // 3, i % 3
            # 繪製分隔線
            draw.line([(cw, 0), (cw, h)], fill=line_color, width=5)
            draw.line([(cw*2, 0), (cw*2, h)], fill=line_color, width=5)
            draw.line([(0, ch), (w, ch)], fill=line_color, width=5)
            # 繪製半透明文字底條
            draw.rectangle([col*cw, (row+1)*ch-80, (col+1)*cw, (row+1)*ch], fill=(0,0,0,120))
            # 寫入文字 (標註名稱)
            draw.text((col*cw + 30, (row+1)*ch - 70), name, fill=line_color)

    st.session_state.menu_config = new_data

    # 顯示合成後的預覽圖
    st.image(final_canvas, caption="📸 合成預覽：將以此圖上傳至 LINE", use_container_width=True)

    # --- 6. 壓縮與發布 ---
    if st.button("🚀 確認並同步至 @000wypqw", use_container_width=True):
        try:
            with st.spinner("White 6 正在處理圖片並發布..."):
                # A. 建立點擊區域
                areas = [
                    RichMenuArea(
                        bounds=RichMenuBounds(x=(i%3)*cw, y=(i//3)*ch, width=cw, height=ch),
                        action=URIAction(label=new_data[i]["name"], uri=new_data[i]["url"])
                    ) for i in range(6)
                ]
                
                # B. 建立 Rich Menu
                rm_obj = RichMenu(
                    size=RichMenuSize(width=2500, height=843),
                    selected=True,
                    name="White6_Auto_Menu",
                    chat_bar_text="功能選單",
                    areas=areas
                )
                
                # C. 向 LINE 註冊
                rm_id = line_bot_api.create_rich_menu(rich_menu=rm_obj)
                
                # D. 圖片瘦身 (JPEG 壓縮至 85% 以符合 1MB 限制)
                img_io = io.BytesIO()
                final_canvas.save(img_io, format='JPEG', quality=85, optimize=True)
                line_bot_api.set_rich_menu_image(rm_id, 'image/jpeg', img_io.getvalue())
                
                # E. 設為預設並清理舊選單
                line_bot_api.set_default_rich_menu(rm_id)
                for m in line_bot_api.get_rich_menu_list():
                    if m.rich_menu_id != rm_id:
                        line_bot_api.delete_rich_menu(m.rich_menu_id)
                
                st.success("✅ 發布成功！請開啟或重新追蹤 @000wypqw 查看效果。")
                st.balloons()
        except Exception as e:
            st.error(f"❌ 發布失敗: {e}")

else:
    st.info("👋 你好！我是 White 6。請上傳照片開始製作你的專屬選單。")
